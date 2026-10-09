"""Render authoritative road geometry and boundary gates without a basemap service."""
from pathlib import Path
import json, os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/magictwintraffic-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection

root = Path(__file__).resolve().parents[1]
n = json.loads((root / 'data/canonical/network.json').read_text())
f, ax = plt.subplots(figsize=(12, 12), facecolor='#eef1eb')
ax.set_facecolor('#eef1eb')
ax.add_collection(PolyCollection([b['polygon'] for b in n['buildings']], facecolors='#d5dbd0', edgecolors='none'))
lanes = [l for l in n['lanes'] if not l.get('internal') and 'passenger' in l.get('allow', [])]
ax.add_collection(LineCollection([l['shape'] for l in lanes], colors='#566461', linewidths=.7))
for key, color, title in [('core_polygon', '#c98d30', '1 km core'), ('requested_simulation_polygon', '#71989c', 'Requested 2 km envelope'), ('simulation_polygon', '#aeb8af', 'Retained-network envelope')]:
    polygon = n[key] + [n[key][0]]
    ax.plot(*zip(*polygon), color=color, lw=2, label=title)
for gate in n['gates']:
    x, y = gate['position']
    ax.scatter([x], [y], c='#257567' if gate['direction'] == 'entry' else '#b04e40', s=23, zorder=5)
ax.set_aspect('equal'); ax.autoscale(); ax.legend(loc='upper right')
ax.set_title('Yulin: OSM road geometry, boundary gates and study scope')
ax.set_xlabel('East (m)'); ax.set_ylabel('North (m)')
f.text(.015, .01, 'Map data © OpenStreetMap contributors · ODbL · Network-derived geometry; traffic attributes include experimental assumptions', fontsize=7)
f.tight_layout(rect=(0,.02,1,1))
output = root / 'docs/evidence/network-overview.png'
output.parent.mkdir(parents=True, exist_ok=True)
f.savefig(output, dpi=130)
print(output)
