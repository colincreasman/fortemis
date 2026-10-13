"""Totemist-style "sandwich" top shell for a Kailh Choc v1 keyboard half.

ErgoMech's Totemist, and GEIST's open-source TOTEM it is derived from, sink every key into a
well: the switch plate sits at the bottom of the wells and the case rim rises almost to the
keycap tops, so from the side the keycaps line up with the case instead of standing on a flat
plate. This module builds that top shell for any board. Each board's generator supplies the
outline, the keys, its plate's switch cut-outs, the screws and the parts the shell must clear.

The same file is used, unchanged, by the Ferris Sweep, Fortemis and Forager repos.

Frame: mm, z up; `z_pcb` is the PCB's top face and heights are given above it.
"""
import math

import numpy as np
from manifold3d import CrossSection, Error, FillRule, JoinType, Manifold, Mesh, OpType, triangulate
from shapely.geometry import Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

# Kailh Choc v1 (PG1350), measured from Kailh's 3D model (GEIGEIGEIST/TOTEM, PCB/totem_0-3/TOTEM3D),
# mm above the PCB top, unpressed. The flange rests on the plate top; at full travel the stem top
# is level with the top housing.
CHOC_V1 = dict(plate_top=2.2, flange_top=3.0, housing_top=5.0, stem_top=8.0, travel=3.0)

# MBK (FKcaps): 17.5 x 16.5 mm, 3.98 mm tall, of which ~1.5 mm is skirt below the ceiling that rests on
# the stem, so its top is ~10.5 mm above the PCB (skirt 3.5 mm above it when pressed: clears the flange).
MBK = dict(size=(17.5, 16.5), height=3.98, top=10.5)

# GEIST's TOTEM case v0.8 (BLE top, STEP), measured: rim 9.05 mm above the PCB top (6.85 above the
# plate), 1.0 mm from keycap edge to wall, 1.5 mm roof over a hollow rim. With MBK caps the cap tops
# stand ~1.45 mm above the rim, the "level with the keycaps (or at least almost)" look of the TOTEM
# and the Totemist. Set rim = MBK['top'] for a rim exactly level with the cap tops.
TOTEM = dict(rim=9.05, cap_clear=1.0, roof=1.5)

SEGS = 48


# ----------------------------------------------------------------------------------------- 2D
def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def polys(g):
    """Polygons of any shapely geometry."""
    if g is None or g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    return [p for q in getattr(g, 'geoms', []) for p in polys(q)]


def clean(g, min_area=0.05):
    out = [p for p in polys(g.buffer(0)) if p.area >= min_area]
    return unary_union(out) if out else Polygon()


def opening(g, width, join=2):
    """Drop every part of g narrower than `width` (morphological opening)."""
    return clean(g.buffer(-width / 2, join_style=join).buffer(width / 2, join_style=join).intersection(g))


def closing(g, width, join=2):
    return clean(g.buffer(width / 2, join_style=join).buffer(-width / 2, join_style=join).union(g))


def smooth(poly, r):
    """Round every outside corner to at least r, so loft() can inset the outline by up to r."""
    out = max(polys(poly.buffer(-r, quad_segs=16).buffer(r, quad_segs=16).simplify(0.002)), key=lambda q: q.area)
    return Polygon(out.exterior)


class Key:
    """A switch position: centre c, unit vector ea along the keycap's 17.5 mm side and
    eb = ea turned 90 degrees. Thumb keys get the lowered front shelf."""

    def __init__(self, c, ea, thumb=False, name=''):
        self.c = np.asarray(c, float)
        self.ea = unit(ea)
        self.eb = np.array([-self.ea[1], self.ea[0]])
        self.thumb, self.name = thumb, name

    def at(self, a, b):
        return self.c + a * self.ea + b * self.eb

    def rect(self, w, h, a0=0.0, b0=0.0):
        return Polygon([self.at(a0 + sa * w / 2, b0 + sb * h / 2) for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))])


# ----------------------------------------------------------------------------------------- 3D
def section(g):
    rings = []
    for p in polys(g):
        if p.area > 1e-6:
            rings += [np.asarray(r.coords)[:-1] for r in [p.exterior, *p.interiors]]
    return CrossSection(rings, FillRule.EvenOdd)


def prism(g, z0, z1):
    if g is None or g.is_empty or z1 <= z0:
        return Manifold()
    return section(g).extrude(z1 - z0).translate([0, 0, z0])


def union(solids):
    solids = [s for s in solids if s is not None and not s.is_empty()]
    return Manifold.batch_boolean(solids, OpType.Add) if solids else Manifold()


def cyl(c, r, z0, z1, r1=None):
    return Manifold.cylinder(z1 - z0, r, r if r1 is None else r1, SEGS).translate([c[0], c[1], z0])


def round_steps(r, n):
    """(depth below the top, inset) along a quarter round of radius r, bottom to top."""
    return [(r - r * math.sin(t), r - r * math.cos(t)) for t in np.linspace(0, math.pi / 2, n + 1)]


def loft(poly, levels):
    """Solid whose cross-section at each (z, d) is `poly` inset by d (levels bottom to top).
    Vertices move along their miters: insets must stay below the smallest outside corner radius."""
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
    tris = [triangulate([rings[0]])[:, ::-1], triangulate([rings[-1]]) + (len(levels) - 1) * n]
    for k in range(len(levels) - 1):
        lo, hi = k * n, (k + 1) * n
        tris += [np.column_stack([lo + i, lo + j, hi + j]), np.column_stack([lo + i, hi + j, hi + i])]
    solid = Manifold(Mesh(vert_properties=verts.astype(np.float32), tri_verts=np.vstack(tris).astype(np.uint32)))
    assert solid.status() == Error.NoError, solid.status()
    return solid


def trim_thin(m, min_feature, max_step=0.1):
    """Cut away slivers thinner than min_feature as seen from above (print services reject walls
    under ~0.8 mm). Slices the part wherever its cross-section changes, takes each slice's
    morphological opening and removes what doesn't survive."""
    if min_feature <= 0 or m.is_empty():
        return m
    m = _trim_pass(m, min_feature, max_step)
    for _ in range(4):
        before = m.volume()
        m = _trim_pass(m, min_feature, max_step, islands_only=True)
        if before - m.volume() < 1e-3:
            break
    return m


def _trim_pass(m, min_feature, max_step, islands_only=False):
    grow = 0.05
    r = min_feature / 2 + grow
    min_area = 0.25 * r * r
    zs = np.unique(np.round(np.asarray(m.to_mesh().vert_properties)[:, 2], 4))
    lv = [zs[0]]
    for z in zs[1:]:
        if z - lv[-1] > 0.01:
            lv.append(z)
    lv[-1] = zs[-1]
    cuts = []
    for za, zb in zip(lv[:-1], lv[1:]):
        sloped = abs(m.slice(za + 0.003).area() - m.slice(zb - 0.003).area()) > 1e-3
        n = max(1, math.ceil((zb - za) / max_step)) if sloped else 1
        for k in range(n):
            z0, z1 = za + (zb - za) * k / n, za + (zb - za) * (k + 1) / n
            thin = CrossSection()
            for z in (z0 + 0.003, (z0 + z1) / 2, z1 - 0.003):
                for comp in m.slice(z).decompose():
                    core = comp.offset(-r, JoinType.Round)
                    if core.is_empty():
                        thin = thin + comp
                        continue
                    if islands_only:
                        continue
                    for q in (comp - core.offset(r, JoinType.Round)).decompose():
                        if q.area() > min_area:
                            thin = thin + q
            if not thin.is_empty():
                c0 = z0 - (1.0 if za == lv[0] and k == 0 else 0.0)
                c1 = z1 + (1.0 if zb == lv[-1] and k == n - 1 else 0.0)
                cuts.append(thin.offset(grow, JoinType.Miter).extrude(c1 - c0).translate([0, 0, c0]))
    if not cuts:
        return m
    bodies = sorted((m - union(cuts)).simplify(0.001).decompose(), key=lambda q: -q.volume())
    keep = [q for q in bodies if q.volume() > 1.0] or bodies[:1]
    return Manifold.compose(keep) if len(keep) > 1 else keep[0]


# --------------------------------------------------------------------------------- the shell
class Sandwich:
    """The sandwich top shell.

    outline      Polygon: the shell's outside, the same as the base's so the two line up
    z_pcb        z of the PCB's top face
    keys         [Key]
    toward_user  unit vector pointing from the keys toward the typist (for the thumb shelf)
    plate_cuts   Manifold: the board's own plate details (switch cut-outs, clip reliefs, puller
                 grooves, screw holes, countersinks), cut from the plate z_pcb .. z_pcb + plate_t
    screws       [dict(c=(x, y), bore=d)]: screws whose head sits on the plate. Under the rim each
                 gets a solid boss and a bore of diameter d down to the plate, so the board keeps
                 its original screws
    keepouts     [(Polygon, z_top)]: parts on top of the PCB, cleared by part_clear on every side
    cuts         [Manifold]: anything else to remove (USB-C slot, reset hole ...)
    rim          rim height above the PCB top (TOTEM's by default)
    tight_clear  keycap-to-wall gap next to keepouts, when they sit closer to a key than cap_clear
    curb         (height, width): where a part is too close to a key for the well wall to reach the
                 plate, a low curb on the plate along the part keeps liquid out of its bay
    ribs         (pitch, width): walls under the roof, so no span is wider than the pitch (short
                 bridges on an FDM printer, a stiffer rim). Kept clear of keepouts. None: no ribs
    """

    def __init__(self, outline, z_pcb, keys, toward_user, plate_cuts, screws=(), keepouts=(), cuts=(),
                 keycap=MBK['size'], rim=TOTEM['rim'], cap_clear=TOTEM['cap_clear'], roof=TOTEM['roof'],
                 plate_t=2.2, wall=1.6, inner_wall=1.2, min_rim=2.0, out_round=1.5, in_chamfer=0.5,
                 bottom_chamfer=0.35, shelf=True, shelf_lip=0.0, shelf_depth=40.0, shelf_round=1.5,
                 part_clear=0.4, boss_wall=1.2, min_hollow=2.0, keep_solid=(), tight_clear=None,
                 curb=(1.0, 1.4), ribs=(12.0, 1.2)):
        self.outline, self.z0, self.keys = outline, z_pcb, list(keys)
        self.tight_clear, self.curb, self.ribs = tight_clear, curb, ribs
        self.toward = unit(toward_user)
        self.plate_cuts, self.screws, self.keepouts, self.cuts = plate_cuts, list(screws), list(keepouts), list(cuts)
        self.keycap, self.rim_h, self.cap_clear, self.roof = keycap, rim, cap_clear, roof
        self.plate_t, self.wall, self.inner_wall, self.min_rim = plate_t, wall, inner_wall, min_rim
        self.out_round, self.in_chamfer, self.bottom_chamfer = out_round, in_chamfer, bottom_chamfer
        self.use_shelf, self.shelf_lip, self.shelf_depth, self.shelf_round = shelf, shelf_lip, shelf_depth, shelf_round
        self.part_clear, self.boss_wall, self.min_hollow = part_clear, boss_wall, min_hollow
        self.keep_solid = list(keep_solid)
        self.info = {}

    # ---------------------------------------------------------------- plan view
    def plan(self):
        W, H = self.keycap
        c = self.cap_clear
        self.caps = unary_union([k.rect(W, H) for k in self.keys])
        self.wells_raw = unary_union([k.rect(W + 2 * c, H + 2 * c) for k in self.keys])
        if self.tight_clear is not None and self.keepouts:
            # where a part sits right next to a key, the wall hugs the keycap so the roof covers the part
            parts = unary_union([p for p, _ in self.keepouts])
            self.wells_raw = unary_union([self.wells_raw.difference(parts),
                                          self.caps.buffer(self.tight_clear, join_style=2)])
        rim = opening(clean(self.outline.difference(self.wells_raw)), self.min_rim)

        # thumb shelf: the strip in front of the thumb keys drops to the plate (TOTEM, Totemist)
        shelf = Polygon()
        thumbs = [k for k in self.keys if k.thumb]
        if self.use_shelf and thumbs:
            strips = []
            for k in thumbs:
                f = 1.0 if np.dot(k.eb, self.toward) > 0 else -1.0
                strips.append(k.rect(W + 2 * c, self.shelf_depth, 0.0, f * (H / 2 + c + self.shelf_depth / 2)))
            ring = unary_union([k.rect(W + 2 * c, H + 2 * c) for k in thumbs])
            shelf = closing(unary_union(strips + [ring]), 6.0).intersection(rim)
            if self.keepouts:        # parts on the PCB stay under the roof
                shelf = shelf.difference(unary_union([p for p, _ in self.keepouts]).buffer(
                    self.inner_wall + self.part_clear + 0.5, join_style=2))
            shelf = clean(shelf, 1.0)
        rim_main = opening(clean(rim.difference(shelf)), self.min_rim)
        self.shelf = clean(rim.difference(rim_main), 1.0) if not shelf.is_empty else Polygon()
        self.rim = rim_main
        self.wells = clean(self.outline.difference(rim).buffer(0))

        # hollow under the roof, open toward the PCB (no closed voids)
        bosses = [Point(*s['c']).buffer(s['bore'] / 2 + self.boss_wall) for s in self.screws]
        solid = unary_union([self.wells.buffer(self.inner_wall, join_style=2),
                             self.shelf.buffer(self.inner_wall, join_style=2)] + bosses + self.keep_solid)
        hollow = self.outline.buffer(-self.wall, join_style=2).difference(solid)
        hollow = clean(opening(hollow, self.min_hollow), 4.0)
        if self.ribs:
            pitch, w = self.ribs
            x0, y0, x1, y1 = hollow.bounds if not hollow.is_empty else (0, 0, 0, 0)
            cx, cy = self.outline.centroid.x, self.outline.centroid.y
            xs = cx + pitch * np.arange(math.floor((x0 - cx) / pitch), math.ceil((x1 - cx) / pitch) + 1)
            ys = cy + pitch * np.arange(math.floor((y0 - cy) / pitch), math.ceil((y1 - cy) / pitch) + 1)
            grid = unary_union([box(x - w / 2, y0 - 1, x + w / 2, y1 + 1) for x in xs]
                               + [box(x0 - 1, y - w / 2, x1 + 1, y + w / 2) for y in ys])
            if self.keepouts:
                grid = grid.difference(unary_union([p for p, _ in self.keepouts]).buffer(
                    self.part_clear + 0.5, join_style=2))
            hollow = clean(opening(hollow.difference(grid), self.min_hollow), 4.0)
        self.hollow = hollow
        lo, hi = 0.0, 50.0                                  # widest roof span: largest circle in the hollow
        while hi - lo > 0.05 and not self.hollow.is_empty:
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if not self.hollow.buffer(-mid).is_empty else (lo, mid)
        self.info['widest_roof_span_mm'] = round(2 * lo, 1)
        self.info.update(rim_area_mm2=round(self.rim.area, 1), shelf_area_mm2=round(self.shelf.area, 1),
                         hollow_area_mm2=round(self.hollow.area, 1),
                         keycaps_past_outline_mm2=round(self.caps.difference(self.outline).area, 2))
        return self

    # ---------------------------------------------------------------- solid
    def edge_cutter(self, region, z_top, r, mask=None, n=6):
        """Removes a quarter round of radius r along the outside of `region`'s top face at z_top."""
        big = self.outline.buffer(10)
        cut = []
        st = round_steps(r, n)
        for (h0, _), (h1, d1) in zip(st[:-1], st[1:]):
            ring = big.difference(region.buffer(-d1, join_style=1))
            if mask is not None:
                ring = ring.intersection(mask)
            cut.append(prism(ring, z_top - h0, z_top + 0.01 if h1 < 1e-9 else z_top - h1 + 1e-4))
        return union(cut)

    def build(self):
        if not hasattr(self, 'rim'):
            self.plan()
        z0 = self.z0
        zp, zr = z0 + self.plate_t, z0 + self.rim_h
        zs = zp + self.shelf_lip
        # outside: the Forager's 0.35 mm chamfer at the seam, a straight wall, a round at the rim
        prof = [(z0, self.bottom_chamfer), (z0 + self.bottom_chamfer, 0.0)]
        prof += [(zr - h, d) for h, d in round_steps(self.out_round, 8)]
        body = loft(self.outline, prof)

        neg = [prism(self.wells, zp, zr + 1)]
        if not self.shelf.is_empty:
            neg.append(prism(self.shelf, zs, zr + 1))
            neg.append(self.edge_cutter(self.outline, zs, min(self.shelf_round, zs - z0 - 0.5),
                                        mask=self.shelf.buffer(3.0, join_style=2)))
        ch, n = self.in_chamfer, 3                    # 45 degree chamfer round every opening
        holes = unary_union([self.wells, self.shelf])
        for k in range(n):
            neg.append(prism(holes.buffer(ch * (k + 1) / n, join_style=2), zr - ch + ch * k / n, zr + 1))
        neg.append(prism(self.hollow, z0 - 1, zr - self.roof))
        for s in self.screws:
            neg.append(cyl(s['c'], s['bore'] / 2, zp - 0.01, zr + 1))
            neg.append(cyl(s['c'], s['bore'] / 2, zr - 0.4, zr + 0.01, s['bore'] / 2 + 0.4))
        for poly, ztop in self.keepouts:
            neg.append(prism(poly.buffer(self.part_clear, join_style=2), z0 - 1, ztop + self.part_clear))
        neg.append(self.plate_cuts)
        neg += self.cuts
        self.solid = body - union(neg)
        if self.keepouts and self.curb:
            # curb on the plate between the wells and any part bay, below the pressed keycaps
            h, w = self.curb
            parts = unary_union([p for p, _ in self.keepouts]).buffer(self.part_clear, join_style=2)
            band = parts.buffer(w, join_style=2).difference(parts).intersection(self.wells)
            flanges = unary_union([k.rect(15.0 + 0.5, 15.0 + 0.5) for k in self.keys])
            support = Polygon()                 # only where the plate is there to stand on
            for r in self.solid.slice(zp - 0.1).to_polygons():
                if len(r) >= 3:
                    support = support.symmetric_difference(Polygon(r))
            band = clean(opening(band.difference(flanges).intersection(support), 0.8), 0.5)
            top = min(zp + h, z0 + MBK['top'] - MBK['height'] - CHOC_V1['travel'] - 0.3)
            if not band.is_empty:
                self.solid = (self.solid + prism(band, zp - 0.05, top)) - union([self.plate_cuts] + self.cuts)
            edge = parts.boundary.intersection(self.wells)
            self.info['curb_mm2'] = round(band.area, 1)
            self.info['bay_edge_in_wells_mm'] = round(edge.length, 1)
            self.info['bay_edge_curbed_mm'] = round(edge.intersection(band.buffer(0.05)).length, 1)
        self.info.update(rim_z=round(zr, 3), plate_top_z=round(zp, 3), shelf_z=round(zs, 3),
                         rim_above_pcb=self.rim_h, cap_top_above_rim_mbk=round(MBK['top'] - self.rim_h, 2))
        return self.solid


# ------------------------------------------------------------------------------- checking
def keycaps(keys, z_pcb, pressed=False, size=MBK['size'], top=MBK['top'], height=MBK['height']):
    """MBK keycaps as blocks, unpressed or fully pressed."""
    dz = -CHOC_V1['travel'] if pressed else 0.0
    return union([prism(k.rect(*size), z_pcb + top - height + dz, z_pcb + top + dz) for k in keys])


def keycap_sweep(keys, z_pcb, **kw):
    """Everything a keycap passes through between unpressed and fully pressed."""
    size, top, height = kw.get('size', MBK['size']), kw.get('top', MBK['top']), kw.get('height', MBK['height'])
    return union([prism(k.rect(*size), z_pcb + top - height - CHOC_V1['travel'], z_pcb + top) for k in keys])


def switches(keys, z_pcb):
    """Choc v1 bodies above the PCB: bottom housing, flange, top housing, stem (unpressed)."""
    out = []
    for k in keys:
        out += [prism(k.rect(13.8, 13.8), z_pcb + 0.01, z_pcb + 2.2), prism(k.rect(15.0, 15.0), z_pcb + 2.2, z_pcb + 3.0),
                prism(k.rect(13.0, 13.0), z_pcb + 3.0, z_pcb + 5.0), prism(k.rect(10.3, 5.7), z_pcb + 5.0, z_pcb + 8.0)]
    return union(out)


def closed_pockets(solid, outline, z_pcb, rim):
    """Spaces inside the shell with material both under them (plate height) and over them (roof),
    i.e. pockets a resin print could trap liquid resin in. Should be empty."""
    def sec(z):
        out = Polygon()
        for r in solid.slice(z).to_polygons():
            if len(r) >= 3:
                out = out.symmetric_difference(Polygon(r))
        return out
    mid, low, high = sec(z_pcb + 4.5), sec(z_pcb + 0.8), sec(z_pcb + rim - 0.6)
    found = []
    for p in polys(outline.buffer(-0.01).difference(mid)):
        if p.area < 1:
            continue
        core = p.buffer(-0.05)
        if core.intersection(low).area > 0.5 * p.area and core.intersection(high).area > 0.5 * p.area:
            found.append((round(p.centroid.x, 1), round(p.centroid.y, 1), round(p.area, 1)))
    return found


def report(name, solid, against):
    """One watertight piece? Size, volume, and overlap with each named solid."""
    x0, y0, z0, x1, y1, z1 = solid.bounding_box()
    res = dict(part=name, pieces=len(solid.decompose()), genus=solid.genus(), status=solid.status().name,
               volume_cm3=round(solid.volume() / 1000, 2),
               size_mm=[round(x1 - x0, 1), round(y1 - y0, 1), round(z1 - z0, 2)], clash_mm3={}, gap_mm={})
    for k, s in against.items():
        v = (solid ^ s).volume()
        res['clash_mm3'][k] = round(v, 4)
        if v <= 1e-3:
            res['gap_mm'][k] = round(solid.min_gap(s, 3.0), 2)
    res['ok'] = res['pieces'] == 1 and res['status'] == 'NoError' and all(v <= 1e-3 for v in res['clash_mm3'].values())
    return res


def write_stl(solid, path, header='sandwich case', mirror_y=False, to_bed=False):
    """Binary STL that is still closed after a slicer merges vertices by position (float32).
    Vertices closer than 1 um are snapped together and the zero-length edges that leaves are
    collapsed where the surface stays manifold; vertices shared only by touching solids are
    nudged 5 um apart. Returns whether the reloaded STL is watertight."""
    import trimesh
    if mirror_y:
        solid = solid.mirror([0, 1, 0])
    if to_bed:
        b = solid.bounding_box()
        solid = solid.translate([-b[0], -b[1], -b[2]])
    tm = _to_trimesh(solid)
    tm.export(path)
    rt = trimesh.load(path)
    return bool(rt.is_watertight and rt.is_winding_consistent and rt.volume > 0)


def _near_groups(P, eps):
    lab = np.arange(len(P))
    cells = []
    for off in np.array(np.meshgrid([0, .5], [0, .5], [0, .5])).reshape(3, -1).T:
        inv = np.unique(np.floor(P / eps + off).astype(np.int64), axis=0, return_inverse=True)[1]
        cells.append(inv.reshape(-1))
    while True:
        old = lab.copy()
        for inv in cells:
            low = np.full(inv.max() + 1, len(P))
            np.minimum.at(low, inv, lab)
            lab = low[inv]
        if (lab == old).all():
            return lab


def _to_trimesh(m, eps=1e-3, nudge=0.005):
    import trimesh
    mesh = m.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    F = np.array(mesh.tri_verts, dtype=np.int64)
    grp = _near_groups(V, eps)
    V = V[grp]
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    zero = E[grp[E[:, 0]] == grp[E[:, 1]]]
    vf = [set() for _ in range(len(V))]
    for fi in np.unique(np.where(np.isin(F, zero))[0]):
        for v in F[fi]:
            vf[v].add(fi)
    rep = np.arange(len(V))
    alive = np.ones(len(F), bool)

    def root(i):
        while rep[i] != i:
            i = rep[i]
        return i
    for a, b in zero:
        a, b = root(a), root(b)
        if a == b:
            continue
        fa, fb = vf[a], vf[b]
        shared = fa & fb
        if len(shared) != 2:
            continue
        opp = {int(v) for f in shared for v in F[f]} - {a, b}
        link = ({int(v) for f in fa for v in F[f]} - {a}) & ({int(v) for f in fb for v in F[f]} - {b})
        if link != opp:
            continue
        for f in shared:
            alive[f] = False
            for v in F[f]:
                vf[v].discard(f)
        for f in fb:
            F[f][F[f] == b] = a
            fa.add(f)
        vf[b] = set()
        rep[b] = a
    F = F[alive]
    used = np.unique(F)
    cnt = np.bincount(grp[used], minlength=len(V))
    pinched = used[cnt[grp[used]] > 1]
    if len(pinched):
        acc = np.zeros_like(V)
        n = np.zeros(len(V))
        for k in range(3):
            np.add.at(acc, F[:, k], V[F].mean(axis=1))
            np.add.at(n, F[:, k], 1)
        d = acc[pinched] / n[pinched, None] - V[pinched]
        V[pinched] += nudge * d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    tm = trimesh.Trimesh(vertices=V, faces=F, process=False)
    tm.remove_unreferenced_vertices()
    return tm


def stl_closed(path):
    """What a slicer sees: reload the STL (vertices merged by position) and check it's closed."""
    import trimesh
    rt = trimesh.load(path)
    return bool(rt.is_watertight and rt.is_winding_consistent and rt.volume > 0)


# ------------------------------------------------------------------------------- pictures
def look(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def render(ax, solids, view, title=''):
    """Flat-shaded orthographic view of [(solid, rgb)] seen from `view` (painter's algorithm)."""
    from matplotlib.collections import PolyCollection
    view = unit(view)
    right = unit(np.cross([0, 0, 1], view)) if abs(view[2]) < 0.999 else np.array([1.0, 0, 0])
    up = np.cross(view, right)
    light = unit(view + 0.6 * up + 0.3 * right)
    size = max(np.ptp(np.reshape(s.bounding_box(), (2, 3)), 0)[:2].max() for s, _ in solids)
    P, C, D = [], [], []
    for solid, rgb in solids:
        mesh = solid.refine_to_length(size / 70).to_mesh()
        v = np.asarray(mesh.vert_properties)[:, :3]
        tri = v[np.asarray(mesh.tri_verts)]
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        front = nrm @ view > 0
        tri, nrm = tri[front], nrm[front]
        P.append(np.stack([tri @ right, tri @ up], -1))
        C.append(np.clip(np.outer(0.35 + 0.65 * np.clip(nrm @ light, 0, 1), rgb), 0, 1))
        D.append(tri.mean(1) @ view)
    P, C, D = np.concatenate(P), np.concatenate(C), np.concatenate(D)
    order = np.argsort(D)
    ax.add_collection(PolyCollection(P[order], facecolors=C[order], edgecolors=C[order], linewidths=0.2))
    pts = P.reshape(-1, 2)
    ax.set_xlim(pts[:, 0].min() - 2, pts[:, 0].max() + 2)
    ax.set_ylim(pts[:, 1].min() - 2, pts[:, 1].max() + 2)
    ax.set_aspect('equal')
    ax.axis('off')
    if title:
        ax.set_title(title, fontsize=10)


def cut_vertical(solid, p0, direction):
    """Rings of `solid` cut by the vertical plane through p0 along `direction`, as (distance, z)."""
    d = unit(direction)
    nrm = np.array([d[1], -d[0]])            # keeps the transform a rotation (determinant +1)
    m = np.array([[d[0], d[1], 0, -(d[0] * p0[0] + d[1] * p0[1])],
                  [0, 0, 1, 0],
                  [nrm[0], nrm[1], 0, -(nrm[0] * p0[0] + nrm[1] * p0[1])]], float)
    return [np.asarray(r) for r in solid.transform(m).slice(0.0).to_polygons()]


def draw_cut(ax, solid, p0, direction, **kw):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    rings = cut_vertical(solid, p0, direction)
    if not rings:
        return
    verts, codes = [], []
    for r in rings:
        verts += list(r) + [r[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(r) - 1) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), **kw))


def profile(ax, key, z_pcb, parts, title, toward, span=26.0):
    """Side view cut through one key along its column, typist on the right: [(solid, kwargs)] plus a
    Choc v1 switch and an MBK keycap (unpressed, and dashed fully pressed)."""
    d = key.eb if np.dot(key.eb, toward) >= 0 else -key.eb
    for solid, kw in parts:
        draw_cut(ax, solid, key.c, d, **kw)
    draw_cut(ax, switches([key], z_pcb), key.c, d, facecolor='#d9a441', edgecolor='#8a6216', lw=0.6)
    draw_cut(ax, keycaps([key], z_pcb), key.c, d, facecolor='#9aa0a8', edgecolor='k', lw=0.6, alpha=0.9)
    draw_cut(ax, keycaps([key], z_pcb, pressed=True), key.c, d, facecolor='none', edgecolor='#444', lw=0.8, ls='--')
    top = z_pcb + MBK['top']
    ax.axhline(top, color='#1f77b4', lw=0.8, ls=':')
    ax.text(-span + 0.5, top + 0.25, f'MBK keycap top, {MBK["top"]:.2f} mm above the PCB', color='#1f77b4', fontsize=7)
    ax.set_xlim(-span, span)
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_ylabel('mm')


def heightmap(solid, step=0.4):
    """Top-surface height of `solid` on a grid (NaN where empty)."""
    import trimesh
    mesh = solid.to_mesh()
    tm = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)
    (x0, y0, _), (x1, y1, z1) = tm.bounds
    X, Y = np.meshgrid(np.arange(x0, x1, step), np.arange(y0, y1, step))
    orig = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, z1 + 5)])
    with np.errstate(divide='ignore', invalid='ignore'):      # degenerate slivers in the ray test
        loc, idx, _ = tm.ray.intersects_location(orig, np.tile([0, 0, -1.0], (len(orig), 1)), multiple_hits=False)
    H = np.full(X.size, np.nan)
    H[idx] = loc[:, 2]
    return H.reshape(X.shape), (x0, x1, y0, y1)
