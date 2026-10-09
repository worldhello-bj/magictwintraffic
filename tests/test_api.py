import json
import sys
import types
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from traffic_twin.api import create_app
from traffic_twin.scheduler import Scheduler, file_hash
from traffic_twin.schemas import Scenario

@pytest.fixture
def env(tmp_path, monkeypatch):
    (tmp_path / "networks/baseline").mkdir(parents=True)
    (tmp_path / "networks/baseline/network.net.xml").write_text("<net/>")
    (tmp_path / "data/canonical").mkdir(parents=True)
    (tmp_path / "data/canonical/network.json").write_text(json.dumps({"network_hash": "network-a"}))
    simulation = types.ModuleType("traffic_twin.simulation")
    simulation.validate_config = lambda config: ["S2 unavailable"] if config["policy"] == "S2" else []
    monkeypatch.setitem(sys.modules, "traffic_twin.simulation", simulation)
    app = create_app(tmp_path, start_scheduler=False, min_free_bytes=0)
    with TestClient(app) as client:
        yield tmp_path, app.state.scheduler, client

def finish(scheduler, run_id, demand="demand-a", network="network-a"):
    out = scheduler.path(run_id)
    (out / "trajectory").mkdir(exist_ok=True)
    chunk = out / "trajectory/chunk000.bin"
    chunk.write_bytes(b"\0" * 32)
    (out / "manifest.json").write_text(json.dumps({"run_id": run_id, "schema_version": "1.0", "network_hash": network, "demand_hash": demand, "policy_hash": "policy", "chunks": [{"id": "0", "file": "trajectory/chunk000.bin", "sha256": file_hash(chunk)}]}))
    (out / "metrics.json").write_text('{"tstt": 10}')
    (out / "audit.json").write_text('{"conservation_ok": true}')
    scheduler._set_status(run_id, "succeeded")

def test_validate_and_allowlist(env):
    _, _, client = env
    assert client.post("/api/scenarios/validate", json={}).json()["valid"]
    for payload in ({"command": "rm -rf /"}, {"network_id": "../../etc"}, {"duration_seconds": 1}, {"step_seconds": 1}, {"policy": "S9"}):
        assert client.post("/api/runs", json=payload).status_code == 422
    assert client.post("/api/runs", json={"policy": "S2"}).status_code == 422

def test_idempotent_submit_cancel_and_retry(env):
    _, scheduler, client = env
    first = client.post("/api/runs", json={}).json()
    again = client.post("/api/runs", json={}).json()
    assert first["run_id"] == again["run_id"] and again["cached"]
    assert client.get(f"/api/runs/{first['run_id']}/metrics").status_code == 409
    assert client.post(f"/api/runs/{first['run_id']}/cancel").json()["status"] == "cancelled"
    assert client.post("/api/runs", json={}).json()["run_id"] != first["run_id"]

def test_hash_cache_invalidation_and_corruption(env):
    root, scheduler, client = env
    a = client.post("/api/runs", json={}).json()["run_id"]
    finish(scheduler, a)
    assert client.post("/api/runs", json={}).json()["run_id"] == a
    (scheduler.path(a) / "trajectory/chunk000.bin").write_bytes(b"bad")
    b = client.post("/api/runs", json={}).json()["run_id"]
    assert b != a and scheduler.get(a)["status"] == "failed"
    (root / "networks/baseline/network.net.xml").write_text("<net changed='true'/>")
    assert client.post("/api/runs", json={}).json()["run_id"] != b

def test_read_guarded_chunks_network_and_compare(env):
    _, scheduler, client = env
    a = client.post("/api/runs", json={}).json()["run_id"]
    b = client.post("/api/runs", json={"seed": 43}).json()["run_id"]
    finish(scheduler, a)
    finish(scheduler, b)
    assert client.get(f"/api/runs/{a}/chunks/0").content == b"\0" * 32
    assert client.get(f"/api/runs/{a}/network").status_code == 200
    assert client.get(f"/api/compare?run_a={a}&run_b={b}").status_code == 200
    finish(scheduler, b, demand="other")
    assert client.get(f"/api/compare?run_a={a}&run_b={b}").status_code == 409
    finish(scheduler, b, network="other")
    assert client.get(f"/api/runs/{b}/network").status_code == 409
    assert client.get("/api/runs/not-a-run").status_code == 404

def test_queue_and_request_quotas(env):
    _, scheduler, client = env
    scheduler.max_queued = 1
    assert client.post("/api/runs", json={}).status_code == 200
    assert client.post("/api/runs", json={"seed": 3}).status_code == 429
    assert client.post("/api/runs", content="x" * 65537).status_code == 413

def test_auth(env, monkeypatch):
    _, _, client = env
    monkeypatch.setenv("TRAFFIC_API_TOKEN", "test-token")
    assert client.get("/api/health").status_code == 401
    assert client.get("/api/health", headers={"authorization": "Bearer test-token"}).status_code == 200

def test_restart_marks_interrupted_failed(tmp_path):
    scheduler = Scheduler(tmp_path, min_free_bytes=0)
    run = scheduler.submit(Scenario().engine_config())
    scheduler._set_status(run["run_id"], "running")
    scheduler.start()
    try:
        assert scheduler.get(run["run_id"])["status"] == "failed"
        second = Scheduler(tmp_path, min_free_bytes=0)
        with pytest.raises(RuntimeError): second.start()
    finally: scheduler.stop()

def test_worker_launch_failure_is_failed(tmp_path):
    scheduler = Scheduler(tmp_path, min_free_bytes=0)
    run = scheduler.submit(Scenario().engine_config())
    scheduler._launch = lambda run: (_ for _ in ()).throw(OSError("intentional"))
    scheduler._tick()
    assert scheduler.get(run["run_id"])["status"] == "failed"

def test_cancel_running_worker_terminates_process(tmp_path):
    import subprocess
    import time
    scheduler = Scheduler(tmp_path, min_free_bytes=0)
    run = scheduler.submit(Scenario().engine_config())
    log = (scheduler.path(run['run_id']) / 'worker.log').open('wb')
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True, stdout=log, stderr=log)
    scheduler._processes[run['run_id']] = (process, log, time.monotonic())
    scheduler._set_status(run['run_id'], 'running')
    assert scheduler.cancel(run['run_id'])['status'] == 'cancelled'
    assert process.poll() is not None
    assert not scheduler._processes

def test_wall_budget_fails_running_worker(tmp_path):
    import subprocess
    import time
    scheduler = Scheduler(tmp_path, min_free_bytes=0, timeout_seconds=0)
    run = scheduler.submit(Scenario().engine_config())
    log = (scheduler.path(run['run_id']) / 'worker.log').open('wb')
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True, stdout=log, stderr=log)
    scheduler._processes[run['run_id']] = (process, log, time.monotonic() - 1)
    scheduler._set_status(run['run_id'], 'running')
    scheduler._tick()
    assert scheduler.get(run['run_id'])['status'] == 'failed'
    assert 'wall-time' in scheduler.get(run['run_id'])['error']
    assert process.poll() is not None

def test_od_bounds_and_unknown_fields(env):
    _, _, client = env
    base = {'origin_gate':'N_entry_1','destination_gate':'S_exit_1','rate_per_hour':120}
    assert client.post('/api/scenarios/validate', json={'od':[base]}).status_code == 200
    for changed in ({'interval_end':299}, {'interval_start':300,'interval_end':300}, {'rate_per_hour':-1}, {'command':'anything'}):
        assert client.post('/api/scenarios/validate', json={'od':[{**base, **changed}]}).status_code == 422

def test_artifact_paths_and_corrupt_metrics_fail_verification(env):
    _, scheduler, client = env
    rid = client.post('/api/runs', json={}).json()['run_id']
    finish(scheduler, rid)
    path = scheduler.path(rid) / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest['chunks'][0]['file'] = '../outside.bin'
    path.write_text(json.dumps(manifest))
    assert client.get(f'/api/runs/{rid}/chunks/0').status_code == 409
    with pytest.raises(ValueError): scheduler.verify_output(rid)
    finish(scheduler, rid)
    (scheduler.path(rid) / 'metrics.json').write_text('not-json')
    with pytest.raises(ValueError): scheduler.verify_output(rid)

def test_compare_rejects_anomalous_or_changed_implementation(env):
    _, scheduler, client = env
    a = client.post('/api/runs', json={}).json()['run_id']
    b = client.post('/api/runs', json={'seed':43}).json()['run_id']
    finish(scheduler,a); finish(scheduler,b)
    p = scheduler.path(b) / 'manifest.json'
    m = json.loads(p.read_text()); m['valid_for_ranking'] = False; p.write_text(json.dumps(m))
    assert client.get(f'/api/compare?run_a={a}&run_b={b}').status_code == 409
    m['valid_for_ranking'] = True; m['implementation_hash'] = 'changed'; p.write_text(json.dumps(m))
    assert client.get(f'/api/compare?run_a={a}&run_b={b}').status_code == 409

def test_bounded_policy_parameters(env):
    _, _, client = env
    assert client.post('/api/scenarios/validate', json={'policy':'S3','policy_parameters':{'green_extension_seconds':8,'downstream_occupancy_threshold':65}}).status_code == 200
    for values in ({'unknown':1},{'green_extension_seconds':16},{'managed_curb_stop_seconds':-1},{'downstream_occupancy_threshold':101}):
        assert client.post('/api/scenarios/validate', json={'policy':'S3','policy_parameters':values}).status_code == 422

def test_downstream_constraint_bounds(env):
    _, _, client = env
    config = {'downstream_block':{'gate_id':'E_exit_1','start_seconds':10,'end_seconds':50,'speed_m_s':.1}}
    assert client.post('/api/scenarios/validate', json=config).status_code == 200
    for changed in ({'speed_m_s':0},{'end_seconds':700},{'start_seconds':60}):
        bad = {'downstream_block':{**config['downstream_block'],**changed}}
        assert client.post('/api/scenarios/validate', json=bad).status_code == 422

def test_nonfinite_and_coerced_numbers_rejected(env):
    _, _, client = env
    for body in ('{"demand_scale":NaN}', '{"duration_seconds":Infinity}'):
        assert client.post('/api/runs', content=body, headers={'content-type':'application/json'}).status_code == 400
    for payload in ({'seed':True}, {'seed':'42'}, {'demand_scale':'1'}):
        assert client.post('/api/runs', json=payload).status_code == 422

def test_queued_job_rejects_mutated_inputs(env):
    root, scheduler, client = env
    rid = client.post('/api/runs', json={}).json()['run_id']
    (root / 'networks/baseline/network.net.xml').write_text('<net changed="yes"/>')
    scheduler._tick()
    assert scheduler.get(rid)['status'] == 'failed'
    assert 'changed while queued' in scheduler.get(rid)['error']

def test_signals_require_completed_run(env):
    _, scheduler, client = env
    rid = client.post('/api/runs', json={}).json()['run_id']
    assert client.get(f'/api/runs/{rid}/signals').status_code == 409
    finish(scheduler,rid)
    states = [{'time':0,'id':'test_signal','state':'Gr'}]
    (scheduler.path(rid) / 'signals.json').write_text(json.dumps(states))
    assert client.get(f'/api/runs/{rid}/signals').json() == states
