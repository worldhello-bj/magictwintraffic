#!/usr/bin/env python3
"""Narrow OSM-tag-based passenger permission correction; geometry is immutable."""
import copy,hashlib,json,xml.etree.ElementTree as ET,sys,os,tempfile,fcntl
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='joined_nijiaqiao_v1';VARIANT='joined_nijiaqiao_access_v2';WAYS={'1491845448','1033678581'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 target=ROOT/'networks'/VARIANT;target.mkdir(parents=True,exist_ok=True)
 with (target/'.build.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  with tempfile.TemporaryDirectory(prefix='.staging-',dir=target) as staging:
   return _build_locked(Path(staging))
def _build_locked(staging):
 import sumolib
 src=ROOT/'networks'/SOURCE/'network.net.xml';source_hash=sha(src)
 canonical=ROOT/'data/canonical'/f'{SOURCE}.json';outdir=ROOT/'networks'/VARIANT;finalnet=outdir/'network.net.xml';finalscene=ROOT/'data/canonical'/f'{VARIANT}.json';receipt_path=outdir/'build_manifest.json'
 build_key=hashlib.sha256((source_hash+sha(canonical)+sha(ROOT/'data/raw/yulin.osm')+sha(Path(__file__))).encode()).hexdigest()
 if all(p.exists() for p in [finalnet,finalscene,receipt_path]):
  try:
   saved=json.loads(receipt_path.read_text())
   if saved.get('build_key')==build_key and saved['network_hash']==sha(finalnet) and saved.get('canonical_hash')==sha(finalscene):
    ET.parse(finalnet);assert json.loads(finalscene.read_text())['network_hash']==saved['network_hash'];return dict(saved,cache_hit=True)
  except (ValueError,KeyError,AssertionError,ET.ParseError):pass
 root=ET.parse(src).getroot();before=copy.deepcopy(root)
 scene=json.loads((ROOT/'data/canonical'/f'{SOURCE}.json').read_text());osm=ET.parse(ROOT/'data/raw/yulin.osm').getroot();evidence={}
 for w in osm.findall('way'):
  if w.get('id') not in WAYS:continue
  tags={t.get('k'):t.get('v') for t in w.findall('tag')};assert tags.get('motor_vehicle')=='yes'
  assert not any('conditional' in k for k in tags)
  assert all(tags.get(k) not in ['no','private','destination','customers'] for k in ['access','vehicle','motor_vehicle','motorcar'])
  evidence[w.get('id')]={'tags':tags,'version':w.get('version'),'timestamp':w.get('timestamp'),'url':'https://www.openstreetmap.org/way/'+w.get('id')}
 assert set(evidence)==WAYS
 edges={e.get('id'):e for e in root.findall('edge')};lanes={l.get('id'):l for e in edges.values() for l in e.findall('lane')};target_edges={e['id'] for e in scene['edges'] if e['osm_way_id'] in WAYS};assert len(target_edges)==4
 changed={}
 def permits(l):return ('passenger' in l.get('allow','').split()) if l.get('allow') is not None else 'passenger' not in l.get('disallow','').split()
 def permit(l):
  if permits(l):return
  old=copy.deepcopy(l.attrib)
  if l.get('allow') is not None:l.set('allow',l.get('allow')+' passenger')
  else:l.set('disallow',' '.join(x for x in l.get('disallow','').split() if x!='passenger'))
  changed[l.get('id')]={'old_allow':old.get('allow'),'new_allow':l.get('allow'),'old_disallow':old.get('disallow'),'new_disallow':l.get('disallow')}
 for eid in target_edges:
  for lane in edges[eid].findall('lane'):permit(lane)
 # Follow existing via chains only where BOTH external lane endpoints now allow passenger.
 connections=root.findall('connection');affected=[]
 for c in connections:
  if c.get('from') not in target_edges and c.get('to') not in target_edges:continue
  if c.get('from','').startswith(':'):continue
  fl=edges[c.get('from')].findall('lane')[int(c.get('fromLane'))];tl=edges[c.get('to')].findall('lane')[int(c.get('toLane'))]
  if not permits(fl) or not permits(tl):continue
  via=c.get('via');visited=set()
  while via and via not in visited:
   visited.add(via);permit(lanes[via]);viaedge=via.rsplit('_',1)[0];vi=via.rsplit('_',1)[1]
   nextc=[q for q in connections if q.get('from')==viaedge and q.get('fromLane')==vi and q.get('to')==c.get('to') and q.get('toLane')==c.get('toLane')]
   assert len(nextc)==1,(via,nextc);via=nextc[0].get('via')
  affected.append(dict(c.attrib,via_chain=sorted(visited)))
 # Remove permission attributes only: every other XML attribute/element must match exactly.
 def without_permissions(tree):
  x=copy.deepcopy(tree)
  for e in x.findall('edge'):
   for l in e.findall('lane'):
    for k in ['allow','disallow']:l.attrib.pop(k,None)
  return ET.tostring(x)
 assert without_permissions(before)==without_permissions(root)
 out=staging/'network.net.xml';ET.ElementTree(root).write(out,encoding='utf-8',xml_declaration=True)
 net=sumolib.net.readNet(str(out),withInternal=True);newscene=copy.deepcopy(scene)
 for l in newscene['lanes']:
  if l['id'] in changed:l['allow']=list(l['allow'])+['passenger']
 for e in newscene['edges']:e['allows_passenger']=net.getEdge(e['id']).allows('passenger')
 newscene.update(network_variant=VARIANT,network_hash=sha(out),name='成都玉林 · 倪家桥合并及显式车行权限修正')
 newscene['provenance']['permission_variant']={'id':VARIANT,'parent_variant':SOURCE,'parent_hash':source_hash,'source_ways':evidence,'method':'Add passenger to four explicitly motor_vehicle=yes external lanes and compatible existing internal connection lanes only; no geometry, speed, width, signal or route changes.','status':'source_tag_consistency_correction_not_field_verified'}
 # Exact JSON geometry/signal/gate identity.
 for k in ['junctions','gates','buildings','traffic_lights','origin']:assert newscene[k]==scene[k]
 for old,new in zip(scene['lanes'],newscene['lanes']):assert {k:v for k,v in old.items() if k!='allow'}=={k:v for k,v in new.items() if k!='allow'}
 for old,new in zip(scene['edges'],newscene['edges']):assert {k:v for k,v in old.items() if k!='allows_passenger'}=={k:v for k,v in new.items() if k!='allows_passenger'}
 stagedscene=staging/'scene.json';stagedscene.write_text(json.dumps(newscene,ensure_ascii=False,indent=2))
 receipt={'network_variant':VARIANT,'network_hash':sha(out),'parent_network_hash':source_hash,'source_ways':evidence,'external_edges_changed':sorted(target_edges),'lane_permission_changes':changed,'compatible_connections':affected,'geometry_width_speed_signals_connections_unchanged':True,'parent_network_unchanged':sha(src)==source_hash,'baseline_hash':sha(ROOT/'networks/baseline/network.net.xml'),'field_verified':False}
 receipt.update(build_key=build_key,canonical_hash=sha(stagedscene),status='ready')
 stagedreceipt=staging/'build_manifest.json';stagedreceipt.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 for p in [out,stagedscene,stagedreceipt]:
  with p.open('rb') as stream:os.fsync(stream.fileno())
 os.replace(out,finalnet);os.replace(stagedscene,finalscene);os.replace(stagedreceipt,receipt_path)
 return receipt
if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
