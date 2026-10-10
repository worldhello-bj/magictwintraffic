#!/usr/bin/env python3
"""Capture actual long-wait vehicles before SUMO closes; no traffic mutation."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def diagnose(config,output):
    import libsumo as api
    from traffic_twin.evaluator import Evaluator
    from traffic_twin.simulation import run_simulation
    from traffic_twin.gis import write_json
    original=Evaluator.step;snapshots=[]
    def observed(self,time,*args):
        original(self,time,*args)
        if time%300:return
        rows=[]
        for vehicle in api.vehicle.getIDList():
            if api.vehicle.getWaitingTime(vehicle)<=100:continue
            rows.append(dict(id=vehicle,road=api.vehicle.getRoadID(vehicle),lane=api.vehicle.getLaneID(vehicle),pos=api.vehicle.getLanePosition(vehicle),wait=api.vehicle.getWaitingTime(vehicle),tls=api.vehicle.getNextTLS(vehicle),leader=api.vehicle.getLeader(vehicle),route=api.vehicle.getRoute(vehicle),route_index=api.vehicle.getRouteIndex(vehicle),stop=api.vehicle.getStopState(vehicle)))
        snapshots.append(dict(time=time,vehicles=rows))
    Evaluator.step=observed
    try:
        manifest=run_simulation(config,output)
        write_json(Path(output)/'long_wait_snapshots.json',dict(network_hash=manifest['network_hash'],demand_hash=manifest['demand_hash'],config=config,snapshots=snapshots))
    finally:Evaluator.step=original


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    output=Path(args.output)
    if output.exists():parser.error('Choose a new output directory; diagnostics never overwrite existing runs')
    diagnose(json.loads(Path(args.config).read_text()),output)
