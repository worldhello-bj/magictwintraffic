import libsumo as a,json,math
from pathlib import Path
args=['sumo','-n','networks/joined_nijiaqiao_access_v2/network.net.xml','--load-state','runs/pressure_links_S0_am_42_v2/state_1200.xml.gz','--begin','1200','--step-length','0.5','--no-step-log','true','--no-warnings','true','--time-to-teleport','-1'];v='internal_42_zone_1_2_0021'
a.start(args);p=a.vehicle.getPosition(v);c=[x for x in a.vehicle.getIDList() if x!=v and math.dist(p,a.vehicle.getPosition(x))<30 and a.vehicle.getSpeed(x)<.1];a.close();res=[]
for x in c:
 a.start(args);removed={'id':x,'lane':a.vehicle.getLaneID(x),'position':a.vehicle.getLanePosition(x),'leader':a.vehicle.getLeader(x,100),'foes':a.vehicle.getJunctionFoes(x,50)};a.vehicle.remove(x)
 for i in range(10):a.simulationStep()
 exists=v in a.vehicle.getIDList();res.append({'removed_vehicle':removed,'target_remaining':exists,'target_lane':a.vehicle.getLaneID(v) if exists else None,'target_pos':a.vehicle.getLanePosition(v) if exists else None,'target_speed':a.vehicle.getSpeed(v) if exists else None});a.close()
Path('docs/evidence/north_exit_single_blocker_probe.json').write_text(json.dumps(res,indent=2));print([(r['removed_vehicle']['id'],r['target_remaining'],r['target_lane'],r['target_pos']) for r in res])
