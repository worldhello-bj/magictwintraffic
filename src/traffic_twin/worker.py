"""Fixed isolated worker entrypoint, never executes client-selected code."""
import argparse
import json
from pathlib import Path
import os
import sys
import resource

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Linux workers die with their API owner, avoiding orphan simulations on crashes.
    if sys.platform == "linux":
        import ctypes
        import signal
        parent = os.getppid()
        ctypes.CDLL(None).prctl(1, signal.SIGTERM)
        if os.getppid() != parent:
            raise SystemExit("Scheduler exited before worker initialization")
    budget = int(os.environ.get("TRAFFIC_WORKER_MEMORY_MB", "4096")) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (budget, budget))
    from traffic_twin.simulation import run_simulation
    config = json.loads(args.config.read_text())
    run_simulation(config, args.output)
    manifest_path = args.output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["run_id"] = config["run_id"]
    manifest["cache_key"] = config["cache_key"]
    manifest["implementation_hash"] = config["implementation_hash"]
    manifest.setdefault("hardware", {}).update(peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, peak_rss_source="getrusage(RUSAGE_SELF).ru_maxrss; Linux KiB")
    from traffic_twin.scheduler import file_hash
    manifest["artifact_hashes"] = {name: file_hash(args.output / name) for name in ("metrics.json", "audit.json", "network.json", "demand.json", "trips.json", "timeseries.json", "events.json", "signals.json") if (args.output / name).is_file()}
    for chunk in manifest.get("chunks", []):
        chunk.update(run_id=config["run_id"], network_hash=manifest["network_hash"], schema_version=manifest["schema_version"], dictionary_version=manifest["network_hash"])
        chunk.setdefault("compression", "none")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
