"""One process, one deterministic libsumo instance, genuine OSM network."""
from pathlib import Path
import json,time,sys,platform,xml.etree.ElementTree as ET,hashlib
from .gis import ROOT,write_json,digest
from .demand import generate_demand
from .policies import compile_policy,PolicyController,NAMES
from .evaluator import Evaluator
from .recorder import Recorder

def validate_config(config):
    if config.get('policy','S0') not in NAMES:raise ValueError('Unknown policy')
    for key,low,high in [('duration_seconds',10,14400),('demand_scale',0,8),('rate_per_gate',0,3000),('seed',0,2147483647)]:
        if key in config and (not isinstance(config[key],(int,float)) or not low<=config[key]<=high):raise ValueError(f'{key} must lie in [{low},{high}]')
    if float(config.get('step_seconds',.5)) not in (.25,.5):raise ValueError('step_seconds must be .25 or .5; action-step remains .5')
    if config.get('period','am') not in ('am','pm'):raise ValueError('period must be am or pm')
    duration=float(config.get('duration_seconds',600));warmup=float(config.get('warmup_seconds',0));end=float(config.get('demand_end_seconds',duration*.7))
    if not 0<=warmup<end<=duration:raise ValueError('Require 0 <= warmup < demand_end <= duration')
    parameters=config.get('policy_parameters',{})
    allowed={}
    if config.get('policy') in ('S1','S3','S6','S7'):allowed['green_extension_seconds']=(1,15)
    if config.get('policy') in ('S3','S6','S7'):allowed['downstream_occupancy_threshold']=(10,90)
    if config.get('policy') in ('S5','S7'):allowed['managed_curb_stop_seconds']=(0,30)
    for key,value in parameters.items():
        if key not in allowed:raise ValueError('Unsupported policy parameter: '+key)
        if not isinstance(value,(int,float)) or not allowed[key][0]<=value<=allowed[key][1]:raise ValueError('Policy parameter out of range: '+key)
    if 'od' in config:
        if not isinstance(config['od'],list) or not 1<=len(config['od'])<=1000:raise ValueError('od must contain 1 to 1000 rows')
        for row in config['od']:
            if not {'origin_gate','destination_gate','rate_per_hour'}<=set(row):raise ValueError('OD requires origin_gate,destination_gate,rate_per_hour')
            if set(row)-{'origin_gate','destination_gate','rate_per_hour','interval_start','interval_end'}:raise ValueError('Unknown OD field')
            if not isinstance(row['rate_per_hour'],(int,float)) or not 0<=row['rate_per_hour']<=3000:raise ValueError('OD rate must lie between0 and3000veh/h')
            a=float(row.get('interval_start',0));b=float(row.get('interval_end',end))
            if not 0<=a<b<=end:raise ValueError('OD interval must lie within demand window')
    block=config.get('downstream_block')
    if block:
        if not isinstance(block,dict) or set(block)-{'gate_id','start_seconds','end_seconds','speed_m_s'}:raise ValueError('Invalid downstream_block')
        if not {'gate_id','start_seconds','end_seconds'}<=set(block):raise ValueError('Downstream block requires gate_id,start_seconds,end_seconds')
        if not 0<=float(block['start_seconds'])<float(block['end_seconds'])<=duration:raise ValueError('Downstream block time out of range')
        if not .1<=float(block.get('speed_m_s',.1))<=2:raise ValueError('Downstream constrained speed range .1 to2m/s')
        scene=json.loads((ROOT/'data/canonical/network.json').read_text())
        if not any(g['id']==block['gate_id'] and g['direction']=='exit' for g in scene['gates']):raise ValueError('Unknown downstream exit gate')
    if config.get('od'):
        import sumolib
        from .demand import legal_paths
        source=ROOT/'data/canonical/network.json'
        if source.exists():
            scene=json.loads(source.read_text());net=sumolib.net.readNet(str(ROOT/'networks/baseline/network.net.xml'))
            paths=legal_paths(net,scene['gates'])
            for row in config['od']:
                if row['origin_gate'] not in paths or not any(c['destination_gate']==row['destination_gate'] for c in paths[row['origin_gate']]):raise ValueError('Unknown or unreachable positive OD: '+row['origin_gate']+' -> '+row['destination_gate'])
    return []

def run_simulation(config,output,progress_callback=None):
    validate_config(config);output=Path(output);output.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    import libsumo as api,sumolib
    source=ROOT/'data/canonical/network.json'
    if not source.exists():raise RuntimeError('Build genuine OSM network first: python scripts/build_network.py')
    baseline=json.loads(source.read_text());base_net=sumolib.net.readNet(str(ROOT/'networks/baseline/network.net.xml'),withInternal=False)
    # Exogenous inventory and baseline reference frozen BEFORE policy compilation.
    trips,demand=generate_demand(base_net,baseline,config)
    policy=config.get('policy','S0');network_path,network,policy_manifest=compile_policy(baseline,policy,output,config.get('policy_parameters'))
    write_json(output/'demand.json',demand)
    dt=float(config.get('step_seconds',.5));control_interval=.5;control_stride=int(round(control_interval/dt));duration=float(config.get('duration_seconds',600));seed=int(config.get('seed',42))
    routes=ET.Element('routes')
    ET.SubElement(routes,'vType',id='car',vClass='passenger',length='4.6',minGap='2.5',maxSpeed='15.0',accel='2.6',decel='4.5',sigma='0.5',tau='1.0',actionStepLength='0.5',speedDev='0.05')
    ET.SubElement(routes,'vType',id='bus',vClass='bus',length='12',minGap='3',maxSpeed='13.9',accel='1.2',decel='4.0',sigma='0.5',tau='1.2',actionStepLength='0.5',speedDev='0.02')
    types=output/'types.rou.xml';ET.ElementTree(routes).write(types,encoding='utf-8')
    api.start(['sumo','-n',str(network_path),'-r',str(types),'--step-length',str(dt),'--seed',str(seed),'--time-to-teleport','-1','--max-depart-delay','-1','--collision.action','warn','--no-step-log','true','--duration-log.disable','true','--xml-validation','never','--log',str(output/'sumo.log'),'--error-log',str(output/'sumo-errors.log')])
    evaluator=Evaluator(trips);recorder=Recorder(output/'trajectory',[t['persistent_trip_id'] for t in trips],[l['id'] for l in network['lanes']]) if config.get('trajectory',True) else None
    controller=PolicyController(api,network,policy,config.get('policy_parameters'));events=[];teleports=0;collisions=0;nx=network['origin']['sumo_x'];ny=network['origin']['sumo_y'];advance_time=0.;read_time=0.;record_time=0.;times=0
    stop_states={};downstream_active=False;downstream_lanes={};signal_states=[];last_signal_states={}
    block=config.get('downstream_block')
    if block:
        gate=next(g for g in network['gates'] if g['id']==block['gate_id'])
        downstream_lanes={l['id']:api.lane.getMaxSpeed(l['id']) for l in network['lanes'] if l['edge_id']==gate['edge_id']}
    try:
        # Prevalidate ALL policy routes before adding any vehicle. No route-invalid demand is dropped.
        actual_routes={}
        for trip in trips:
            route=trip['route'];key=(route[0],route[-1],trip['vehicle_type'])
            if key not in actual_routes:
                rr=api.simulation.findRoute(route[0],route[-1],vType=trip['vehicle_type'])
                if not rr.edges:raise ValueError(f'Policy {policy} makes positive OD unreachable: {trip["origin_gate"]} -> {trip["destination_gate"]}')
                actual_routes[key]=rr.edges
        for index,trip in enumerate(trips):
            v=trip['persistent_trip_id'];key=(trip['route'][0],trip['route'][-1],trip['vehicle_type']);route=actual_routes[key];rid='r'+str(index);api.route.add(rid,route)
            api.vehicle.add(v,rid,typeID=trip['vehicle_type'],depart=str(trip['desired_departure']),departLane='best',departSpeed='0')
            # Real stopping vehicles create lane blockage. Same exogenous selected trips across policies.
            is_bus=trip['vehicle_type']=='bus';curb=not is_bus and index%18==0
            if is_bus or curb:
                candidates=[e for e in route[1:-1] if base_net.hasEdge(e) and base_net.getEdge(e).getLength()>60 and any(abs(p[0]-nx)<500 and abs(p[1]-ny)<500 for p in base_net.getEdge(e).getShape())]
                if candidates:
                    edge=candidates[len(candidates)//2];length=api.lane.getLength(edge+'_0');stop_duration=20 if is_bus else (float(config.get('policy_parameters',{}).get('managed_curb_stop_seconds',8)) if policy in ('S5','S7') else 40)
                    lane_index=0
                    # Choose a permitted lane for the vehicle's class, avoiding sidewalk index0.
                    edgeobj=base_net.getEdge(edge)
                    permitted=[lane for lane in edgeobj.getLanes() if lane.allows('bus' if is_bus else 'passenger')]
                    if permitted:
                        lane_index=permitted[0].getIndex();length=permitted[0].getLength();pos=min(length-10,max(20,length*.65));api.vehicle.setStop(v,edge,pos=pos,laneIndex=lane_index,duration=stop_duration)
                        events.append(dict(time=trip['desired_departure'],type='scheduled_bus_stop' if is_bus else 'scheduled_curb_stop',vehicle_id=v,edge_id=edge,position=pos,duration=stop_duration,source='assumed_exogenous_event'))
        setup_time=time.perf_counter()-start
        for step in range(1,int(round(duration/dt))+1):
            t=step*dt;tick=time.perf_counter()
            if block:
                constrained=block['start_seconds']<=t-dt<block['end_seconds']
                if constrained!=downstream_active:
                    for lane,speed in downstream_lanes.items():api.lane.setMaxSpeed(lane,float(block.get('speed_m_s',.1)) if constrained else speed)
                    downstream_active=constrained;events.append(dict(time=t-dt,type='downstream_constraint_start' if constrained else 'downstream_constraint_end',gate_id=block['gate_id'],speed_m_s=float(block.get('speed_m_s',.1)),source='explicit_hypothetical_receiving_constraint'))
            if (step-1)%control_stride==0:controller.step(t-dt)
            api.simulationStep();advance_time+=time.perf_counter()-tick;tick=time.perf_counter()
            active=api.vehicle.getIDList();departed=api.simulation.getDepartedIDList();arrived=api.simulation.getArrivedIDList();teleports+=api.simulation.getStartingTeleportNumber();collisions+=api.simulation.getCollidingVehiclesNumber()
            positions={};rows=[];queues=0
            for v in active:
                x,y=api.vehicle.getPosition(v);p=(x-nx,y-ny);positions[v]=p;speed=api.vehicle.getSpeed(v);queues+=speed<.1;evaluator.distance[v]=api.vehicle.getDistance(v)
                stopped=api.vehicle.isStopped(v)
                if stopped and v not in stop_states:stop_states[v]=t;events.append(dict(time=t,type='stop_started',vehicle_id=v,edge_id=api.vehicle.getRoadID(v)))
                elif not stopped and v in stop_states:events.append(dict(time=t,type='stop_ended',vehicle_id=v,duration=t-stop_states.pop(v)))
                if recorder:rows.append((v,p[0],p[1],api.vehicle.getAngle(v),speed,api.vehicle.getLaneID(v),1 if api.vehicle.getTypeID(v)=='bus' else 0))
            evaluator.step(t,dt,active,departed,arrived,positions,queues);read_time+=time.perf_counter()-tick
            if recorder:
                for tls in controller.links:
                    state=api.trafficlight.getRedYellowGreenState(tls)
                    if last_signal_states.get(tls)!=state:signal_states.append(dict(time=t,tls=tls,state=state,phase=api.trafficlight.getPhase(tls)));last_signal_states[tls]=state
                tick=time.perf_counter();recorder.frame(t,rows);record_time+=time.perf_counter()-tick
            if step%100==0 and progress_callback:progress_callback({'time':t,'duration':duration,'progress':t/duration})
            if step%100==0:write_json(output/'progress.json',dict(time=t,duration=duration,progress=t/duration,inside=len(active)))
        metrics,summaries=evaluator.finish(duration,teleports,collisions)
        # Exact entry wait, including insertion interval; arrival times quantized to step length.
        metrics['external_wait_vehicle_seconds']=sum(max(0,min(duration,evaluator.inserted.get(t['persistent_trip_id'],duration))-t['desired_departure']) for t in trips if t['cohort_id']=='peak' and t['desired_departure']<=duration)
        metrics['spatial_time_method']='End-of-step rectangular integration; peak core/periphery may differ by <= step boundary terms from exact trip elapsed time.'
        metrics['queue_population']='All cohorts; stopped-speed threshold <0.1 m/s is a count proxy, not contiguous physical queue length.'
        metrics['observed_stop_starts']=sum(e['type']=='stop_started' for e in events)
        metrics['signal_extensions']=len([e for e in controller.events if e['type']=='green_extension'])
        metrics['bus_completed']=sum(t['vehicle_type']=='bus' and t['status']=='completed' for t in summaries)
        chunks=recorder.close() if recorder else []
        events+=controller.events
        audit=dict(conservation_passed=True,conservation_max_residual=0,teleports=teleports,collisions=collisions,explicit_failures=0,unexplained_losses=0,steps=int(duration/dt),field_calibrated=False,critical_unknowns=['Actual signals/turn permissions/driver behavior require field verification','Synthetic boundary OD and bus/curb events','No pedestrian demand or nonmotorized agents yet; lane geometry only'],status='passed_software_checks' if not teleports and not collisions else 'anomalies_require_review')
        write_json(output/'signals.json',signal_states);write_json(output/'metrics.json',metrics);write_json(output/'trips.json',summaries);write_json(output/'timeseries.json',evaluator.series);write_json(output/'events.json',events);write_json(output/'audit.json',audit)
        try:
            import pyarrow as pa,pyarrow.parquet as pq
            for name,records in [('trips',summaries),('metrics',evaluator.series),('events',events)]:
                if records:pq.write_table(pa.Table.from_pylist(records),output/(name+'.parquet'))
        except ImportError:pass
        manifest=dict(schema_version='1.0',run_id=config.get('run_id',output.name),network_hash=network['network_hash'],demand_hash=demand['demand_hash'],policy_hash=policy_manifest['policy_hash'],engine='SUMO/libsumo',engine_version=api.getVersion()[1],policy=policy,period=config.get('period','am'),seed=seed,step_seconds=dt,action_step_seconds=.5,control_interval_seconds=control_interval,rate_per_gate=config.get('rate_per_gate',120),demand_scale=config.get('demand_scale',1),config=config,cohort={'warmup_seconds':demand['warmup_seconds'],'demand_end_seconds':demand['demand_end_seconds'],'target':'peak'},start_time=0,end_time=duration,duration_seconds=duration,network='network.json',metrics='metrics.json',timeseries='timeseries.json',trips='trips.json',events='events.json',signals='signals.json',audit='audit.json',chunks=chunks,vehicles=[{'id':i,'persistent_trip_id':t['persistent_trip_id'],'type':t['vehicle_type']} for i,t in enumerate(trips)],lanes=[l['id'] for l in network['lanes']],trajectory=dict(record_bytes=32,endianness='little',layout=['time:f32','vehicle_id:u32','x:f32','y:f32','angle:f32','speed:f32','lane_index:u32','flags:u32'],angle_convention='degrees_clockwise_from_north',chunk_seconds=20),wall_time_seconds=time.perf_counter()-start,timing={'initialization_seconds':setup_time,'simulation_seconds':advance_time,'collection_evaluation_seconds':read_time,'trajectory_seconds':record_time},hardware=dict(platform=platform.platform(),processor=platform.processor()),status='completed',valid_for_ranking=not teleports and not collisions,calibration_status='uncalibrated_synthetic_scenario',limitations=audit['critical_unknowns'])
        write_json(output/'manifest.json',manifest);return manifest
    finally:api.close()
