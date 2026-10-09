#!/usr/bin/env python3
"""Draw the Fortemis left-half key layout over the Forager and Ferris Sweep (aligned on the middle
home key), the Totemist's thumbs and the first draft's (v0.3.0) thumbs (aligned on the inner
bottom key) -> docs/img/layout_compare.png.  Needs: node (npx), PyYAML, shapely, matplotlib."""
import math
import pathlib, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yaml
from shapely.geometry import box
from shapely import affinity
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from check_layout import run, CFG, CAP

def cap(x, y, r):
    return affinity.translate(affinity.rotate(box(-CAP[0]/2, -CAP[1]/2, CAP[0]/2, CAP[1]/2), r, origin=(0, 0)), x, y)

pts = {k: v for k, v in run(CFG.read_text()).items() if k.startswith(('matrix_', 'thumbs_'))}
mh, ib = pts['matrix_middle_home'], pts['matrix_inner_bottom']
# Forager left half (KiCad, y down) -> y up, shifted so its middle home key sits on ours
fx, ftop = [-107, -89, -71, -53, -35], [-28, -34, -39, -36, -34]
fdx, fdy = mh['x'] + 71, mh['y'] - 22
forager = [(x + fdx, -(t + 17 * i) + fdy, 0) for x, t in zip(fx, ftop) for i in range(3)]
forager += [(-32.251 + fdx, -21.6 + fdy, -25), (-17.63 + fdx, -32.83 + fdy, -25)]
# Ferris Sweep columns: drop below middle 19 / 7 / 0 / 5.5 / 8, no splay
sweep = [(mh['x'] + 18 * (c - 2), mh['y'] - d + 17 * i, 0)
         for c, d in enumerate([19, 7, 0, 5.5, 8]) for i in (-1, 0, 1)]
# Thumbs relative to the inner bottom key: the Totemist's (measured from the seller's top-down
# photo; its main block is the TOTEM's) and the first draft's (Forager thumbs + tuck thumb)
totemist = [(ib['x'] + x, ib['y'] + y, r) for x, y, r in [(-5.97, -19.31, -15), (12.68, -26.92, -30), (28.82, -38.92, -45)]]
draft = [(ib['x'] + x, ib['y'] + y, -25) for x, y in [(-15.25, -17.62), (2.749, -21.6), (17.37, -32.83)]]

fig, ax = plt.subplots(figsize=(9, 7.5))
for (x, y, r), style in [(p, dict(fc='none', ec='tab:blue', ls=':', lw=1.2)) for p in sweep] + \
                        [(p, dict(fc='none', ec='tab:red', ls='--', lw=1.2)) for p in forager] + \
                        [(p, dict(fc='none', ec='0.45', ls=':', lw=1.4)) for p in draft] + \
                        [(p, dict(fc='none', ec='tab:purple', ls='-.', lw=1.4)) for p in totemist]:
    ax.fill(*cap(x, y, r).exterior.xy, **style)
for k, v in pts.items():
    ax.fill(*cap(v['x'], v['y'], v['r']).exterior.xy, fc='#f2d98c', ec='k', lw=1, alpha=0.9)
    ax.text(v['x'], v['y'], k.split('_', 1)[1].replace('_', '\n'), ha='center', va='center', fontsize=6)
cfg = yaml.safe_load(CFG.read_text())
u = cfg['units']
a = [math.radians(d) for d in range(8, 66)]
ax.plot([ib['x'] + u['thumb_cx'] + u['thumb_r'] * math.sin(t) for t in a],
        [ib['y'] + u['thumb_cy'] + u['thumb_r'] * math.cos(t) for t in a], color='tab:purple', lw=0.6, alpha=0.6)
ax.plot([], [], color='k', label=f"Fortemis v{cfg['meta']['version']} (Sweep stagger +15% ring/pinky, TOTEM splay, Totemist thumb arc +{u['thumb_arc']:g} mm)")
ax.plot([], [], color='tab:purple', ls='-.', label='Totemist thumbs (measured)')
ax.plot([], [], color='0.45', ls=':', label='First draft v0.3.0 thumbs (tag first-draft)')
ax.plot([], [], color='tab:red', ls='--', label='Forager')
ax.plot([], [], color='tab:blue', ls=':', label='Ferris Sweep columns')
ax.set_aspect('equal'); ax.legend(loc='lower left', fontsize=7); ax.set_title('Fortemis left half: Choc keycaps 17.5 x 16.5 mm')
ax.grid(alpha=0.2)
out = CFG.parent.parent / 'docs' / 'img' / 'layout_compare.png'; out.parent.mkdir(exist_ok=True)
fig.savefig(out, dpi=110, bbox_inches='tight'); print(out)
