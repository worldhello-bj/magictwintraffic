# Experiment service and offline replay

## Run

The backend needs Python 3.11+ on Linux (process-group cancellation, Linux parent-death signaling and resource limits). Windows users can use Docker Desktop or WSL. The static replay needs only any local HTTP server and works independently of the backend.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install --no-deps -e .
./scripts/start_backend.sh
# Separate offline mode; first build web/dist as described in README
./scripts/start_replay.sh
```

The API binds localhost:8000 by default, with one process owning the SQLite queue. Never add Uvicorn workers to this scheduler. `docker compose up --build` binds the published port to localhost. Set a strong `TRAFFIC_API_TOKEN` and deploy a TLS/authenticated reverse proxy before any public exposure. The application checks `Authorization: Bearer <token>` when a token is configured. Do not put secrets in tracked files. Hosted multi-user access/account quotas are outside the prototype.

`TRAFFIC_STATE_DIR` selects an administrator-owned state directory. Clients cannot choose server paths. SQLite and isolated run directories live there; default is `var/`. Storage is persistent across server restarts. Queued work resumes; interrupted running/finalizing jobs become failed, preserving diagnostic logs. Explicitly resubmitting is required to retry a failed or cancelled run. Linux workers exit if their API owner dies.

## Contract

- `GET /api/health`, `/api/policies`, `/api/networks`
- `POST /api/scenarios/validate`, `POST /api/runs`
- `GET /api/runs`, `/api/runs/{run_id}`
- `POST /api/runs/{run_id}/cancel`
- `GET /api/runs/{run_id}/manifest`, `/network`, `/metrics`, `/timeseries`, `/audit`, `/logs`
- `GET /api/runs/{run_id}/chunks/{chunk_id}`
- `GET /api/networks/{network_hash}/manifest`
- `GET /api/compare?run_a=...&run_b=...`

OpenAPI schemas are served at `/docs` and `/openapi.json`. A minimal request is `{"policy":"S0","seed":42,"duration_seconds":600,"trajectory":true}`. This is a short demonstration, not the plan's formal 9,900-second study. `duration_seconds` is total simulation time; omitted demand_end_seconds becomes duration minus drain. Explicit warmup/demand/drain windows should be fixed before comparative studies. Rate units are vehicles/hour. Optional `od` rows contain origin_gate, destination_gate, rate_per_hour, interval_start and interval_end; intervals align to 300 seconds and must fit the demand window. Unknown fields, commands and paths fail validation.

Optional `policy_parameters` accepts `green_extension_seconds` (1–15, S1/S3/S6/S7), `downstream_occupancy_threshold` (10–90 percent, S3/S6/S7), and `managed_curb_stop_seconds` (0–30, S5/S7). Parameters outside the selected policy are rejected.

Policy support comes from the scenario compiler; an unsupported family or infeasible OD cannot be silently accepted. Configurations are bounded to 14,400 seconds, 0.25/0.5-second step, at most 1,000 OD rows, a 5× demand scale and 1,800 vehicles/hour per input. More demanding experiments require deliberate server-side budget review, not a client override.

The cache key contains all normalized inputs, network/canonical/demand/scenario bytes, dependency versions, Python version, all Python implementation bytes and dependency manifests. Exact duplicate active/verified requests return the same run. Cache artifacts are verified before reuse. Changed code, network or recording configuration invalidates the cache.

Completed results require a successful worker exit, manifest identities, metrics, audit and verified trajectory checksums. Cancelled, failed and partial results cannot be requested as completed metrics or replay. Comparison requires identical exogenous demand hashes, schema and evaluation timing/step; topology differences are explicitly marked as structural changes. A single paired run is not statistical evidence of superiority.

## Resource limits

Conservative default: one worker, 32 queued requests, one-hour wall time per run, 4 GiB worker address space, 2 GB output per run and a 256 MB free-disk reserve. The scheduler constructor accepts administrator overrides after measured throughput/RSS/storage validation. Its public health response exposes limits and current occupancy. The worker address-space bound includes imported libraries; measure real RSS and increase deliberately for production-scale runs. Output/free-disk budgets are checked each scheduler tick; the maximum between-check overshoot is bounded by the worker's write rate, not a hard filesystem quota. Docker imposes a separate 6 GiB container memory bound. Every experiment preserves a worker log, and logs are served as a bounded final 64 KiB tail.

## Checks

`tests/test_api.py` exercises input rejection, queue quotas, caching and invalidation, cancellation and retry, guarded chunks, network-hash mismatch, demand-pair rejection, authorization, restart recovery and exclusive ownership. The real SUMO worker is separately smoke-tested by submitting through the running application. Container and Windows launcher verification must be reported separately if those runtimes are unavailable.
