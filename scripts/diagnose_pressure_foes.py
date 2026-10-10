#!/usr/bin/env python3
"""Read-only detailed junction foes capture on exact final demand/control inputs."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import libsumo as api
from traffic_twin.evaluator import Evaluator
from traffic_twin.simulation import run_simulation
source=ROOT/'runs/high_pressure_S0_am_42_v2';config=json.loads((source/'manifest.json').read_text())['config'];config.update(run_id='pressure_foes_S0_am_42_v2',trajectory=False)
output=ROOT/'runs'/config['run_id'];assert not output.exists()
original=Evaluator.step;snapshots=[]
def observed(self,time,*args):
 original(self,time,*args)
 if time%300:return
 rows=[]
 for v in api.vehicle.getIDList():
  if api.vehicle.getWaitingTime(v)<100:continue
  rows.append(dict(id=v,road=api.vehicle.getRoadID(v),lane=api.vehicle.getLaneID(v),pos=api.vehicle.getLanePosition(v),wait=api.vehicle.getWaitingTime(v),leader100=api.vehicle.getLeader(v,100),foes=api.vehicle.getJunctionFoes(v,50),tls=api.vehicle.getNextTLS(v),route=api.vehicle.getRoute(v),route_index=api.vehicle.getRouteIndex(v),stop=api.vehicle.getStopState(v)))
 snapshots.append(dict(time=time,vehicles=rows));print(time,len(rows),flush=True)
Evaluator.step=observed
try:
 m=run_simulation(config,output);old=json.loads((source/'manifest.json').read_text());assert m['network_hash']==old['network_hash'];assert m['demand_hash']==old['demand_hash']
 result={'network_hash':m['network_hash'],'demand_hash':m['demand_hash'],'reference_run':source.name,'diagnostic_run':output.name,'read_only_diagnostics':True,'snapshots':snapshots};(output/'junction_foe_snapshots.json').write_text(json.dumps(result,indent=2))
finally:Evaluator.step=original
