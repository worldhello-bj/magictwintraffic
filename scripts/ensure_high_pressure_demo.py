#!/usr/bin/env python3
"""Verify published v3 physics provenance and regenerate only missing seed-42 replay pairs."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IDS=[f'high_pressure_{policy}_{period}_42_v3' for period in ('am','pm') for policy in ('S0','S7')]
def available(root=ROOT):
 try:
  config=json.loads((root/'scenarios/high_pressure_v3.json').read_text());canonical=json.loads((root/'data/canonical'/f"{config['network_variant']}.json").read_text());catalog=json.loads((root/'web/public/data/catalog.json').read_text());entries={x['run_id']:x for x in catalog['runs']}
  if [x['run_id'] for x in catalog['runs'][:4]]!=IDS:return False
  netfile=root/'networks'/config['network_variant']/'network.net.xml'
  if hashlib.sha256(netfile.read_bytes()).hexdigest()!=canonical['network_hash']:return False
  for run_id in IDS:
   folder=root/'web/public/data/runs'/run_id;m=json.loads((folder/'manifest.json').read_text());a=json.loads((folder/'audit.json').read_text())
   if any(m['config'].get(k)!=v for k,v in config.items()):return False
   if m['network_hash']!=canonical['network_hash'] or json.loads((folder/m['network']).read_text())['network_hash']!=m['network_hash']:return False
   if not a['conservation_passed'] or not a['parked_stock_conservation_passed'] or a['collisions'] or a['teleports']:return False
   for key in ('signals','signal_topology','queue_hotspots','stock_timeseries','internal_zones','od_matrix','metrics','timeseries'):json.loads((folder/m[key]).read_text())
   if not (folder/m['od_csv']).is_file() or not m['chunks']:return False
   for chunk in m['chunks']:
    if hashlib.sha256((folder/chunk['file']).read_bytes()).hexdigest()!=chunk['sha256']:return False
  for period in ('am','pm'):
   pair=[json.loads((root/'web/public/data/runs'/f'high_pressure_{p}_{period}_42_v3'/'manifest.json').read_text())['demand_hash'] for p in ('S0','S7')]
   if len(set(pair))!=1:return False
  return True
 except (OSError,ValueError,KeyError,TypeError):return False

def ensure(root=ROOT):
 if available(root):print('High-pressure v3 seed-42 AM/PM paired replays verified.');return
 python=root/'.venv/bin/python';python=str(python) if python.exists() else sys.executable
 subprocess.run([python,str(root/'scripts/build_internal_network.py')],cwd=root,check=True)
 subprocess.run([python,str(root/'scripts/build_access_network.py')],cwd=root,check=True)
 subprocess.run([python,str(root/'scripts/build_north_surface_network.py')],cwd=root,check=True)
 print('Preparing genuine high-pressure SUMO replay pairs; first generation may take several minutes.',flush=True)
 subprocess.run([python,str(root/'scripts/run_high_pressure_demo.py'),'--seeds','42','--workers','2'],cwd=root,check=True)
 if not available(root):raise RuntimeError('High-pressure replay asset verification failed')
if __name__=='__main__':ensure()
