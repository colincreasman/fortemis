#!/usr/bin/env python3
"""Generate the Fortemis case, a top plate and a base for each half, around the routed PCBs.

  python3 ergogen/tools/case.py                  # both halves -> case/*.stl and docs/img/case.png
  python3 ergogen/tools/case.py fortemis_left    # one half

The board outline, switches, nuts, XIAO, power switch and battery come from pcb/<board>.kicad_pcb
through KiCad's bundled Python (pcb_kicad.py geom), so the case follows the PCB. The dimensions copy
the Forager case (docs/design-log.md). Each part is checked against simple models of the components,
and the script fails if anything overlaps.

Needs KiCad 10 and `pip install -r ergogen/tools/requirements.txt`.

Frame: mm; x right, y away from the typist (KiCad's y flipped), z up; z = 0 is the PCB's bottom face.
"""
import json, pathlib, re, subprocess, sys, tempfile

import manifold3d as m3d
import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pcb import BOARDS, KICAD_PY, PCB, ROOT  # noqa: E402

OUT = ROOT / 'case'
IMG = ROOT / 'docs' / 'img' / 'case.png'
CONFIG = ROOT / 'ergogen' / 'config.yaml'
SEGS = 48                       # segments per circle

# Stack: base bottom, floor top, PCB bottom (0), PCB top = base rim, plate top. 8.4 mm overall.
Z_BOTTOM, Z_FLOOR, Z_PCB, Z_TOP = -4.6, -3.6, 1.6, 3.8
EDGE = 1.3                      # case outline = PCB outline (without the switch tab) + EDGE
GAP = 0.3                       # PCB edge to the base's inner wall
TAPER_Z, TAPER = -0.6, 2.0      # below TAPER_Z the inner wall leans TAPER inward by the floor
SCREW_D = 2.4                   # M2 clearance
NUT_BOTTOM = -2.0               # SMD nuts hang 2.0 below the PCB

# Top plate
CUT, CUT_R = 13.9, 0.0          # switch cutout, square-cornered like Forager's, rotated with the key
CLIP = 1.0                      # 45 deg chamfer under the E/W sides: 1.2 mm ledge for the clips
GROOVE_W, GROOVE_L, GROOVE_Z, GROOVE_R = 4.4, 2.55, 2.3, 0.7   # switch-puller grooves N and S
TOP_CSK_D, TOP_CSK_DEPTH = 4.5, 1.05
POCKET_D, POCKET_DEPTH = 3.0, 0.6   # under through-hole solder joints (XIAO BAT+)
MIN_CSK_WALL = 0.8              # a nut gets a top screw only this far from cutouts and grooves

# Base
BOSS_R0, BOSS_R1, BOSS_TOP = 3.78, 2.78, -2.1
BOT_CSK_D, BOT_CSK_DEPTH = 5.0, 1.3
RIB_W, RIB_TOP, RIB_PITCH, RIB_CLEAR = 1.0, -2.4, 15.0, 1.0
BAT_RECESS, BAT_CELL = 0.4, (30.0, 12.0, 3.3)
PANEL_V = 8.4                   # outer wall flat and vertical for this far either side of the USB-C

# XIAO frame: u from the USB-C end of the module inward, v toward the D0..D6 pad row.
XIAO_L, XIAO_W = 20.96, 17.78
USB_SLOT = (4.72, -0.95, 1.5, 2.0)          # half width, top z, top corner radius, inner end u
USB_C = (8.94, 3.25, -1.56, 6.5)            # receptacle shell (stadium): width, height, u range
USB_HOLE = (4.75, 7.43)                     # floor opening: half width, inner end u
LEVER = (1.88, 7.43, 4.75, 6.75, 0.4)       # tip centre u, root u, v range, slot width
LEVER_CLEAR_Z = -0.9
NUB = (1.0, 0.6, -2.0)                      # cone radius at floor, at top, top z
PIPE = (-6.513, -2.7, 1.95, 4.43)           # light pipe bore: v, z, diameter, inner end u
PIPE_BLOCK = (-8.11, -5.04, -1.75, 0.85)    # filament channel: v range, top z, open from u

# Power switch frame: t along the switch's front face, n outward; notch through the base wall
NOTCH = ((6.3, 0.0, Z_PCB), (4.9, -1.8, 0.0))   # (half width, z0, z1): PCB tab, switch body
NOTCH_N = -3.5


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def xy(p):
    return np.array([p['x'], p['y']])


class Frame:
    """Local 2D coordinates (a, b) -> world origin + a * ea + b * eb."""

    def __init__(self, origin, ea, eb=None):
        self.o, self.ea = np.asarray(origin, float), unit(ea)
        self.eb = unit(eb) if eb is not None else np.array([-self.ea[1], self.ea[0]])

    def __call__(self, a, b):
        return self.o + a * self.ea + b * self.eb

    def local(self, p):
        d = np.asarray(p, float) - self.o
        return np.array([d @ self.ea, d @ self.eb])

    def geom(self, g):
        return affinity.affine_transform(g, [self.ea[0], self.eb[0], self.ea[1], self.eb[1], *self.o])


def rrect(w, h, r, cx=0.0, cy=0.0):
    b = box(cx - w / 2 + r, cy - h / 2 + r, cx + w / 2 - r, cy + h / 2 - r)
    return b.buffer(r, quad_segs=SEGS // 4) if r > 0 else b


def disc(c, r):
    return Point(*c).buffer(r, quad_segs=SEGS // 4)


def section(g):
    rings = []
    for p in getattr(g, 'geoms', [g]):
        if not p.is_empty:
            rings += [np.asarray(r.coords)[:-1] for r in [p.exterior, *p.interiors]]
    return m3d.CrossSection(rings, m3d.FillRule.EvenOdd)


def prism(g, z0, z1):
    return section(g).extrude(z1 - z0).translate([0, 0, z0])


def cone(c, r0, z0, r1, z1):
    return m3d.Manifold.cylinder(z1 - z0, r0, r1, SEGS).translate([c[0], c[1], z0])


def union(solids):
    return m3d.Manifold.batch_boolean(list(solids), m3d.OpType.Add)


def smooth(poly, r):
    """Round every outside corner to at least r (opening). The outline's arcs come polygonised from
    KiCad and buffering adds tiny joins along them, which would fold over when loft() insets them."""
    out = poly.buffer(-r, quad_segs=16).buffer(r, quad_segs=16).simplify(0.001)
    assert out.geom_type == 'Polygon' and poly.hausdorff_distance(out) < 0.3
    return out


def loft(poly, levels):
    """Solid whose cross-section at each (z, d) level is `poly` inset by d (levels bottom to top).
    Vertices move along their miters: only valid for insets below the smallest outside radius."""
    p = np.asarray(orient(poly, 1.0).exterior.coords)[:-1]
    e = np.roll(p, -1, 0) - p
    out = np.column_stack([e[:, 1], -e[:, 0]]) / np.linalg.norm(e, axis=1)[:, None]
    a, b = np.roll(out, 1, 0), out
    miter = (a + b) / (1 + (a * b).sum(1))[:, None]
    rings = [p - d * miter for _, d in levels]
    for (z, d), r in zip(levels, rings):
        assert Polygon(r).is_valid, f'outline inset by {d} at z={z} self-intersects'
    n, i = len(p), np.arange(len(p))
    j = np.roll(i, -1)
    verts = np.vstack([np.column_stack([r, np.full(n, z)]) for r, (z, _) in zip(rings, levels)])
    tris = [m3d.triangulate([rings[0]])[:, ::-1], m3d.triangulate([rings[-1]]) + (len(levels) - 1) * n]
    for k in range(len(levels) - 1):
        lo, hi = k * n, (k + 1) * n
        tris += [np.column_stack([lo + i, lo + j, hi + j]), np.column_stack([lo + i, hi + j, hi + i])]
    solid = m3d.Manifold(m3d.Mesh(vert_properties=verts.astype(np.float32),
                                  tri_verts=np.vstack(tris).astype(np.uint32)))
    assert solid.status() == m3d.Error.NoError, solid.status()
    return solid


def arc(r, z_tangent, z_end, steps=16):
    """(z, inset) along a round of radius r that is tangent to the vertical wall at z_tangent."""
    t = np.linspace(0, np.arcsin(min(1.0, abs(z_end - z_tangent) / r)), steps)
    return [(z_tangent + np.sign(z_end - z_tangent) * r * np.sin(a), r * (1 - np.cos(a))) for a in t]


TOP_EDGE = [(Z_PCB, 0.35), (Z_PCB + 0.35, 0.0)] + arc(2.08, 2.0, Z_TOP)        # 0.35 chamfer, round
BASE_EDGE = arc(5.39, -0.182, Z_BOTTOM)[::-1] + [(1.4, 0.0), (1.4, 0.4), (Z_PCB, 0.4)]  # round, reveal


def load(board):
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / 'geom.json'
        r = subprocess.run([KICAD_PY, str(pathlib.Path(__file__).with_name('pcb_kicad.py')), 'geom',
                            str(PCB / f'{board}.kicad_pcb'), str(out)], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)
        return json.loads(out.read_text())


def config_value(name):
    return float(re.search(rf'^\s*{name}:\s*([\d.]+)', CONFIG.read_text(), re.M).group(1))


class Half:
    def __init__(self, board):
        self.name = board
        g = load(board)
        flip = lambda pts: [(x, -y) for x, y in pts]
        o = g['outline'][0]
        self.board = Polygon(flip(o['outer']), [flip(h) for h in o['holes']])
        fps = g['footprints']
        for f in fps:
            f['y'] = -f['y']
            for p in f['pads']:
                p['y'] = -p['y']
        kind = lambda prefix: [f for f in fps if f['lib'].startswith(prefix)]
        self.switches = kind('switch_')
        self.keys = [self.key_frame(f) for f in self.switches]
        self.nuts = [np.array([f['x'], f['y']]) for f in kind('nut_')]
        self.mcu = self.mcu_frame(kind('mcu_')[0])
        self.pwr = self.power_frame(kind('power_switch')[0])
        bat = kind('battery')[0]
        rot = np.radians(bat['rot'])
        self.bat = Frame(xy(bat), [np.cos(rot), np.sin(rot)])
        self.bat_area = (config_value('bat_l'), config_value('bat_w'))
        self.bat_pads = [xy(p) for p in bat['pads']]
        others = [f for f in fps if f not in self.switches and not f['lib'].startswith('nut_')]
        self.solder = [(xy(p), max(POCKET_D, p['w'] + 1.3)) for f in others for p in f['pads']
                       if p['kind'] == 'th' and p['front']]
        self.notab = self.remove_tab()
        # PCB corners are r2.25: just round the polygonised arcs
        self.outline = smooth(self.notab.buffer(EDGE, quad_segs=SEGS // 4), 2.25 + EDGE + 0.05)
        self.cavity = smooth(self.notab.buffer(GAP, quad_segs=SEGS // 4), 2.25 + GAP + 0.05)
        self.cutouts = unary_union([k.geom(rrect(CUT, CUT, CUT_R)) for k in self.keys]
                                   + [k.geom(g) for k in self.keys for g in self.grooves()])
        self.top_screws = [c for c in self.nuts
                           if Point(*c).distance(self.cutouts) >= TOP_CSK_D / 2 + MIN_CSK_WALL]

    @staticmethod
    def key_frame(f):
        holes = [p for p in f['pads'] if p['kind'] == 'npth']
        posts = [xy(p) for p in holes if abs(p['drill'][0] - 1.9) < 0.05]
        return Frame(xy(max(holes, key=lambda p: p['drill'][0])), posts[1] - posts[0])

    @staticmethod
    def mcu_frame(f):
        pad = {p['name']: xy(p) for p in f['pads']}
        out = unit(pad['D0'] + pad['5V'] - pad['D6'] - pad['D7'])
        across = pad['D0'] - pad['5V']
        centre = (pad['D0'] + pad['5V'] + pad['D6'] + pad['D7']) / 4
        return Frame(centre + out * XIAO_L / 2, -out, across - (across @ out) * out)

    @staticmethod
    def power_frame(f):
        pins = [xy(p) for p in f['pads'] if p['name'] in ('1', '2', '3')]
        n = unit(xy(f) - np.mean(pins, 0))
        return Frame(xy(f), [n[1], -n[0]], n)

    def remove_tab(self):
        """The board without the power-switch tab, which ends flush with the case's outer wall."""
        tn = np.array([self.pwr.local(p) for p in self.board.exterior.coords])
        side = tn[(np.abs(tn[:, 0]) > 12) & (np.abs(tn[:, 0]) < 25)]
        edge = side[:, 1].max()
        tab_end = tn[np.abs(tn[:, 0]) < 6.5][:, 1].max()
        assert abs(tab_end - edge - EDGE) < 0.05, f'switch tab should end {EDGE} past the board edge'
        notab = self.board.difference(self.pwr.geom(box(-25, edge, 25, edge + 10)))
        assert 0 < self.board.area - notab.area < 30
        return notab

    @staticmethod
    def grooves():
        length = GROOVE_L + 1.0
        c = CUT / 2 + GROOVE_L - length / 2
        return [rrect(GROOVE_W, length, GROOVE_R, 0, c), rrect(GROOVE_W, length, GROOVE_R, 0, -c)]

    # ---------------------------------------------------------------- top plate
    def switch_cut(self, k):
        corners = lambda w, z: [[*k(a, b), z] for a, b in np.asarray(rrect(w, CUT, CUT_R).exterior.coords)]
        z0 = Z_PCB - 0.1
        chamfer = m3d.Manifold.hull_points(np.array(corners(CUT + 2 * (CLIP + 0.1), z0)
                                                    + corners(CUT, Z_PCB + CLIP)))
        straight = prism(k.geom(rrect(CUT, CUT, CUT_R)), Z_PCB + CLIP - 0.01, Z_TOP + 1)
        grooves = prism(unary_union([k.geom(g) for g in self.grooves()]), GROOVE_Z, Z_TOP + 1)
        return chamfer + straight + grooves

    def top(self):
        cuts = [self.switch_cut(k) for k in self.keys]
        for c in self.top_screws:
            cuts += [cone(c, SCREW_D / 2, Z_PCB - 1, SCREW_D / 2, Z_TOP + 1),
                     cone(c, SCREW_D / 2, Z_TOP - TOP_CSK_DEPTH, TOP_CSK_D / 2 + 0.1, Z_TOP + 0.1)]
        cuts += [cone(c, d / 2, Z_PCB - 1, d / 2, Z_PCB + POCKET_DEPTH) for c, d in self.solder]
        return loft(self.outline, TOP_EDGE) - union(cuts)

    # ---------------------------------------------------------------- base
    def keepouts(self):
        """Floor areas the ribs stay out of."""
        u = self.mcu
        return unary_union([
            self.bat.geom(rrect(*self.bat_area, 1.0)),
            *[disc(p, 2.5) for p in self.bat_pads],
            u.geom(box(-5, -XIAO_W / 2 - 0.5, XIAO_L, XIAO_W / 2 + 0.5)),
            self.pwr.geom(box(-NOTCH[1][0], NOTCH_N, NOTCH[1][0], 5)),
        ]).buffer(RIB_CLEAR)

    def ribs(self):
        floor = self.notab.buffer(GAP - TAPER + 0.4)          # 0.4 into the leaning wall
        x0, y0, x1, y1 = floor.bounds
        cx, cy = self.notab.centroid.x, self.notab.centroid.y
        xs = cx + RIB_PITCH * np.arange(-np.ceil((cx - x0) / RIB_PITCH), np.ceil((x1 - cx) / RIB_PITCH) + 1)
        ys = cy + RIB_PITCH * np.arange(-np.ceil((cy - y0) / RIB_PITCH), np.ceil((y1 - cy) / RIB_PITCH) + 1)
        grid = unary_union([box(x - RIB_W / 2, y0, x + RIB_W / 2, y1) for x in xs]
                           + [box(x0, y - RIB_W / 2, x1, y + RIB_W / 2) for y in ys])
        return grid.intersection(floor).difference(self.keepouts())

    def along_u(self, prof, u0, u1):
        """Extrude a profile drawn in the XIAO's (v, z) plane along u from u0 to u1."""
        ea, eb, o = self.mcu.ea, self.mcu.eb, self.mcu(u0, 0)
        m = np.array([[eb[0], 0, ea[0], o[0]], [eb[1], 0, ea[1], o[1]], [0, 1, 0, 0]])
        return section(prof).extrude(u1 - u0).transform(m)

    def usb_slot(self):
        w, top, r, end = USB_SLOT
        prof = unary_union([box(-w, Z_BOTTOM - 1, w, top - r), box(-w + r, Z_BOTTOM - 1, w - r, top),
                            disc((-w + r, top - r), r), disc((w - r, top - r), r)])
        return self.along_u(prof, -6, end)

    def lever(self):
        tip, root, v0, v1, slot = LEVER
        vc = (v0 + v1) / 2
        arm = unary_union([box(tip, v0, root, v1), disc((tip, vc), (v1 - v0) / 2)])
        around = unary_union([box(tip, v0 - 1, root, v1 + slot), disc((tip, vc), (v1 - v0) / 2 + slot)])
        return self.mcu.geom(around.difference(arm)), self.mcu.geom(around), self.mcu(tip, vc)

    def base(self):
        u = self.mcu
        body = loft(self.outline, BASE_EDGE)
        body += prism(u.geom(box(-6, -PANEL_V, 3, PANEL_V)).intersection(self.outline), Z_BOTTOM, 1.0)
        body -= loft(self.cavity, [(Z_FLOOR, TAPER), (TAPER_Z, 0.0), (Z_PCB + 1, 0.0)])
        pv, pz, pd, pend = PIPE
        bv0, bv1, btop, bopen = PIPE_BLOCK
        slope = (BOSS_R0 - BOSS_R1) / (BOSS_TOP - Z_FLOOR)
        body += union([cone(c, BOSS_R0 + 0.1 * slope, Z_FLOOR - 0.1, BOSS_R1, BOSS_TOP) for c in self.nuts]
                      + [prism(self.ribs(), Z_FLOOR - 0.1, RIB_TOP),
                         prism(u.geom(box(-1.0, bv0, pend, bv1)), Z_FLOOR - 0.1, btop)])

        slot, clear, tip = self.lever()
        bore = m3d.Manifold.cylinder(pend + 6, pd / 2, pd / 2, SEGS).rotate(
            [0, 90, np.degrees(np.arctan2(u.ea[1], u.ea[0]))]).translate([*u(-6, pv), pz])
        cuts = [self.usb_slot(),
                prism(u.geom(box(-6, -USB_HOLE[0], USB_HOLE[1], USB_HOLE[0])), Z_BOTTOM - 1, Z_FLOOR + 0.1),
                prism(slot, Z_BOTTOM - 1, Z_FLOOR + 0.05), prism(clear, Z_FLOOR, LEVER_CLEAR_Z),
                bore, prism(u.geom(box(bopen, pv - pd / 2, pend + 1, pv + pd / 2)), pz, btop + 0.5),
                prism(self.bat.geom(rrect(self.bat_area[0] + 0.5, self.bat_area[1] + 0.5, 1.0)),
                      Z_FLOOR - BAT_RECESS, Z_FLOOR + 0.1)]
        for w, z0, z1 in NOTCH:
            cuts.append(prism(self.pwr.geom(box(-w, NOTCH_N, w, 5)), z0, z1 + 0.1))
        for c in self.nuts:
            cuts += [cone(c, SCREW_D / 2, Z_BOTTOM - 1, SCREW_D / 2, NUT_BOTTOM + 0.1),
                     cone(c, BOT_CSK_D / 2 + 0.1, Z_BOTTOM - 0.1, SCREW_D / 2, Z_BOTTOM + BOT_CSK_DEPTH)]
        body -= union(cuts)
        r0, r1, ztop = NUB
        return body + cone(tip, r0, Z_FLOOR - 0.05, r1, ztop)

    # ---------------------------------------------------------------- checks
    def components(self):
        """Simplified solids for everything the case must clear."""
        u, s, parts = self.mcu, self.pwr, {}
        add = lambda k, solid: parts.setdefault(k, []).append(solid)
        add('PCB', prism(self.board, 0, Z_PCB))
        for k, f in zip(self.keys, self.switches):
            add('switch housing', prism(k.geom(box(-6.9, -6.9, 6.9, 6.9)), Z_PCB, Z_TOP))
            socket = [p for p in f['pads'] if p['kind'] == 'smd' or abs(p['drill'][0] - 3.0) < 0.05]
            hull = unary_union([disc(xy(p), max(p['w'], p['h']) / 2) for p in socket]).convex_hull
            add('hot-swap socket', prism(hull.buffer(0.5), -1.85, 0))
            for p in f['pads']:
                if p['kind'] != 'smd' and abs(p['drill'][0] - 3.0) > 0.05:
                    add('switch posts', cone(xy(p), p['drill'][0] / 2 + 0.2, -2.2, p['drill'][0] / 2 + 0.2, 0))
        for c in self.nuts:
            add('nuts', cone(c, 2.6, NUT_BOTTOM, 2.6, 0))
        add('XIAO', prism(u.geom(box(0, -XIAO_W / 2, XIAO_L, XIAO_W / 2)), -1.0, 0))
        add('XIAO', prism(u.geom(box(4.5, -XIAO_W / 2 + 0.5, XIAO_L, XIAO_W / 2 - 0.5)), -2.05, -1.0))
        add('XIAO', prism(u.geom(box(0.2, -6.5, 3.5, -5.0)), -1.6, -1.0))         # RGB and charge LEDs
        add('XIAO', prism(u.geom(box(0.3, 4.85, 3.5, 6.6)), -1.6, -1.0))          # reset button
        w, h, u0, u1 = USB_C
        add('USB-C receptacle', self.along_u(rrect(w, h, h / 2 - 0.02, 0, -1.0 - h / 2), u0, u1))
        add('power switch', prism(s.geom(box(-3.5, -2.7, 3.5, 0)), -1.5, 0))
        add('power switch', prism(s.geom(box(-4.6, -2.0, 4.6, -0.6)), -0.5, 0))
        add('power switch', prism(s.geom(box(-2.25, 0, 2.25, 1.5)), -1.2, -0.3))
        bl, bw, bh = BAT_CELL
        add('battery', prism(self.bat.geom(rrect(bl, bw, 0.5)), Z_FLOOR - BAT_RECESS + 0.01,
                             Z_FLOOR - BAT_RECESS + bh))
        for p in self.bat_pads:
            add('battery wires', cone(p, 1.5, -1.0, 1.5, 0))
        return {k: union(v) for k, v in parts.items()}

    def check(self, parts):
        comps, ok = self.components(), True
        for name, solid in parts.items():
            pieces = len(solid.decompose())
            x0, y0, z0, x1, y1, z1 = solid.bounding_box()
            print(f'  {name}: {solid.volume() / 1000:.1f} cm3, {x1 - x0:.1f} x {y1 - y0:.1f} x {z1 - z0:.1f} mm,'
                  f' {solid.num_tri()} triangles, genus {solid.genus()}, {pieces} piece(s)')
            ok &= pieces == 1 and solid.status() == m3d.Error.NoError
            gaps = []
            for cname, comp in comps.items():
                clash = (solid ^ comp).volume()
                if clash > 1e-3:
                    print(f'    CLASH with {cname}: {clash:.3f} mm3')
                    ok = False
                elif cname != 'PCB':
                    gaps.append(f'{cname} {solid.min_gap(comp, 2.0):.2f}')
            print('    min gap (mm): ' + ', '.join(gaps))
        inside = [k for k in comps if k not in ('PCB', 'switch housing', 'battery')]
        for k in inside:
            clash = (comps['battery'] ^ comps[k]).volume()
            if clash > 1e-3:
                print(f'    battery CLASH with {k}: {clash:.3f} mm3')
                ok = False
        print(f'  top screws at {len(self.top_screws)} of {len(self.nuts)} nuts; '
              f'{len(self.keys)} switches; checks {"passed" if ok else "FAILED"}')
        return ok


def write_stl(solid, path):
    mesh = solid.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float32)
    tri = v[np.asarray(mesh.tri_verts)]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(tri), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('attr', '<u2')])
    rec['n'], rec['v'] = n, tri
    with open(path, 'wb') as f:
        f.write(f'Fortemis {path.stem}'.encode().ljust(80, b' '))
        f.write(np.uint32(len(tri)).tobytes())
        f.write(rec.tobytes())


def look(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def crop(solid, centre, r, z1=10.0):
    return solid ^ m3d.Manifold.cube([2 * r, 2 * r, z1 + 10]).translate([centre[0] - r, centre[1] - r, -10])


def render(ax, solids, view, title):
    """Flat-shaded orthographic view of [(solid, rgb)] seen from direction `view`, painter's algorithm."""
    from matplotlib.collections import PolyCollection
    view = unit(view)
    right = unit(np.cross([0, 0, 1], view)) if abs(view[2]) < 0.999 else np.array([1.0, 0, 0])
    up = np.cross(view, right)
    light = unit(view + 0.6 * up + 0.3 * right)
    size = max(np.ptp(np.reshape(s.bounding_box(), (2, 3)), 0)[:2].max() for s, _ in solids)
    polys, colours, depth = [], [], []
    for solid, rgb in solids:
        mesh = solid.refine_to_length(size / 80).to_mesh()      # small triangles sort better
        v = np.asarray(mesh.vert_properties)[:, :3]
        tri = v[np.asarray(mesh.tri_verts)]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        front = n @ view > 0
        tri, n = tri[front], n[front]
        polys.append(np.stack([tri @ right, tri @ up], -1))
        colours.append(np.clip(np.outer(0.35 + 0.65 * np.clip(n @ light, 0, 1), rgb), 0, 1))
        depth.append(tri.mean(1) @ view)
    polys, colours, depth = np.concatenate(polys), np.concatenate(colours), np.concatenate(depth)
    order = np.argsort(depth)
    ax.add_collection(PolyCollection(polys[order], facecolors=colours[order], edgecolors=colours[order],
                                     linewidths=0.2))
    pts = polys.reshape(-1, 2)
    ax.set_xlim(pts[:, 0].min() - 2, pts[:, 0].max() + 2)
    ax.set_ylim(pts[:, 1].min() - 2, pts[:, 1].max() + 2)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=10)


def preview(halves):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plate, base, gold = (0.93, 0.93, 0.95), (0.55, 0.62, 0.72), (0.85, 0.72, 0.3)
    (half, left), (_, right) = halves['fortemis_left'], halves['fortemis_right']
    lifted = lambda parts: [(parts['base'], base), (parts['top'].translate([0, 0, 14]), plate)]
    u = half.mcu
    usb, out = u(4, 0), -np.append(u.ea, 0)
    fig, axes = plt.subplots(2, 3, figsize=(18, 10.5), dpi=100)
    render(axes[0, 0], lifted(left), look(35, -60), 'Left half, plate lifted')
    render(axes[0, 1], lifted(right), look(35, -120), 'Right half, plate lifted')
    render(axes[0, 2], [(left['base'], base)], look(60, -75), 'Left base: ribs, screw bosses, battery recess')
    render(axes[1, 0], [(left['base'], base)], look(-45, -150), 'Left base from below: countersunk screws')
    render(axes[1, 1], [(crop(left['base'], usb, 14), base),
                        (crop(half.components()['USB-C receptacle'], usb, 14), gold)],
           out + [0, 0, 0.35], 'USB-C end: receptacle in its slot, light pipe exit')
    render(axes[1, 2], [(crop(left['base'], usb, 14, z1=-0.5), base)], -0.4 * out + [0, 0, 1],
           'USB-C end from inside (cut at z = -0.5): light-pipe channel, reset lever and nub')
    fig.tight_layout()
    fig.savefig(IMG)
    print(IMG.relative_to(ROOT))


def main():
    boards = sys.argv[1:] or BOARDS
    OUT.mkdir(exist_ok=True)
    built, ok = {}, True
    for board in boards:
        print(board)
        half = Half(board)
        parts = {'top': half.top(), 'base': half.base()}
        ok &= half.check(parts)
        for name, solid in parts.items():
            write_stl(solid, OUT / f'{board}_{name}.stl')
        built[board] = half, parts
    if set(BOARDS) <= set(built):
        preview(built)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
