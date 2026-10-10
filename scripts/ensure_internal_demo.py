#!/usr/bin/env python3
"""Restore/generate the separate building OD demo on a clean checkout."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]


def available(root=ROOT):
    config=json.loads((root/'scenarios/internal_moderate_demo.json').read_text())
    try:
        catalog=json.loads((root/'web/public/data/catalog.json').read_text())
        ids=[f'internal_moderate_{policy}_{period}_42_v1' for period in ('am','pm') for policy in ('S0','S7')]
        if [e['run_id'] for e in catalog['runs'][:4]]!=ids:return False
        if not any(e['run_id']=='internal_demo_S0_am_42_v1' for e in catalog['runs']):return False
        for run_id in ids+['internal_demo_S0_am_42_v1']:
            expected_config=config if run_id.startswith('internal_moderate_') else json.loads((root/'scenarios/internal_peak_demo.json').read_text())
            folder=root/'web/public/data/runs'/run_id
            manifest=json.loads((folder/'manifest.json').read_text())
            if any(manifest['config'].get(k)!=v for k,v in expected_config.items()):return False
            audit=json.loads((folder/'audit.json').read_text())
            if not audit.get('parked_stock_conservation_passed') or audit['teleports'] or audit['collisions']:return False
            for key in ('signals','signal_topology','queue_hotspots','stock_timeseries','internal_zones','od_matrix','metrics','timeseries'):
                json.loads((folder/manifest[key]).read_text())
            if not (folder/manifest['od_csv']).is_file() or not (folder/manifest['network']).is_file():return False
            if not manifest['chunks']:return False
            for chunk in manifest['chunks']:
                if hashlib.sha256((folder/chunk['file']).read_bytes()).hexdigest()!=chunk['sha256']:return False
        return True
    except (OSError,ValueError,KeyError,TypeError):return False


def ensure(root=ROOT):
    if available(root):
        print('Internal AM/PM OD, signal and stock demo assets verified.');return
    python=root/'.venv/bin/python'
    print('Preparing genuine SUMO building OD demos; the first build may take several minutes.',flush=True)
    subprocess.run([str(python) if python.exists() else sys.executable,str(root/'scripts/run_internal_demo.py')],cwd=root,check=True)
    if not available(root):raise RuntimeError('Internal demo did not produce verified offline assets')


if __name__=='__main__':ensure()
