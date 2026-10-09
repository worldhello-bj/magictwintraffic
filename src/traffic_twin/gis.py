"""Reproducible OSM -> SUMO -> local-metric scene. No invented road geometry."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
CENTER=(104.0600,30.6270)
RAW_URL='https://www.openstreetmap.org/api/0.6/map?bbox=104.047,30.610,104.078,30.640'
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def build_network(download=False):
    import pyproj,sumolib
    raw=ROOT/'data/raw/yulin.osm'
    if download or not raw.exists():
        import requests
        response=requests.get(RAW_URL,timeout=180);response.raise_for_status();raw.parent.mkdir(parents=True,exist_ok=True);raw.write_bytes(response.content)
    osm=ET.parse(raw).getroot()
    if osm.tag!='osm':raise ValueError('Input is not genuine OSM XML')
    raw_tags={w.get('id'):{t.get('k'):t.get('v') for t in w.findall('tag')} for w in osm.findall('way')}
    project=pyproj.Transformer.from_crs('EPSG:4326','EPSG:32648',always_xy=True)
    unproject=pyproj.Transformer.from_crs('EPSG:32648','EPSG:4326',always_xy=True)
    cx,cy=project.transform(*CENTER)
    def square(half):return [[-half,-half],[half,-half],[half,half],[-half,half]]
    outer_geo=[unproject.transform(cx+x,cy+y) for x,y in square(1000)]
    binary=Path(sys.executable).parent/'netconvert'
    if not binary.exists(): binary=Path(sumolib.checkBinary('netconvert'))
    target=ROOT/'networks/baseline/network.net.xml';target.parent.mkdir(parents=True,exist_ok=True)
    import sumo
    types=ET.parse(Path(sumo.__file__).parent/'data/typemap/osmNetconvert.typ.xml')
    assumed_speeds={'highway.primary':50/3.6,'highway.secondary':40/3.6,'highway.tertiary':30/3.6,'highway.residential':30/3.6,'highway.unclassified':30/3.6,'highway.primary_link':30/3.6,'highway.secondary_link':30/3.6,'highway.tertiary_link':30/3.6,'highway.trunk_link':40/3.6,'highway.service':20/3.6}
    for typ in types.getroot():
        if typ.get('id') in assumed_speeds:typ.set('speed',str(assumed_speeds[typ.get('id')]))
    typefile=ROOT/'data/canonical/urban_assumed_types.xml';types.write(typefile,encoding='utf-8')
    command=[str(binary),'--type-files',str(typefile),'--osm-files',str(raw),'--output-file',str(target),'--proj', '+proj=utm +zone=48 +datum=WGS84 +units=m +no_defs','--keep-edges.in-geo-boundary',','.join(str(v) for p in outer_geo for v in p),'--keep-edges.by-vclass','passenger,bus,bicycle,pedestrian','--geometry.remove','true','--ramps.guess','false','--junctions.join','true','--tls.guess','true','--tls.default-type','static','--tls.yellow.time','3','--tls.allred.time','1','--tls.green.time','30','--output.street-names','true','--output.original-names','true','--no-warnings','false']
    process=subprocess.run(command,capture_output=True,text=True)
    (target.parent/'conversion.log').write_text(process.stdout+'\n'+process.stderr)
    if process.returncode:raise RuntimeError(process.stderr)
    pre=sumolib.net.readNet(str(target))
    signal_nodes=[]
    for node in pre.getNodes():
        incoming=[e for e in node.getIncoming() if e.allows('passenger')]
        major=[e for e in incoming if any(t in e.getType() for t in ('primary','secondary','tertiary'))]
        if len(incoming)>=3 and len(major)>=2 and not node.getType().startswith('traffic_light'):signal_nodes.append(node.getID())
    if signal_nodes:
        command2=[str(binary),'--sumo-net-file',str(target),'--output-file',str(target),'--tls.set',','.join(signal_nodes),'--tls.default-type','static','--tls.yellow.time','3','--tls.allred.time','1','--tls.green.time','30','--output.street-names','true']
        second=subprocess.run(command2,capture_output=True,text=True)
        (target.parent/'signals.log').write_text(second.stdout+'\n'+second.stderr)
        if second.returncode:raise RuntimeError(second.stderr)
    # Remove time/path-bearing generator comments so identical inputs hash identically.
    ET.parse(target).write(target,encoding='utf-8',xml_declaration=True)
    net=sumolib.net.readNet(str(target),withInternal=True,withPrograms=True)
    nx,ny=net.convertLonLat2XY(*CENTER)
    def local(p):return [round(p[0]-nx,3),round(p[1]-ny,3)]
    lanes=[];edges=[];mapping=[]
    for edge in net.getEdges(withInternal=True):
        for lane in edge.getLanes():
            lanes.append(dict(id=lane.getID(),edge_id=edge.getID(),shape=[local(p) for p in lane.getShape()],width=lane.getWidth(),speed=lane.getSpeed(),length=lane.getLength(),allow=list(lane.getPermissions()),internal=edge.getFunction()=='internal'))
        if edge.getFunction()=='internal':continue
        original=edge.getParam('origId',edge.getID().lstrip('-').split('#')[0]);tags=raw_tags.get(original,{})
        layer=int(tags.get('layer','0')) if tags.get('layer','0').lstrip('-').isdigit() else 0
        elevation=layer*5.0 if layer else 5.0 if tags.get('bridge') in ('yes','viaduct') else 0.
        for lane in lanes[-len(edge.getLanes()):]:lane['display_elevation']=elevation;lane['layer']=layer;lane['elevation_status']='derived_display_from_osm_layer_bridge' if elevation else 'ground_assumed' 
        edges.append(dict(id=edge.getID(),name=edge.getName(),osm_way_id=original,from_node=edge.getFromNode().getID(),to_node=edge.getToNode().getID(),length=edge.getLength(),speed=edge.getSpeed(),lanes=[l.getID() for l in edge.getLanes()],shape=[local(p) for p in edge.getShape()],allows_passenger=edge.allows('passenger'),type=edge.getType(),osm_tags=tags,display_elevation=elevation,layer=layer))
        mapping.append(dict(logical_road_id=original,osm_way_id=original,scenario_edge_id=edge.getID(),lane_ids=[l.getID() for l in edge.getLanes()],attribute_status='map_tag_or_sumo_default_unverified'))
    junctions=[dict(id=n.getID(),position=local(n.getCoord()),shape=[local(p) for p in n.getShape()],type=n.getType()) for n in net.getNodes() if not n.getID().startswith(':')]
    gates=[]
    for e in net.getEdges():
        if not e.allows('passenger'):continue
        for direction,node in [('entry',e.getFromNode()),('exit',e.getToNode())]:
            others=node.getIncoming() if direction=='entry' else node.getOutgoing()
            # Outer terminal approaches only; residential cul-de-sacs inside are not gates.
            p=local(node.getCoord())
            if max(abs(p[0]),abs(p[1]))<1000:continue
            car_others=[a for a in others if a.allows('passenger') and a.getID()!=('-'+e.getID()) and e.getID()!=('-'+a.getID())]
            if car_others:continue
            side=('E' if p[0]>0 else 'W') if abs(p[0])>abs(p[1]) else ('N' if p[1]>0 else 'S')
            gates.append(dict(id=f'{side}_{direction}_{e.getID()}',edge_id=e.getID(),direction=direction,side=side,position=p,status='derived_outer_terminal'))
    nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in osm.findall('node')}
    buildings=[]
    for way in osm.findall('way'):
        tags={t.attrib['k']:t.attrib['v'] for t in way.findall('tag')}
        if 'building' not in tags:continue
        points=[]
        for nd in way.findall('nd'):
            if nd.attrib['ref'] not in nodes:continue
            px,py=project.transform(*nodes[nd.attrib['ref']]);points.append([round(px-cx,3),round(py-cy,3)])
        if len(points)<4 or not any(abs(x)<1200 and abs(y)<1200 for x,y in points):continue
        height=9.;status='assumed'
        try:
            if 'height' in tags:height=float(tags['height'].replace(' m',''));status='map_tag'
            elif 'building:levels' in tags:height=float(tags['building:levels'])*3;status='derived_from_map_tag'
        except ValueError:pass
        buildings.append(dict(id=way.attrib['id'],polygon=points,height=min(180,max(3,height)),height_status=status,name=tags.get('name','')))
    xx=[p[0] for l in lanes for p in l['shape']];yy=[p[1] for l in lanes for p in l['shape']]
    bounds=[min(xx),min(yy),max(xx),max(yy)]
    manifest=dict(schema_version='1.0',network_hash=digest(target),name='成都玉林 · OSM 真实街区实验',origin=dict(lon=CENTER[0],lat=CENTER[1],sumo_x=nx,sumo_y=ny),crs='EPSG:32648',coordinate_convention='x East, y North; Three.js x=x,z=-y',core_polygon=square(500),simulation_polygon=[[bounds[0],bounds[1]],[bounds[2],bounds[1]],[bounds[2],bounds[3]],[bounds[0],bounds[3]]],requested_simulation_polygon=square(1000),core_wgs84=[unproject.transform(cx+x,cy+y) for x,y in square(500)],simulation_wgs84=outer_geo,actual_bounds_m=bounds,actual_envelope_area_km2=(bounds[2]-bounds[0])*(bounds[3]-bounds[1])/1e6,lanes=lanes,edges=edges,junctions=junctions,gates=gates,buildings=buildings,traffic_lights=[dict(id=t.getID(),junction_ids=[t.getID()]) for t in net.getTrafficLights()],provenance=dict(source='OpenStreetMap contributors',url=RAW_URL,license='ODbL-1.0',license_url='https://www.openstreetmap.org/copyright',downloaded_at='2026-10-09',osm_sha256=digest(raw),assumed_default_speeds_m_s=assumed_speeds,ignored_restrictions=[{'id':'19781710','type':'no_left_turn','via_wgs84':[104.0595409,30.6386243],'reason':'Via node north of requested simulation boundary; from edge truncated before via. Not a core-turn restriction.'}],traffic_attributes='OSM tags where present, explicit assumed urban speeds 20/30/40/50 km/h by road class otherwise; other SUMO defaults not field verified',signals='SUMO inferred experimental fixed-time control; not observed Chengdu timing',buildings='OSM footprints; tagged/derived heights or 9 m illustrative fallback'),validation_status='software_network_only_not_field_calibrated')
    write_json(ROOT/'data/canonical/network.json',manifest);write_json(ROOT/'web/public/data/network.json',manifest)
    write_json(ROOT/'data/canonical/road_mapping.json',mapping)
    write_json(ROOT/'data/raw/provenance.json',dict(**manifest['provenance'],conversion_command=command,sumo_version=subprocess.check_output([str(binary),'--version'],text=True).splitlines()[0],center_wgs84=CENTER,core_size_m=[1000,1000],requested_outer_size_m=[2000,2000],actual_bounds_m=bounds,notes='netconvert retains complete intersecting edges/junctions, so actual outer extent differs from exact 2 km square. No geometric additions or artificial grid. Critical OSM attributes and inferred connections require field/manual verification.'))
    return manifest
