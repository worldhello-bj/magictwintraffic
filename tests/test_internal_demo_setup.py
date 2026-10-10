import importlib.util
import json
from pathlib import Path
import pytest

SPEC=importlib.util.spec_from_file_location('ensure_internal_demo',Path(__file__).resolve().parents[1]/'scripts/ensure_internal_demo.py')
module=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(module)


def test_reuses_verified_internal_demo(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'available',lambda *_:True)
    monkeypatch.setattr(module.subprocess,'run',lambda *_args,**_kwargs:pytest.fail('Verified demo must not rerun'))
    module.ensure(tmp_path)


def test_generates_missing_internal_demo_then_verifies(tmp_path,monkeypatch):
    state=iter([False,True]);calls=[]
    monkeypatch.setattr(module,'available',lambda *_:next(state))
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:calls.append((a,k)))
    module.ensure(tmp_path)
    assert len(calls)==1 and calls[0][0][0][-1].endswith('scripts/run_internal_demo.py')


def test_internal_demo_missing_postcondition_is_failure(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'available',lambda *_:False)
    monkeypatch.setattr(module.subprocess,'run',lambda *_args,**_kwargs:None)
    with pytest.raises(RuntimeError,match='verified'):module.ensure(tmp_path)
