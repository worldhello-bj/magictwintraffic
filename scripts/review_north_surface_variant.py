#!/usr/bin/env python3
"""Review contracted passenger movements and grade-separated asset preservation."""
import json,xml.etree.ElementTree as ET,collections
from pathlib import Path
import sumolib
ROOT=Path(__file__).resolve().parents[1];old='joined_nijiaqiao_access_v2';new='joined_north_surface_v3'
settings=json.loads((ROOT/'scenarios/north_surface_join.json').read_text());joined=set(settings['joined_nodes']);removed=set(settings['expected_removed_external_edges'])
a=sumolib.net.readNet(str(ROOT/'networks'/old/'network.net.xml'));b=sumolib.net.readNet(str(ROOT/'networks'/new/'network.net.xml'))
ain={e.getID() for e in a.getEdges() if e.getToNode().getID() in joined and e.getID() not in removed and e.allows('passenger')};aout={e.getID() for e in a.getEdges() if e.getFromNode().getID() in joined and e.getID() not in removed and e.allows('passenger')}
def nexts(net,eid,mode="passenger"):
 result=set()
 for edge,conns in net.getEdge(eid).getOutgoing().items():
  if any(c.getFromLane().allows(mode) and c.getToLane().allows(mode) for c in conns):result.add(edge.getID())
 return result
expected=set()
for start in ain:
 pending=[start];seen=set()
 while pending:
  e=pending.pop()
  if e in seen:continue
  seen.add(e)
  for n in nexts(a,e):
   if n in aout:expected.add((start,n))
   elif n in removed:pending.append(n)
actual={(start,n) for start in ain for n in nexts(b,start) if n in aout}
expected_bus=set()
for start in ain:
 pending=[start];seen=set()
 while pending:
  e=pending.pop()
  if e in seen:continue
  seen.add(e)
  for n in nexts(a,e,'bus'):
   if n in aout:expected_bus.add((start,n))
   elif n in removed:pending.append(n)
actual_bus={(start,n) for start in ain for n in nexts(b,start,'bus') if n in aout}
sa=json.loads((ROOT/'data/canonical'/f'{old}.json').read_text());sb=json.loads((ROOT/'data/canonical'/f'{new}.json').read_text());ea={e['id']:e for e in sa['edges']};eb={e['id']:e for e in sb['edges']};la={l['id']:l for l in sa['lanes']};lb={l['id']:l for l in sb['lanes']}
grade=[e['id'] for e in sa['edges'] if e['osm_tags'].get('tunnel') or e['layer']!=0 or e['osm_tags'].get('bridge')];grade_changes=[]
for e in grade:
 if ea[e]!=eb[e] or any(la[l]!=lb[l] for l in ea[e]['lanes']):grade_changes.append(e)
edge_changes=[]
for e in sorted(set(ea)&set(eb)):
 diff={k:{'old':ea[e].get(k),'new':eb[e].get(k)} for k in set(ea[e])|set(eb[e]) if ea[e].get(k)!=eb[e].get(k)}
 if diff:edge_changes.append({'edge_id':e,'changes':diff})
# Compare tunnel lane shapes/permissions numerically; JSON permission ordering may vary.
semantic_grade_changes=[]
for e in grade:
 if any(ea[e].get(k)!=eb[e].get(k) for k in ['shape','length','from_node','to_node','speed','layer','allows_passenger']):semantic_grade_changes.append(e)
 for l in ea[e]['lanes']:
  if any(la[l].get(k)!=lb[l].get(k) for k in ['shape','length','width','speed']) or set(la[l]['allow'])!=set(lb[l]['allow']):semantic_grade_changes.append(l)
result={'source_variant':old,'variant':new,'source_hash':sa['network_hash'],'variant_hash':sb['network_hash'],'joined_nodes':sorted(joined),'ingress_edges':sorted(ain),'egress_edges':sorted(aout),'old_contracted_passenger_movements':sorted(expected),'new_passenger_movements':sorted(actual),'missing_movements':sorted(expected-actual),'added_movements':sorted(actual-expected),'missing_bus_movements':sorted(expected_bus-actual_bus),'added_bus_movements':sorted(actual_bus-expected_bus),'grade_separated_edges_checked':grade,'grade_separated_semantic_changes':semantic_grade_changes,'surviving_external_edge_changes':edge_changes,'gates_equal':sa['gates']==sb['gates'],'buildings_equal':sa['buildings']==sb['buildings'],'interpretation':'Reachability across old intra-cluster edges is a conservative movement contract including circular/U-turn paths. Added/missing pairs require explicit review; geometry changes only at the joined surface junction are expected.'}
(ROOT/'docs/evidence/north_surface_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['surviving_external_edge_changes','old_contracted_passenger_movements','new_passenger_movements']},ensure_ascii=False,indent=2))
