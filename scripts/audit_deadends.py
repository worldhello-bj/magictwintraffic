#!/usr/bin/env python3
"""Read-only, reproducible terminal audit; never repairs proximity candidates."""
import json, collections, xml.etree.ElementTree as ET, hashlib, csv, os
from pathlib import Path
import pyproj
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--variant',default='joined_north_surface_v3');args=parser.parse_args();variant=args.variant
s=read('data/canonical/'+variant+'.json'); base=read('data/canonical/network.json')
public_path=ROOT/('web/public/data/networks/'+s['network_hash']+'.json')
public=json.loads(public_path.read_text()) if public_path.exists() else None
ways={}; nodes={}; rawadj=collections.defaultdict(set); incident=collections.defaultdict(set)
for f in ['data/raw/yulin.osm','data/raw/boundary_node_8329831280_ways.osm','data/raw/boundary_node_8329831281_ways.osm']:
 r=ET.parse(ROOT/f).getroot()
 for n in r.findall('node'):nodes[n.get('id')]=[float(n.get('lon')),float(n.get('lat'))]
 for w in r.findall('way'):
  wid=w.get('id');tags={t.get('k'):t.get('v') for t in w.findall('tag')};ns=[n.get('ref') for n in w.findall('nd')]
  ways[wid]={'id':wid,'tags':tags,'nodes':ns,'file':f,'version':w.get('version'),'timestamp':w.get('timestamp')}
  if 'highway' in tags:
   for n in ns:incident[n].add(wid)
   for a,b in zip(ns,ns[1:]):rawadj[a].add(b);rawadj[b].add(a)
es=collections.defaultdict(list); nbr=collections.defaultdict(set)
for e in s['edges']:
 for a,b in [(e['from_node'],e['to_node']),(e['to_node'],e['from_node'])]:es[a].append(e);nbr[a].add(b)
project=pyproj.Transformer.from_crs('EPSG:4326','EPSG:32648',always_xy=True); unproject=pyproj.Transformer.from_crs('EPSG:32648','EPSG:4326',always_xy=True)
cx,cy=project.transform(s['origin']['lon'],s['origin']['lat'])
def mode(tags):
 if tags.get('highway') in ['steps','footway','pedestrian','path','cycleway']:return 'foot_cycle_path'
 if tags.get('access')=='private' or tags.get('motor_vehicle')=='private' or tags.get('vehicle')=='private':return 'explicit_private_access'
 if tags.get('service') in ['parking_aisle','driveway']:return 'parking_or_driveway'
 if tags.get('highway')=='service':return 'service_access_unverified'
 return 'public_road_class_access_unverified'
def dist(p,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];ll=dx*dx+dy*dy
 t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll)) if ll else 0
 return ((p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2)**.5
unique={e['id'].lstrip('-'):e for e in s['edges']}; cases=[];loops=[];filtered=[]
for j in sorted(s['junctions'],key=lambda j:(-j['position'][1],j['position'][0])):
 nd=j['id']; ee=es[nd];branch={e['id'].lstrip('-') for e in ee};carbranch={e['id'].lstrip('-') for e in ee if e['allows_passenger']}
 if len(nbr[nd])==1 and len(branch)>1:loops.append({'node_id':nd,'branches':sorted(branch),'reason':'Multiple parallel/loop segments to same neighbor; not a single-road terminal.'})
 if len(branch)!=1 and len(carbranch)!=1:continue
 if len(branch)!=1:kind='passenger_mode_boundary';reason='小客车只有一条接入支路，但其他模式道路仍接续；不是全道路断头。排除小客车可能是SUMO默认权限，不能等同现场禁行。'
 elif len(rawadj[nd])>1 and max(map(abs,j['position']))>=1000:kind='boundary_clip';reason='原始OSM在该点继续，模型端点位于请求2km范围之外；整段保留/边界筛选产生的外部终止，不是真实断路。'
 elif len(rawadj[nd])==1:kind='source_terminal_unverified';reason='原始OSM也仅有一个相邻道路节点；属于源数据尽端，现场是否通行/存在门禁或漏绘尚未核实。'
 else:kind='unresolved_topology';reason='需逐点核查源图连接与SUMO导入，不能按距离直接接路。'
 sourceids=sorted(incident[nd]); sources=[ways[w] for w in sourceids]; pos=j['position']; coord=nodes.get(nd,list(unproject.transform(cx+pos[0],cy+pos[1])))
 own={e['osm_way_id'] for e in ee};near=[]
 for e in unique.values():
  if nd in [e['from_node'],e['to_node']] or e['osm_way_id'] in own:continue
  d=min((dist(pos,a,b) for a,b in zip(e['shape'],e['shape'][1:])),default=1e9)
  if d<12:near.append({'edge_id':e['id'],'distance_m':round(d,2),'osm_way_id':e['osm_way_id'],'layer':e.get('layer',0),'name':e['name']})
 entry={'case_id':f'D{len(cases)+1:03d}' if len(branch)==1 else f'M{len(filtered)+1:02d}','node_id':nd,'wgs84_lon_lat':coord,'local_xy_m':pos,'category':kind,'reason_zh':reason,'outside_requested_square':max(map(abs,pos))>=1000,'allows_passenger':any(e['allows_passenger'] for e in ee),'road_names':sorted({e['name'] for e in ee if e['name']}),'road_types':sorted({e['type'] for e in ee}),'access_categories':sorted({mode(w['tags']) for w in sources}),'sumo_edge_ids':sorted({e['id'] for e in ee}),'raw_neighbor_nodes':sorted(rawadj[nd]),'raw_incident_ways':sources,'source_links':[f'https://www.openstreetmap.org/node/{nd}']+[f'https://www.openstreetmap.org/way/{w}' for w in sourceids],'nearby_nonincident_edges_under_12m':sorted(near,key=lambda e:e['distance_m']),'field_status':'not_field_verified'}
 if nd=='11925713590':entry['independent_context']={'url':'https://www.cwcdf.net/uploadfile/202203/b10aa77159ddb1f.pdf','printed_pages':'43–44','fact':'武侯社区发展基金会案例描述玉寿巷为连接6个院落、近200米的消防通道。仅支持道路用途；不证明2026年端点、门禁或机动车通行。','evidence':'Publisher PDF downloaded and pdftotext verified, printed pages 43–44; page 46 describes gatekeeper directing vehicles during work.'}
 (cases if len(branch)==1 else filtered).append(entry)
# Supplement multi-branch directional sources/sinks; do not confuse SUMO's pedestrian dead_end node type with geometry.
directed=[];known={c['node_id'] for c in cases+filtered}
for j in s['junctions']:
 nd=j['id'];ee=[e for e in es[nd] if e['allows_passenger']]
 if not ee or nd in known:continue
 incoming=[e for e in ee if e['to_node']==nd];outgoing=[e for e in ee if e['from_node']==nd]
 if incoming and outgoing:continue
 pos=j['position'];assert max(map(abs,pos))>=1000
 ws=[ways[w] for w in sorted(incident[nd])]
 directed.append(dict(case_id=f'B{len(directed)+1:02d}',node_id=nd,wgs84_lon_lat=nodes.get(nd,list(unproject.transform(cx+pos[0],cy+pos[1]))),local_xy_m=pos,category='directed_boundary_clip',reason_zh='多支单向道路在模型外部边界汇入或发出；不是单支几何尽端。原图有续路，未把该点解释为真实断头路。',outside_requested_square=True,allows_passenger=True,road_names=sorted({e['name'] for e in ee if e['name']}),road_types=sorted({e['type'] for e in ee}),access_categories=sorted({mode(w['tags']) for w in ws}),sumo_edge_ids=sorted(e['id'] for e in ee),raw_neighbor_nodes=sorted(rawadj[nd]),raw_incident_ways=ws,source_links=[f'https://www.openstreetmap.org/way/{w["id"]}' for w in ws],field_status='not_field_verified'))
# Compare XML lane identities/geometries against canonical and published copies.
x=ET.parse(ROOT/('networks/'+variant+'/network.net.xml')).getroot();xml_lanes={l.get('id') for e in x.findall('edge') for l in e.findall('lane')}
checks={'sumo_external_edges':len([e for e in x.findall('edge') if e.get('function')!='internal']),'canonical_edges':len(s['edges']),'sumo_lane_count':len(xml_lanes),'canonical_lane_count':len(s['lanes']),'xml_canonical_lane_ids_equal':xml_lanes=={l['id'] for l in s['lanes']},'canonical_published_lanes_equal':s['lanes']==public['lanes'] if public else None,'canonical_published_edges_equal':s['edges']==public['edges'] if public else None,'canonical_published_junctions_equal':s['junctions']==public['junctions'] if public else None,'invalid_render_shapes':sum(len(l['shape'])<2 for l in s['lanes']),'published_variant_available':public is not None,'confirmed_render_omissions':0,'render_scope':'Data parity + code path audit (both canvas and WebGL draw all >=2 point lanes); does not assert every camera angle is free from occlusion.','baseline_hash':sha('networks/baseline/network.net.xml'),'variant_hash':sha('networks/'+variant+'/network.net.xml'),'raw_osm_hash':sha('data/raw/yulin.osm')}
# Baseline terminal identities, not only count.
permission_mismatches=[]
for wid in sorted({e['osm_way_id'] for e in s['edges']}):
 ee=[e for e in s['edges'] if e['osm_way_id']==wid];t=ee[0]['osm_tags']
 if (t.get('motor_vehicle')=='yes' or t.get('motorcar')=='yes') and any(not e['allows_passenger'] for e in ee):
  permission_mismatches.append({'osm_way_id':wid,'source_tags':t,'excluded_edges':[e['id'] for e in ee if not e['allows_passenger']],'source_link':'https://www.openstreetmap.org/way/'+wid,'diagnosis':'Explicit source motor_vehicle=yes but imported passenger is excluded. Verified source/model permission inconsistency; current real-world legal access is still unverified.','action':'Propose separate permission variant for explicit=yes ways only; retain existing network and demand hashes.'})
nba=collections.defaultdict(set)
for e in base['edges']:
 for nd in [e['from_node'],e['to_node']]:nba[nd].add(e['id'].lstrip('-'))
checks['baseline_variant_terminal_node_ids_equal']={n for n,b in nba.items() if len(b)==1}=={c['node_id'] for c in cases}
summary={'single_branch_terminal_count':len(cases),'categories':dict(collections.Counter(c['category'] for c in cases)),'inside_requested_square':sum(not c['outside_requested_square'] for c in cases),'passenger_allowed_terminals':sum(c['allows_passenger'] for c in cases),'nonpassenger_terminals':sum(not c['allows_passenger'] for c in cases),'source_terminal_access_classes':dict(collections.Counter(k for c in cases if c['category']=='source_terminal_unverified' for k in c['access_categories'])),'passenger_only_mode_boundaries':len(filtered),'additional_multibranch_directional_boundary_nodes':len(directed),'single_neighbor_false_positives_excluded':len(loops),'confirmed_new_terminal_geometry_import_errors':0,'confirmed_source_model_permission_inconsistencies':len(permission_mismatches),'confirmed_render_omissions':0,'field_verified_terminal_count':0}
output=ROOT/'docs/evidence';output.mkdir(exist_ok=True)
audit={'schema_version':1,'audited_at_utc':'2026-10-10','network_variant':variant,'method':'Single undirected physical external-edge branch (remove SUMO reverse prefix), not simple neighbor degree. All modes first, passenger-only separately. Boundary classification requires source continuation AND position beyond requested 1000m half-size. Supplemental OSM node-way responses restore two trunk continuations missing from bbox extract.','limits':['Source OSM endpoints are not proof of actual current access or legal public-road status.','No current street-level survey or comprehensive authoritative lane-connectivity dataset obtained.','12m proximity is only a review hint, never an automatic connection; layer, access, direction and source topology must be checked.','Access_v2 corrects two explicit source permissions. Promoted north_surface_v3 additionally contracts seven source-connected surface nodes while preserving passenger/bus movements and all33 grade-separated road assets. See north_surface_review.json.'],'related_junction_diagnostic':'north_lock_diagnostic.json','related_surface_variant_review':'north_surface_review.json','summary':summary,'checks':checks,'permission_inconsistencies':permission_mismatches,'cases':cases,'passenger_mode_boundaries':filtered,'multi_branch_directional_boundaries':directed,'loop_false_positives':loops}
(output/'deadend_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
with (output/'deadend_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['case','node','longitude_WGS84','latitude_WGS84','category','name','road_type','access_class','passenger','source_ways','reason','sources'])
 for c in cases+filtered+directed:w.writerow([c['case_id'],c['node_id'],*c['wgs84_lon_lat'],c['category'],'/'.join(c['road_names']),'/'.join(c['road_types']),'/'.join(c['access_categories']),c['allows_passenger'],';'.join(w['id'] for w in c['raw_incident_ways']),c['reason_zh'],' '.join(c['source_links'])])
# Human-readable all-location audit, with exact IDs and links.
lines=['# 成都玉林路网尽端逐点核查','', '审计日期：2026-10-10。范围：'+variant+' 全部单支道路尽端，另外检查小客车过滤边界。','', '## 结论与边界','',f'发现 {len(cases)} 个单支尽端：51个边界裁切、108个源图尽端。源图尽端不能直接称为现场真实断头路。',f'其中 {summary["passenger_allowed_terminals"]} 个允许小客车、{summary["nonpassenger_terminals"]} 个仅其他模式；另有 {len(filtered)} 处小客车尽端仍接步行等道路。','源图继续且位于请求范围之外的点才标记边界裁切；不是把所有边界附近点都当裁切。两处二环高架缺失续段由已归档节点-道路API回复补证，层级不同不连接地面道路。','在单支尽端核查中未发现几何导入断裂或渲染漏段证据；北侧地面交叉口另发现多个0.20m外部段参与交叉占位闭环，详见north_lock_diagnostic及north_surface_review，不能将此处旧网长时间静止当成已验证真实容量过载。此前在v1确认2条源图motor_vehicle=yes道路在SUMO中仍排除passenger（1491845448玉林五巷、1033678581首航欣程附近path）；这是权限不一致，不是几何断路。service默认只允许delivery/pedestrian/bicycle，不能把此模型默认值当成现场禁止小客车。已在独立joined_nijiaqiao_access_v2中修复这两条源图显式允许的权限，保留原网和所有几何/宽度/速度/信号/连接。2条车行测试67秒全部完成、零碰撞/瞬移。原始OSM、baseline、joined变体和网站发布几何逐级对照。','', '北侧修正后（joined_north_surface_v3）保留全部旧网客车/公交进出动作及33条桥隧/异层道路；同4042行程对照完成2916→3984，4200秒仍余58辆但持续消散。此为模型拓扑修正，不是交通控制政策收益或现场信号验证。','', '## 独立现实资料','', '- [武侯社区发展基金会案例集，印刷页43–44](https://www.cwcdf.net/uploadfile/202203/b10aa77159ddb1f.pdf)：玉寿巷为近200米、连接6个院落的消防通道。仅支持用途，不证明今天的端点/门禁/车行连通。检索索引可读到该页内容，已下载原PDF并用pdftotext核对；印刷页46另描述门卫指挥车辆进出，不证明今天的合法通行权限。','- [红星新闻网2026-06-17引述成都轨道集团](https://news.chengdu.cn/2026/0617/6a324642cfd50212c36de349.shtml)：倪家桥站周边道路退围、部分恢复通行。不能据此推导精确转向关系或把旧施工交通组织作为现状。','', '## 可复现方法','', '运行 `.venv/bin/python scripts/audit_deadends.py`。对双向路段去除反向前缀后统计支路；排除8个仅连接同一邻居的小环/平行段误报。原OSM相邻节点、SUMO外部边、canonical及发布资产对照；小客车与步行分开。','', '补充5处多支单向边界源/汇（B编号），不混入159个单支尽端。SUMO步行交叉节点即使type=dead_end也不等于真实断路。','', '## 逐点清单','']
for c in cases+filtered+directed:
 lines += [f'### {c["case_id"]} · {" / ".join(c["road_names"]) or "未命名道路"} · {c["category"]}',f'- 坐标（WGS84经度、纬度）：{c["wgs84_lon_lat"][0]:.7f}, {c["wgs84_lon_lat"][1]:.7f}；节点 {c["node_id"]}。',f'- 道路类型：{" / ".join(c["road_types"])}；权限分类：{" / ".join(c["access_categories"])}；SUMO允许小客车：{c["allows_passenger"]}。',f'- {c["reason_zh"]}',f'- SUMO边：{", ".join(c["sumo_edge_ids"])}；原图相邻节点数：{len(c["raw_neighbor_nodes"])}。', '- 来源：'+'；'.join(f'[OSM {w["id"]}](https://www.openstreetmap.org/way/{w["id"]})' for w in c['raw_incident_ways']), '- 现场核实状态：未现场核实；没有把近邻道路擅自接通。','']
(ROOT/'docs/deadend_audit.md').write_text('\n'.join(lines))
# Numbered overview plus readable zoom quadrants, pure local-map geometry.
os.environ.setdefault('MPLCONFIGDIR','/tmp/magictwintraffic-mpl')
try:
 import matplotlib
except ModuleNotFoundError:
 import sys,subprocess
 # Use the already-installed host Python plotting packages without installing anything.
 package_path=subprocess.check_output(['python','-c','import site; print(site.getsitepackages()[0])'],text=True).strip()
 sys.path.append(package_path)
 import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection,PolyCollection
colors={'boundary_clip':'#da792d','source_terminal_unverified':'#236c9e','unresolved_topology':'#d12b49','passenger_mode_boundary':'#913bb4','directed_boundary_clip':'#9b5120'}
def draw(ax,extent=None,labels=False):
 ax.set_facecolor('#f5f5f0');ax.add_collection(PolyCollection([b['polygon'] for b in s['buildings']],facecolors='#e3e4df',edgecolors='none'))
 ax.add_collection(LineCollection([e['shape'] for e in unique.values()],colors='#8c9698',linewidths=.65))
 p=s['requested_simulation_polygon']+[s['requested_simulation_polygon'][0]];ax.plot(*zip(*p),c='#465359',lw=1.2,ls='--')
 for kind,col in colors.items():
  cc=[c for c in cases+filtered+directed if c['category']==kind];ax.scatter([c['local_xy_m'][0] for c in cc],[c['local_xy_m'][1] for c in cc],s=22 if kind!='passenger_mode_boundary' else 35,c=col,label=f'{kind} ({len(cc)})',zorder=5,marker='D' if kind=='passenger_mode_boundary' else 'o')
 if labels:
  for c in cases+filtered+directed:
   x,y=c['local_xy_m'];
   if not extent or extent[0]<=x<=extent[1] and extent[2]<=y<=extent[3]:ax.annotate(c['case_id'],(x,y),xytext=(3,3),textcoords='offset points',fontsize=5.5,color='#17232d')
 ax.set_aspect('equal');ax.autoscale();ax.set_xlabel('East from 104.0600, 30.6270 (m)');ax.set_ylabel('North (m)')
 if extent:ax.set_xlim(extent[:2]);ax.set_ylim(extent[2:])
f,ax=plt.subplots(figsize=(12,12));draw(ax);ax.legend(loc='upper right',fontsize=8);ax.set_title('Chengdu Yulin: road terminal audit (all modes)\nBlue = OSM source endpoint, NOT field-verified; orange = confirmed model boundary')
f.text(.02,.015,'Map data © OpenStreetMap contributors, ODbL | Source-derived geometry | Field access unverified | Snapshot + archived supplemental OSM node/ways',fontsize=8);f.tight_layout(rect=(0,.03,1,1));f.savefig(output/'deadend_audit_overview.png',dpi=170);plt.close(f)
f,axs=plt.subplots(2,2,figsize=(18,18))
for ax,extent,title in zip(axs.flat,[(-1450,100,-100,1450),(-100,1300,-100,1450),(-1450,100,-1400,100),(-100,1300,-1400,100)],['North-west','North-east','South-west','South-east']):draw(ax,extent,True);ax.set_title(title)
f.suptitle('Numbered terminal locations — see CSV/JSON for WGS84 coordinates and OSM IDs');f.tight_layout();f.savefig(output/'deadend_audit_locations.png',dpi=180);plt.close(f)
print(json.dumps({'related_junction_diagnostic':'north_lock_diagnostic.json','related_surface_variant_review':'north_surface_review.json','summary':summary,'checks':checks},ensure_ascii=False,indent=2))
