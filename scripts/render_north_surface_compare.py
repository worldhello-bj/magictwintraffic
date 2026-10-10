from pathlib import Path
import json,os,sys,subprocess
os.environ.setdefault('MPLCONFIGDIR','/tmp/magictwintraffic-mpl')
try:import matplotlib
except ModuleNotFoundError:
 sys.path.append(subprocess.check_output(['python','-c','import site;print(site.getsitepackages()[0])'],text=True).strip());import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection,PolyCollection
ROOT=Path(__file__).resolve().parents[1];cfg=json.loads((ROOT/'scenarios/north_surface_join.json').read_text());removed=set(cfg['expected_removed_external_edges']);f,axes=plt.subplots(1,2,figsize=(14,8))
for ax,variant,title in zip(axes,['joined_nijiaqiao_access_v2','joined_north_surface_v3'],['Before: fragmented surface intersection','Counterfactual: one surface junction']):
 s=json.loads((ROOT/'data/canonical'/f'{variant}.json').read_text());ax.set_facecolor('#f2f4f4');ax.add_collection(PolyCollection([b['polygon'] for b in s['buildings']],facecolors='#dfe3e1',edgecolors='none'))
 ax.add_collection(PolyCollection([j['shape'] for j in s['junctions'] if j.get('shape')],facecolors='#c9d2d6',edgecolors='none'))
 ax.add_collection(LineCollection([l['shape'] for l in s['lanes'] if l['internal']],colors='#8a9fa9',linewidths=.5))
 ax.add_collection(LineCollection([l['shape'] for l in s['lanes'] if not l['internal']],colors='#66727a',linewidths=2))
 ax.add_collection(LineCollection([e['shape'] for e in s['edges'] if e['osm_tags'].get('tunnel')],colors='#ec8e27',linewidths=3,linestyles='dashed',label='Grade-separated underpass (unchanged)'))
 if variant.endswith('v2'):
  ax.add_collection(LineCollection([e['shape'] for e in s['edges'] if e['id'] in removed],colors='#cb3f47',linewidths=4,label='Nine external segments contracted'))
  for j in s['junctions']:
   if j['id'] in cfg['joined_nodes']:ax.scatter(*j['position'],s=30,c='#cb3f47',zorder=5)
 else:
  j=next(j for j in s['junctions'] if j['id']==variant);ax.add_collection(PolyCollection([j['shape']],facecolors='#4d98bb88',edgecolors='#236f94',linewidths=2,label='Rebuilt surface-junction footprint'))
  ax.add_collection(LineCollection([l['shape'] for l in s['lanes'] if l['id'].startswith(':'+variant)],colors='#327b9c',linewidths=.5))
 ax.set_xlim(325,480);ax.set_ylim(920,1050);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('East of model origin (m)');ax.set_ylabel('North (m)');ax.legend(loc='lower left',fontsize=8)
f.suptitle('North Renmin South Road / First Ring Road: source-grounded topology test\nOSM geometry, not surveyed signal design; underpass is not merged',fontsize=13);f.text(.02,.01,'© OpenStreetMap contributors, ODbL | Same geographic window. Counterfactual geometry changes are confined to the surface junction.',fontsize=8);f.tight_layout(rect=(0,.03,1,.91));f.savefig(ROOT/'docs/evidence/north_surface_comparison.png',dpi=170)
