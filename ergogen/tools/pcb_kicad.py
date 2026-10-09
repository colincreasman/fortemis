"""KiCad-side steps of `pcb.py route`. Runs under KiCad's bundled Python (needs pcbnew).

  pcb_kicad.py dsn <board.kicad_pcb> <out.dsn>   # export a Specctra DSN patched for Freerouting
  pcb_kicad.py ses <board.kicad_pcb> <in.ses>    # import the routes, pour + stitch GND, save
  pcb_kicad.py geom <board.kicad_pcb> <out.json> # outline, footprints and pads for case.py
"""
import math, re, sys
import pcbnew

MM, TO_MM = pcbnew.FromMM, pcbnew.ToMM
BUMP_UM = 10          # route 10 um wider than the rules: Freerouting rounds, KiCad's DRC doesn't
EDGE_STRIP = 0.1      # mm wide keepout along the inside of the board edge (see edge_keepouts)
POUR_NET = 'GND'


def scope_end(text, start):
    depth = 0
    for j in range(start, len(text)):
        if text[j] == '(':
            depth += 1
        elif text[j] == ')':
            depth -= 1
            if depth == 0:
                return j
    raise ValueError('unbalanced DSN')


def bbox_mm(polys):
    xs, ys = [], []
    for i in range(polys.OutlineCount()):
        c = polys.Outline(i)
        for n in range(c.PointCount()):
            xs.append(c.CPoint(n).x)
            ys.append(c.CPoint(n).y)
    return TO_MM(min(xs)), TO_MM(min(ys)), TO_MM(max(xs)), TO_MM(max(ys))


# Delete, not Remove: Remove hands the item to Python, whose garbage collector then frees it under
# pcbnew's feet.
def strip_board(b):
    """Drop routing and copper pours, so the board can be routed again from scratch."""
    for t in list(b.GetTracks()):
        b.Delete(t)
    for z in list(b.Zones()):
        if not z.GetIsRuleArea():
            b.Delete(z)


def drop_pour_only_rule_areas(b):
    # KiCad exports every rule area as a keepout for everything, including the antenna's
    # "no copper pour" area, which would stop traces crossing it.
    pour_only = lambda z: z.GetIsRuleArea() and not z.GetDoNotAllowTracks() and not z.GetDoNotAllowVias()
    for fp in b.GetFootprints():
        for z in list(fp.Zones()):
            if pour_only(z):
                fp.Delete(z)
    for z in list(b.Zones()):
        if pour_only(z):
            b.Delete(z)


def edge_keepouts(b, width=EDGE_STRIP, tile=10.0):
    """Polygons (DSN um, y up) covering a thin strip along the inside of the board edge.

    Freerouting's own boundary clearance makes some pads near the edge unreachable, so we keep
    the default boundary rule and add these instead: 0.1 mm strip + 0.2 mm clearance clears
    KiCad's 0.3 mm copper-to-edge rule. Tiled, since DSN keepouts can't have holes.
    """
    outline = pcbnew.SHAPE_POLY_SET()
    assert b.GetBoardPolygonOutlines(outline, False), 'board outline is not closed'
    inner = pcbnew.SHAPE_POLY_SET(outline)
    inner.Deflate(MM(width), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.005))
    ring = pcbnew.SHAPE_POLY_SET(outline)
    ring.BooleanSubtract(inner)
    x0, y0, x1, y1 = bbox_mm(outline)
    x0, y0 = x0 - 1, y0 - 1
    nx, ny = math.ceil((x1 - x0 + 1) / tile), math.ceil((y1 - y0 + 1) / tile)
    polys = []
    for i in range(nx):
        for j in range(ny):
            sq = pcbnew.SHAPE_POLY_SET()
            sq.NewOutline()
            for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1)):
                sq.Append(MM(x0 + (i + dx) * tile), MM(y0 + (j + dy) * tile))
            piece = pcbnew.SHAPE_POLY_SET(ring)
            piece.BooleanIntersection(sq)
            for k in range(piece.OutlineCount()):
                c = piece.Outline(k)
                if abs(c.Area()) < MM(0.05) ** 2:
                    continue
                polys.append([(c.CPoint(n).x / 1000, -c.CPoint(n).y / 1000) for n in range(c.PointCount())])
    return polys


def patch_dsn(text, b):
    text = re.sub(r'\(clearance (\d+(?:\.\d+)?)\)', lambda m: f'(clearance {float(m.group(1)) + BUMP_UM:g})', text)
    # GND is poured after routing instead
    k0 = text.index('(network')
    m = re.search(r'\(net %s\s' % re.escape(POUR_NET), text[k0:])
    if m:
        k = k0 + m.start()
        text = text[:k] + text[scope_end(text, k) + 1:]
    text = re.sub(r'\(class [^()]*', lambda m: re.sub(r'(?<=\s)%s(?=\s)' % re.escape(POUR_NET), '', m.group(0)), text)
    keepouts = ''.join(
        f'    (keepout "" (polygon {ly} 0  ' + '  '.join(f'{x:.1f} {y:.1f}' for x, y in p) + '))\n'
        for p in edge_keepouts(b) for ly in ('F.Cu', 'B.Cu'))
    k = scope_end(text, text.index('(boundary')) + 1
    return text[:k] + '\n' + keepouts + text[k:]


def export_dsn(pcb, path):
    b = pcbnew.LoadBoard(pcb)
    strip_board(b)
    drop_pour_only_rule_areas(b)
    assert pcbnew.ExportSpecctraDSN(b, path), 'DSN export failed'
    with open(path) as f:
        text = f.read()
    with open(path, 'w') as f:
        f.write(patch_dsn(text, b))


def fill(b):
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()


def add_pours(b, net, clearance=0.3, min_width=0.25):
    outline = pcbnew.SHAPE_POLY_SET()
    assert b.GetBoardPolygonOutlines(outline, False), 'board outline is not closed'
    zones = []
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(b)
        z.SetLayer(layer)
        z.SetNet(net)
        z.SetZoneName(f'{net.GetNetname()} {b.GetLayerName(layer)}')
        z.Outline().Append(outline)
        z.SetLocalClearance(MM(clearance))
        z.SetMinThickness(MM(min_width))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.5))
        z.SetThermalReliefSpokeWidth(MM(0.5))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        b.Add(z)
        zones.append(z)
    return zones


def stitch(b, net, zf, zb, pitch=10.0, step=0.5, via_d=0.6, drill=0.3, margin=0.05, min_gap=2.0,
           avoid_refs=('MCU1',)):
    """GND vias wherever both pours are, on a coarse grid, plus one in every F.Cu piece left over.

    All the GND pads are on the back, so without these the front pour floats.
    """
    region = zf.GetFilledPolysList(pcbnew.F_Cu).CloneDropTriangulation()
    region.BooleanIntersection(zb.GetFilledPolysList(pcbnew.B_Cu))
    region.Deflate(MM(via_d / 2 + margin), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.005))
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            region.BooleanSubtract(z.Outline())
    for f in b.GetFootprints():
        if f.GetReference() in avoid_refs:  # nothing under the XIAO
            hull = f.GetBoundingHull()
            hull.Inflate(MM(0.5), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.005))
            region.BooleanSubtract(hull)
    region.BuildBBoxCaches()
    pt = lambda p: pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))
    x0, y0, x1, y1 = bbox_mm(region)
    cand = [(x0 + i * step, y0 + j * step)
            for i in range(int((x1 - x0) / step) + 1)
            for j in range(int((y1 - y0) / step) + 1)]
    cand = [p for p in cand if region.Contains(pt(p), -1, 0, True)]
    chosen = []
    free = lambda p: all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= min_gap ** 2 for q in chosen)
    cells = {}
    for p in cand:
        cells.setdefault((math.floor((p[0] - x0) / pitch), math.floor((p[1] - y0) / pitch)), []).append(p)
    for (cx, cy), pts in sorted(cells.items()):
        c = (x0 + (cx + 0.5) * pitch, y0 + (cy + 0.5) * pitch)
        for p in sorted(pts, key=lambda p: (p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2):
            if free(p):
                chosen.append(p)
                break
    front = zf.GetFilledPolysList(pcbnew.F_Cu)
    front.BuildBBoxCaches()
    for k in range(front.OutlineCount()):
        inside = [p for p in cand if front.Contains(pt(p), k, 0, True)]
        if inside and not any(front.Contains(pt(p), k, 0, True) for p in chosen):
            mx, my = sum(p[0] for p in inside) / len(inside), sum(p[1] for p in inside) / len(inside)
            chosen.append(min(inside, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2))
    for p in chosen:
        v = pcbnew.PCB_VIA(b)
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetPosition(pt(p))
        v.SetWidth(MM(via_d))
        v.SetDrill(MM(drill))
        v.SetNet(net)
        b.Add(v)
    return len(chosen)


def import_ses(pcb, path):
    b = pcbnew.LoadBoard(pcb)
    strip_board(b)
    assert pcbnew.ImportSpecctraSES(b, path), 'SES import failed'
    net = b.FindNet(POUR_NET)
    zf, zb = add_pours(b, net)
    fill(b)
    n = stitch(b, net, zf, zb)
    fill(b)
    b.Save(pcb)
    print(f'{n} {POUR_NET} stitching vias')


def dump_geom(pcb, path):
    """Board outline, footprints and pads (mm, KiCad axes: y down) for case.py."""
    import json
    b = pcbnew.LoadBoard(pcb)
    ps = pcbnew.SHAPE_POLY_SET()
    assert b.GetBoardPolygonOutlines(ps, False), 'board outline is not closed'
    chain = lambda c: [[TO_MM(c.CPoint(i).x), TO_MM(c.CPoint(i).y)] for i in range(c.PointCount())]
    outline = [{'outer': chain(ps.Outline(i)), 'holes': [chain(ps.Hole(i, h)) for h in range(ps.HoleCount(i))]}
               for i in range(ps.OutlineCount())]
    kinds = {pcbnew.PAD_ATTRIB_PTH: 'th', pcbnew.PAD_ATTRIB_NPTH: 'npth', pcbnew.PAD_ATTRIB_SMD: 'smd'}
    fps = []
    for f in b.GetFootprints():
        pads = []
        for p in f.Pads():
            pos, size = p.GetPosition(), p.GetSize(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
            drill = p.GetDrillSize()
            pads.append({'name': p.GetNumber(), 'net': p.GetNetname(), 'x': TO_MM(pos.x), 'y': TO_MM(pos.y),
                         'w': TO_MM(size.x), 'h': TO_MM(size.y), 'rot': p.GetOrientationDegrees(),
                         'kind': kinds.get(p.GetAttribute(), 'other'),
                         'drill': [TO_MM(drill.x), TO_MM(drill.y)],
                         'front': p.IsOnLayer(pcbnew.F_Cu), 'back': p.IsOnLayer(pcbnew.B_Cu)})
        pos = f.GetPosition()
        fps.append({'ref': f.GetReference(), 'lib': f.GetFPID().GetLibItemName().wx_str(),
                    'x': TO_MM(pos.x), 'y': TO_MM(pos.y), 'rot': f.GetOrientationDegrees(),
                    'back': f.IsFlipped(), 'pads': pads})
    thickness = TO_MM(b.GetDesignSettings().GetBoardThickness())
    with open(path, 'w') as fh:
        json.dump({'thickness': thickness, 'outline': outline, 'footprints': fps}, fh, indent=1)


if __name__ == '__main__':
    mode, pcb, path = sys.argv[1:4]
    {'dsn': export_dsn, 'ses': import_ses, 'geom': dump_geom}[mode](pcb, path)
