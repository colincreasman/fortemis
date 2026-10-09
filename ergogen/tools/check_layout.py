#!/usr/bin/env python3
"""Check (and optionally solve) the Fortemis layout produced by Ergogen.

Reports column angles, home-key drops vs the middle column, thumb placement relative to the inner
bottom key (the thumb arc, decision D3), and the smallest gap between Choc keycaps (17.5 x 16.5 mm).

  python3 ergogen/tools/check_layout.py            # check
  python3 ergogen/tools/check_layout.py --solve    # tune ring/pinky stagger units in config.yaml
Needs: node (npx), PyYAML, shapely.
"""
import math, re, subprocess, sys, tempfile, pathlib, yaml
from shapely.geometry import Polygon
from shapely import affinity

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / 'config.yaml'
TARGET = {'ring': 8.0, 'pinky': 21.8}          # home-key drop below middle, mm (Sweep 7/19 +15%)
CAP = (17.5, 16.5)

def run(cfg_text):
    with tempfile.TemporaryDirectory() as d:
        src = pathlib.Path(d) / 'src'; src.mkdir()
        (src / 'config.yaml').write_text(cfg_text)
        fp = ROOT / 'footprints'
        if fp.exists(): (src / 'footprints').symlink_to(fp)
        subprocess.run(['npx', '--yes', 'ergogen@4.2.1', str(src), '-o', d + '/out', '--debug'],
                       check=True, capture_output=True)
        return yaml.safe_load(open(d + '/out/points/points.yaml'))

def measure(pts):
    # keys only (left half): the other points are the controller, switch, nuts and battery
    P = {k: v for k, v in pts.items() if k.startswith(('matrix_', 'thumbs_'))}
    home = {c: P[f'matrix_{c}_home'] for c in ['pinky', 'ring', 'middle', 'index', 'inner']}
    drop = {c: round(home['middle']['y'] - h['y'], 3) for c, h in home.items()}
    ang = {c: round(h['r'], 3) for c, h in home.items()}
    ib = P['matrix_inner_bottom']
    thumbs = {k: (round(v['x'] - ib['x'], 3), round(-(v['y'] - ib['y']), 3), round(v['r'], 3))
              for k, v in P.items() if k.startswith('thumbs')}
    caps = {}
    for k, v in P.items():
        r = Polygon([(-CAP[0]/2, -CAP[1]/2), (CAP[0]/2, -CAP[1]/2), (CAP[0]/2, CAP[1]/2), (-CAP[0]/2, CAP[1]/2)])
        caps[k] = affinity.translate(affinity.rotate(r, v['r'], origin=(0, 0)), v['x'], v['y'])
    names = sorted(caps); worst = (1e9, None)
    for i, a in enumerate(names):
        for b in names[i+1:]:
            g = caps[a].distance(caps[b]) if not caps[a].intersects(caps[b]) else -caps[a].intersection(caps[b]).area
            if g < worst[0]: worst = (g, (a, b))
    return drop, ang, thumbs, worst

def set_unit(text, name, val):
    return re.sub(rf'(\n  {name}: )[-\d.]+', rf'\g<1>{val:.4f}', text)

def main():
    text = CFG.read_text()
    if '--solve' in sys.argv:
        for _ in range(6):
            drop, *_ = measure(run(text))
            u = yaml.safe_load(text)['units']
            err_r = TARGET['ring'] - drop['ring']
            err_p = TARGET['pinky'] - drop['pinky'] - err_r
            if abs(err_r) < 1e-3 and abs(TARGET['pinky'] - drop['pinky']) < 1e-3: break
            text = set_unit(text, 'ring_stagger', u['ring_stagger'] + err_r)
            text = set_unit(text, 'pinky_stagger', u['pinky_stagger'] + err_p)
        CFG.write_text(text)
    drop, ang, thumbs, worst = measure(run(text))
    print('home drop below middle (mm):', drop)
    print('column angles (deg):', ang)
    print('thumbs rel. inner bottom key (dx, dy down, rot):', thumbs)
    print('closest keycaps: %.3f mm %s' % worst, '(negative = overlap area)')
    u = yaml.safe_load(text)['units']; print('units: ring_stagger', u['ring_stagger'], 'pinky_stagger', u['pinky_stagger'])

if __name__ == '__main__':
    main()
