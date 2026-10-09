"""Real isolated SUMO smoke; skip only when the generated network/dependencies are absent."""
import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from traffic_twin.api import create_app

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def real_api(tmp_path):
    pytest.importorskip('libsumo')
    if not (ROOT / 'networks/baseline/network.net.xml').exists():
        pytest.skip('Build the genuine OSM network first')
    with TestClient(create_app(ROOT, tmp_path, min_free_bytes=0)) as client:
        yield client

def await_terminal(client, run_id):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        run = client.get(f'/api/runs/{run_id}').json()
        if run['status'] in ('succeeded','failed','cancelled'):
            return run
        time.sleep(.1)
    pytest.fail('Real smoke worker did not terminate within 45 seconds')

def test_real_worker_artifacts_cache_and_cancel(real_api):
    c = real_api
    config = {'duration_seconds':30,'demand_end_seconds':20,'rate_per_gate':20,'trajectory':True}
    first = c.post('/api/runs', json=config)
    assert first.status_code == 200, first.text
    rid = first.json()['run_id']
    assert c.post('/api/runs', json=config).json()['run_id'] == rid
    result = await_terminal(c, rid)
    assert result['status'] == 'succeeded', c.get(f'/api/runs/{rid}/logs').text
    manifest = c.get(f'/api/runs/{rid}/manifest').json()
    assert manifest['run_id'] == rid and manifest['artifact_hashes']
    assert manifest['hardware']['peak_rss_kib'] > 0
    assert 'Linux KiB' in manifest['hardware']['peak_rss_source']
    assert c.get(f'/api/runs/{rid}/signals').status_code == 200
    assert c.get(f'/api/runs/{rid}/network').status_code == 200
    for chunk in manifest['chunks']:
        r = c.get(f'/api/runs/{rid}/chunks/{chunk["id"]}')
        import gzip
        data = gzip.decompress(r.content) if chunk.get("compression") == "gzip" else r.content
        assert r.status_code == 200 and len(data) == chunk['record_count'] * 32
        assert chunk['run_id'] == rid
    assert c.post('/api/runs', json=config).json()['run_id'] == rid
    pending = c.post('/api/runs', json={**config,'seed':43,'duration_seconds':9900,'demand_end_seconds':8100}).json()
    assert c.post(f'/api/runs/{pending["run_id"]}/cancel').json()['status'] == 'cancelled'
    assert c.get(f'/api/runs/{pending["run_id"]}/metrics').status_code == 409

def test_real_unknown_od_never_queued(real_api):
    config = {'od':[{'origin_gate':'invented_origin','destination_gate':'invented_destination','rate_per_hour':120}]}
    response = real_api.post('/api/runs', json=config)
    assert response.status_code == 422, response.text
    assert real_api.get('/api/runs').json()['runs'] == []
