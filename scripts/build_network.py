#!/usr/bin/env python3
import sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from traffic_twin.gis import build_network
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--download',action='store_true');a=p.parse_args();n=build_network(a.download);print(json.dumps({k:len(n[k]) for k in ['lanes','edges','junctions','gates','buildings','traffic_lights']},indent=2))
