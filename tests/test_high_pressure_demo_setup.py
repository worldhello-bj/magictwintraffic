import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
module=load('ensure_high_pressure_demo')
def test_verified_pressure_demo_is_reused(tmp_path,monkeypatch):
 monkeypatch.setattr(module,'available',lambda *_:True)
 monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('Must not regenerate verified replay'))
 module.ensure(tmp_path)
def test_missing_demo_builds_network_then_seed42_only(tmp_path,monkeypatch):
 states=iter([False,True]);calls=[]
 monkeypatch.setattr(module,'available',lambda *_:next(states));monkeypatch.setattr(module.subprocess,'run',lambda a,**k:calls.append(a));module.ensure(tmp_path)
 assert len(calls)==4
 assert calls[0][1].endswith('build_internal_network.py') and calls[1][1].endswith('build_access_network.py')
 assert calls[2][1].endswith('build_north_surface_network.py')
 assert calls[3][-4:]==['--seeds','42','--workers','2']
def test_verification_failure_is_not_silent(tmp_path,monkeypatch):
 monkeypatch.setattr(module,'available',lambda *_:False);monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:None)
 with pytest.raises(RuntimeError,match='verification'):module.ensure(tmp_path)
def test_missing_assets_unavailable(tmp_path):
 assert not module.available(tmp_path)
def test_lane_projection_follows_bent_geometry():
 p=load('analyze_high_pressure').project
 assert p(5,1,[[0,0],[10,0],[10,10]])==5
 assert p(11,6,[[0,0],[10,0],[10,10]])==16
 assert p(-3,0,[[0,0],[10,0]])==0
