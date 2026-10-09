"""Single-owner durable SQLite queue with isolated, resource-bounded SUMO workers."""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

TERMINAL = {"succeeded", "failed", "cancelled"}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

class Scheduler:
    def __init__(self, root: Path, state: Path | None = None, max_workers=1,
                 timeout_seconds=3600, max_run_bytes=2_000_000_000,
                 min_free_bytes=256_000_000, max_queued=32, worker_memory_mb=4096):
        self.root = Path(root).resolve()
        self.state = Path(state or self.root / "var").resolve()
        self.state.mkdir(parents=True, exist_ok=True)
        self.runs_dir = self.state / "runs"
        self.runs_dir.mkdir(exist_ok=True)
        self.db_path = self.state / "jobs.sqlite3"
        self.max_workers = max(1, min(int(max_workers), 8))
        self.timeout_seconds = timeout_seconds
        self.max_run_bytes = max_run_bytes
        self.min_free_bytes = min_free_bytes
        self.max_queued = max_queued
        self.worker_memory_mb = worker_memory_mb
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._processes = {}
        self._owner = None
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, cache_key TEXT NOT NULL, status TEXT NOT NULL, config TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL, error TEXT)")
            db.execute("CREATE INDEX IF NOT EXISTS runs_cache ON runs(cache_key)")

    def connection(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def start(self):
        import fcntl
        with self._lock:
            if self._thread:
                return
            self._owner = (self.state / "scheduler.lock").open("w")
            try:
                fcntl.flock(self._owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self._owner.close()
                self._owner = None
                raise RuntimeError("Only one API scheduler process may own this state directory")
            with self.connection() as db:
                db.execute("UPDATE runs SET status='failed', error='Server interrupted before verified completion; resubmit to retry', updated_at=? WHERE status IN ('running','finalizing','validating')", (time.time(),))
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="traffic-scheduler")
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        with self._lock:
            for run_id, item in list(self._processes.items()):
                self._terminate(item[0])
                item[1].close()
                self._set_status(run_id, "failed", "Server stopped during execution; resubmit to retry")
            self._processes.clear()
            self._thread = None
            if self._owner:
                self._owner.close()
                self._owner = None

    def fingerprints(self, config):
        sources = {str(p.relative_to(self.root)): file_hash(p) for p in sorted((self.root / "src").rglob("*.py"))}
        for name in ("pyproject.toml", "requirements.lock"):
            p = self.root / name
            if p.exists(): sources[name] = file_hash(p)
        inputs = {}
        for folder in ("networks", "data/canonical", "data/demand", "scenarios"):
            for p in sorted((self.root / folder).rglob("*")):
                if p.is_file(): inputs[str(p.relative_to(self.root))] = file_hash(p)
        versions = {"python": sys.version}
        for name in ("libsumo", "eclipse-sumo", "sumolib", "numpy", "pyarrow", "pydantic"):
            try: versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError: versions[name] = "missing"
        implementation_hash = digest(sources)
        key = digest({"schema": "1.0", "config": config, "inputs": inputs, "versions": versions, "code": implementation_hash})
        return key, implementation_hash

    def submit(self, config):
        key, implementation = self.fingerprints(config)
        with self._lock, self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT * FROM runs WHERE cache_key=? AND status IN ('queued','running','finalizing','succeeded') ORDER BY created_at DESC", (key,)).fetchall()
            for row in rows:
                if row["status"] == "succeeded":
                    try: self.verify_output(row["run_id"])
                    except (ValueError, OSError, KeyError, json.JSONDecodeError):
                        db.execute("UPDATE runs SET status='failed',error='Cached artifacts failed verification',updated_at=? WHERE run_id=?", (time.time(), row["run_id"]))
                        continue
                return {**self._row(row), "cached": True}
            if db.execute("SELECT COUNT(*) FROM runs WHERE status='queued'").fetchone()[0] >= self.max_queued:
                raise RuntimeError("Queue quota reached")
            if shutil.disk_usage(self.state).free < self.min_free_bytes:
                raise RuntimeError("Insufficient free storage for a new experiment")
            run_id = uuid.uuid4().hex
            now = time.time()
            output = self.path(run_id)
            output.mkdir()
            worker_config = {**config, "run_id": run_id, "cache_key": key, "implementation_hash": implementation}
            (output / "config.json").write_text(json.dumps(worker_config, indent=2))
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,NULL)", (run_id, key, "queued", json.dumps(config), now, now))
            return {"run_id": run_id, "cache_key": key, "status": "queued", "config": config, "created_at": now, "updated_at": now, "error": None, "cached": False}

    def path(self, run_id):
        if len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
            raise KeyError("Unknown run")
        return self.runs_dir / run_id

    def _row(self, row):
        result = dict(row)
        result["config"] = json.loads(result["config"])
        return result

    def get(self, run_id):
        self.path(run_id)
        with self.connection() as db:
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if not row: raise KeyError("Unknown run")
        return self._row(row)

    def list(self, limit=100):
        with self.connection() as db:
            return [self._row(row) for row in db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (min(max(limit, 1), 500),))]

    def _set_status(self, run_id, status, error=None):
        with self.connection() as db:
            db.execute("UPDATE runs SET status=?,error=?,updated_at=? WHERE run_id=?", (status, error, time.time(), run_id))

    def cancel(self, run_id):
        with self._lock:
            run = self.get(run_id)
            if run["status"] in TERMINAL: return run
            item = self._processes.pop(run_id, None)
            if item:
                self._terminate(item[0])
                item[1].close()
            self._set_status(run_id, "cancelled", "Cancelled by user; partial artifacts are not valid results")
            return self.get(run_id)

    def _terminate(self, process):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
            except ProcessLookupError: pass

    def verify_output(self, run_id):
        output = self.path(run_id)
        manifest = json.loads((output / "manifest.json").read_text())
        for name in ("network_hash", "demand_hash", "policy_hash", "schema_version"):
            if not manifest.get(name): raise ValueError(f"Missing manifest identity {name}")
        if manifest.get("run_id") != run_id: raise ValueError("Run identity mismatch")
        json.loads((output / "metrics.json").read_text())
        audit = json.loads((output / "audit.json").read_text())
        if audit.get("conservation_ok") is False or audit.get("conservation_passed") is False or audit.get("passed") is False or audit.get("unexplained_losses", 0) != 0:
            raise ValueError("Conservation audit failed")
        for name, expected in manifest.get("artifact_hashes", {}).items():
            path = (output / name).resolve()
            if not path.is_relative_to(output.resolve()) or not path.is_file() or file_hash(path) != expected:
                raise ValueError("Artifact checksum mismatch")
        for chunk in manifest.get("chunks", []):
            path = (output / chunk["file"]).resolve()
            if not path.is_relative_to(output.resolve()): raise ValueError("Invalid chunk path")
            if not path.is_file() or file_hash(path) != chunk["sha256"]: raise ValueError("Chunk checksum mismatch")
        return manifest

    def _launch(self, run):
        run_id = run["run_id"]
        current_key, _ = self.fingerprints(run["config"])
        if current_key != run["cache_key"]:
            raise RuntimeError("Code, inputs or dependencies changed while queued; resubmit against the new version")
        output = self.path(run_id)
        log = (output / "worker.log").open("ab")
        env = {**os.environ, "PYTHONPATH": str(self.root / "src"), "TRAFFIC_WORKER_MEMORY_MB": str(self.worker_memory_mb)}
        process = subprocess.Popen([sys.executable, "-m", "traffic_twin.worker", "--config", str(output / "config.json"), "--output", str(output)], cwd=self.root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self._processes[run_id] = (process, log, time.monotonic())
        self._set_status(run_id, "running")

    def _tick(self):
        with self._lock:
            for run_id, (process, log, started) in list(self._processes.items()):
                reason = None
                if time.monotonic() - started > self.timeout_seconds: reason = "Worker wall-time budget exceeded"
                size = sum(p.stat().st_size for p in self.path(run_id).rglob("*") if p.is_file())
                if size > self.max_run_bytes: reason = "Worker output storage budget exceeded"
                if shutil.disk_usage(self.state).free < self.min_free_bytes: reason = "Free storage reserve reached"
                if reason:
                    self._terminate(process)
                    self._set_status(run_id, "failed", reason)
                elif process.poll() is None: continue
                elif process.returncode:
                    self._set_status(run_id, "failed", f"Worker exited with code {process.returncode}; see worker log")
                else:
                    self._set_status(run_id, "finalizing")
                    try:
                        self.verify_output(run_id)
                        self._set_status(run_id, "succeeded")
                    except Exception as exc:
                        self._set_status(run_id, "failed", f"Output verification failed: {exc}")
                log.close()
                del self._processes[run_id]
            if self._stop.is_set(): return
            for run in reversed(self.list(500)):
                if len(self._processes) >= self.max_workers: break
                if run["status"] == "queued":
                    try: self._launch(run)
                    except Exception as exc: self._set_status(run["run_id"], "failed", f"Worker launch failed: {exc}")

    def _loop(self):
        while not self._stop.is_set():
            try: self._tick()
            except Exception as exc:
                # Keep queue alive; store a bounded administrative diagnostic.
                (self.state / "scheduler.error").write_text(str(exc)[:4000])
            self._stop.wait(0.25)

    def status(self):
        return {"max_workers": self.max_workers, "running": len(self._processes), "max_queued": self.max_queued,
                "max_run_bytes": self.max_run_bytes, "timeout_seconds": self.timeout_seconds,
                "worker_memory_mb": self.worker_memory_mb, "free_bytes": shutil.disk_usage(self.state).free}
