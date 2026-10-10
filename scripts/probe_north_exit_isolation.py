import libsumo as a,json
from pathlib import Path
root=Path.cwd();p=root/'runs/pressure_links_S0_am_42_v2/state_1200.xml.gz';n=root/'networks/joined_nijiaqiao_access_v2/network.net.xml';v='internal_42_zone_1_2_0021';results=[]
for mode in ['saved_state_unmodified','saved_state_other_active_vehicles_removed','fresh_isolated']:
 args=['sumo','-n',str(n),'--step-length','0.5','--no-step-log','true','--time-to-teleport','-1','--no-warnings','true']
 if mode!='fresh_isolated':args+=['--load-state',str(p),'--begin','1200']
 a.start(args)
 if mode=='saved_state_other_active_vehicles_removed':
  for x in a.vehicle.getIDList():
   if x!=v:a.vehicle.remove(x)
 if mode=='fresh_isolated':
  a.vehicletype.copy('DEFAULT_VEHTYPE','car');a.vehicletype.setLength('car',4.6);a.vehicletype.setMinGap('car',2.5);a.route.add('probe',['131319574#15','136005112#0']);a.vehicle.add(v,'probe',typeID='car',departLane='1',departSpeed='0')
 seen=[];arrived=False
 for i in range(120):
  a.simulationStep()
  if v in a.simulation.getArrivedIDList():arrived=True;break
  if v in a.vehicle.getIDList() and i%20==0:seen.append([a.simulation.getTime(),a.vehicle.getRoadID(v),a.vehicle.getLaneID(v),a.vehicle.getLanePosition(v),a.vehicle.getSpeed(v)])
 results.append({'mode':mode,'arrived_within60s':arrived,'observations':seen});a.close()
(root/'docs/evidence/north_exit_isolation_probe.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
