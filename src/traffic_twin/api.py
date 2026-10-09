"""Local-first experiment API. Bind publicly only with TRAFFIC_API_TOKEN set."""
from contextlib import asynccontextmanager
import hmac
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from traffic_twin.schemas import Scenario
from traffic_twin.scheduler import Scheduler, file_hash

ROOT = Path(__file__).resolve().parents[2]

def create_app(root: Path = ROOT, state: Path | None = None, start_scheduler=True, **scheduler_options):
    root = Path(root).resolve()
    scheduler = Scheduler(root, state, **scheduler_options)

    @asynccontextmanager
    async def lifespan(app):
        if start_scheduler: scheduler.start()
        try: yield
        finally:
            if start_scheduler: scheduler.stop()

    app = FastAPI(title="Magic Twin Traffic", version="0.1.0", lifespan=lifespan)
    app.state.scheduler = scheduler

    @app.middleware("http")
    async def limits(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            token = os.environ.get("TRAFFIC_API_TOKEN")
            if token and not hmac.compare_digest(request.headers.get("authorization", ""), "Bearer " + token):
                return JSONResponse({"detail": "Bearer token required"}, 401)
            # No streaming uploads: bounded JSON bodies only.
            if request.method in {"POST", "PUT", "PATCH"}:
                try: length = int(request.headers.get("content-length", "0"))
                except ValueError: return JSONResponse({"detail": "Invalid content length"}, 400)
                if length > 65536: return JSONResponse({"detail": "Request body too large"}, 413)
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 65536: return JSONResponse({"detail": "Request body too large"}, 413)
                if body:
                    try:
                        def reject_constant(value):
                            raise ValueError("Non-finite JSON number")
                        json.loads(body, parse_constant=reject_constant)
                    except (ValueError, UnicodeDecodeError, RecursionError):
                        return JSONResponse({"detail": "A valid finite-number JSON body is required"}, 400)
                request._body = bytes(body)
        return await call_next(request)

    def run_or_404(run_id):
        try: return scheduler.get(run_id)
        except KeyError: raise HTTPException(404, "Unknown run")

    def completed(run_id):
        run = run_or_404(run_id)
        if run["status"] != "succeeded": raise HTTPException(409, "Run has no verified completed result")
        return run

    def read_json(path):
        try: return json.loads(path.read_text())
        except FileNotFoundError: raise HTTPException(404, "Artifact unavailable")

    def validate(config):
        errors = []
        if not (root / "networks/baseline/network.net.xml").is_file(): errors.append("Baseline SUMO network has not been built")
        if not (root / "data/canonical/network.json").is_file(): errors.append("Network asset manifest is missing")
        try:
            from traffic_twin.simulation import validate_config
            result = validate_config(config)
            if isinstance(result, list): errors.extend(result)
            elif isinstance(result, dict): errors.extend(result.get("errors", []))
        except ImportError: errors.append("Simulation validation module is unavailable")
        except (ValueError, RuntimeError, OSError) as exc: errors.append(str(exc))
        return {"valid": not errors, "errors": errors, "config": config,
                "warnings": ["Synthetic scenario demand; this is not calibrated local traffic."]}

    @app.get("/api/health")
    def health(): return {"status": "ok", "schema_version": "1.0", "scheduler": scheduler.status()}

    @app.get("/api/policies")
    def policies():
        try:
            from traffic_twin.policies import policy_catalog
            result = policy_catalog()
            return result if isinstance(result, dict) and "policies" in result else {"policies": result}
        except ImportError: raise HTTPException(503, "Policy catalog unavailable")

    @app.get("/api/networks")
    def networks():
        p = root / "data/canonical/network.json"
        if not p.exists(): return {"networks": []}
        data = read_json(p)
        return {"networks": [{"network_id": "baseline", "network_hash": data.get("network_hash"), "manifest_url": f"/api/networks/{data.get('network_hash')}/manifest"}]}

    @app.get("/api/networks/{network_hash}/manifest")
    def network_manifest(network_hash):
        paths = [root / "data/canonical/network.json"]
        for run in scheduler.list(500):
            if run["status"] == "succeeded": paths.append(scheduler.path(run["run_id"]) / "network.json")
        for p in paths:
            if p.is_file():
                data = read_json(p)
                if data.get("network_hash") == network_hash: return data
        raise HTTPException(404, "Unknown network hash")

    @app.post("/api/scenarios/validate")
    @app.post("/api/validate", include_in_schema=False)
    def validation(scenario: Scenario): return validate(scenario.engine_config())

    @app.post("/api/runs")
    def submit(scenario: Scenario):
        config = scenario.engine_config()
        result = validate(config)
        if not result["valid"]: raise HTTPException(422, result)
        try: return scheduler.submit(config)
        except RuntimeError as exc: raise HTTPException(429, str(exc))

    @app.get("/api/runs")
    def runs(limit: int = Query(100, ge=1, le=500)): return {"runs": scheduler.list(limit)}

    @app.get("/api/runs/{run_id}")
    def run_status(run_id: str):
        run = run_or_404(run_id)
        progress = scheduler.path(run_id) / "progress.json"
        if progress.is_file():
            try: run["progress"] = json.loads(progress.read_text())
            except (OSError, json.JSONDecodeError): pass
        return run

    @app.post("/api/runs/{run_id}/cancel")
    def cancel(run_id: str):
        run_or_404(run_id)
        return scheduler.cancel(run_id)

    @app.get("/api/runs/{run_id}/manifest")
    def manifest(run_id: str):
        completed(run_id)
        data = read_json(scheduler.path(run_id) / "manifest.json")
        return {**data, "chunks": [{**chunk, "file": f"/api/runs/{run_id}/chunks/{chunk['id']}"} for chunk in data.get("chunks", [])], "network_url": f"/api/runs/{run_id}/network", "metrics_url": f"/api/runs/{run_id}/metrics", "chunks_base_url": f"/api/runs/{run_id}/chunks/"}

    @app.get("/api/runs/{run_id}/network")
    def run_network(run_id: str):
        completed(run_id)
        output = scheduler.path(run_id)
        manifest = read_json(output / "manifest.json")
        path = output / "network.json"
        if not path.exists(): path = root / "data/canonical/network.json"
        data = read_json(path)
        if data.get("network_hash") != manifest.get("network_hash"): raise HTTPException(409, "Network/run hash mismatch")
        return data

    @app.get("/api/runs/{run_id}/metrics")
    def metrics(run_id: str):
        completed(run_id)
        return read_json(scheduler.path(run_id) / "metrics.json")

    @app.get("/api/runs/{run_id}/timeseries")
    def timeseries(run_id: str):
        completed(run_id)
        return read_json(scheduler.path(run_id) / "timeseries.json")

    @app.get("/api/runs/{run_id}/signals")
    def signals(run_id: str):
        completed(run_id)
        return read_json(scheduler.path(run_id) / "signals.json")

    @app.get("/api/runs/{run_id}/events")
    def events(run_id: str):
        completed(run_id)
        return read_json(scheduler.path(run_id) / "events.json")

    @app.get("/api/runs/{run_id}/trips")
    def trips(run_id: str):
        completed(run_id)
        return read_json(scheduler.path(run_id) / "trips.json")

    @app.get("/api/runs/{run_id}/audit")
    def audit(run_id: str):
        completed(run_id)
        return read_json(scheduler.path(run_id) / "audit.json")

    @app.get("/api/runs/{run_id}/logs")
    def logs(run_id: str):
        run_or_404(run_id)
        path = scheduler.path(run_id) / "worker.log"
        if not path.exists(): return {"text": ""}
        with path.open("rb") as f:
            f.seek(max(0, path.stat().st_size - 65536))
            return {"text": f.read().decode("utf-8", errors="replace"), "truncated": path.stat().st_size > 65536}

    @app.get("/api/runs/{run_id}/chunks/{chunk_id}")
    def chunk(run_id: str, chunk_id: str):
        completed(run_id)
        output = scheduler.path(run_id)
        manifest = read_json(output / "manifest.json")
        for item in manifest.get("chunks", []):
            if chunk_id in {str(item.get("id")), Path(item["file"]).name}:
                path = (output / item["file"]).resolve()
                if not path.is_relative_to(output): raise HTTPException(409, "Unsafe artifact path")
                if not path.is_file() or file_hash(path) != item["sha256"]: raise HTTPException(409, "Chunk checksum mismatch")
                return FileResponse(path, media_type="application/octet-stream", headers={"X-Network-Hash": manifest["network_hash"], "X-Run-Id": run_id, "ETag": '"' + item["sha256"] + '"'})
        raise HTTPException(404, "Unknown chunk")

    @app.get("/api/compare")
    def compare(run_a: str | None = None, run_b: str | None = None, baseline: str | None = None, candidate: str | None = None):
        a, b = run_a or baseline, run_b or candidate
        if not a or not b: raise HTTPException(422, "Specify run_a and run_b")
        completed(a); completed(b)
        ma = read_json(scheduler.path(a) / "manifest.json")
        mb = read_json(scheduler.path(b) / "manifest.json")
        if ma.get("schema_version") != mb.get("schema_version") or ma.get("demand_hash") != mb.get("demand_hash"):
            raise HTTPException(409, "Comparison requires matching schema and identical exogenous demand manifests")
        if ma.get("valid_for_ranking") is False or mb.get("valid_for_ranking") is False:
            raise HTTPException(409, "Anomalies require review before policy comparison")
        for identity in ("implementation_hash", "engine_version", "action_step_seconds"):
            if ma.get(identity) != mb.get(identity):
                raise HTTPException(409, f"Incompatible experiment implementation: {identity}")
        ca, cb = scheduler.get(a)["config"], scheduler.get(b)["config"]
        for key in ("duration_seconds", "warmup_seconds", "demand_end_seconds", "step_seconds"):
            if ca.get(key) != cb.get(key): raise HTTPException(409, f"Incompatible evaluation condition: {key}")
        am = read_json(scheduler.path(a) / "metrics.json")
        bm = read_json(scheduler.path(b) / "metrics.json")
        delta = {k: bm[k] - v for k, v in am.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and isinstance(bm.get(k), (int, float))}
        return {"run_a": a, "run_b": b, "paired_demand": True, "structural_change": ma["network_hash"] != mb["network_hash"], "metrics_a": am, "metrics_b": bm, "delta": delta, "warning": "One paired run is not an independent statistical policy ranking."}

    built = root / "web/dist"
    if built.is_dir(): app.mount("/", StaticFiles(directory=built, html=True), name="viewer")
    return app

app = create_app(state=Path(os.environ["TRAFFIC_STATE_DIR"]) if os.environ.get("TRAFFIC_STATE_DIR") else None)
