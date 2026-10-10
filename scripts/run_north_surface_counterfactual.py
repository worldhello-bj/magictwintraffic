#!/usr/bin/env python3
"""Same-OD 360-demand north-surface topology counterfactual; does not promote a default."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
def main():
 from diagnose_internal_deadlock import diagnose
 from analyze_high_pressure import summarize
 from build_north_surface_network import build
 build()
 source=ROOT/'runs/high_pressure_S0_am_42_v2';old=json.loads((source/'manifest.json').read_text());c=old['config'].copy();c.update(network_variant='joined_north_surface_v3',run_id='north_surface_counterfactual_S0_am_42_v3_movementfix');p=ROOT/'runs'/c['run_id']
 if not p.exists():diagnose(c,p)
 elif not (p/'manifest.json').exists() or json.loads((p/'manifest.json').read_text())['config']!=c:raise ValueError('Existing counterfactual incomplete or config mismatch; preserve it')
 x=summarize(p);(p/'high_pressure_analysis.json').write_text(json.dumps(x,ensure_ascii=False,indent=2))
 new=json.loads((p/'manifest.json').read_text());assert new['network_hash']==json.loads((ROOT/'data/canonical/joined_north_surface_v3.json').read_text())['network_hash'];assert old['demand_hash']==new['demand_hash'];before=json.loads((source/'high_pressure_analysis.json').read_text())
 evidence=dict(status='Topology counterfactual, not same-network policy comparison and not field calibration.',same_demand_hash=old['demand_hash'],same_exogenous_inventory=True,same_ids_departure_times_origin_destination_behavior_seeds=True,trajectory_interventions='None: ordinary SUMO safe insertion, no vehicle deletion, no teleport or safety changes in either compared run.',source_run_id=old['run_id'],target_run_id=new['run_id'],source_network_hash=old['network_hash'],target_network_hash=new['network_hash'],source=before,target=x,interpretation='Read in combination with movement and grade-separation audit before promotion; compare pressure and recovery without reducing demand.')
 (ROOT/'docs/evidence/north_surface_counterfactual.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2));print(json.dumps(dict(same_demand=True,before_final=before['final_state'],after_final=x['final_state'],clearance=x['clearance_time_seconds'])),flush=True)
if __name__=='__main__':main()
