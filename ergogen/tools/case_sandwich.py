#!/usr/bin/env python3
"""Generate the Fortemis sandwich case: the enclosed (Forager-style) case with a Totemist-style top.

  python3 ergogen/tools/case_sandwich.py                 # both halves -> case/sandwich/
  python3 ergogen/tools/case_sandwich.py --rim 10.5      # rim exactly level with MBK keycap tops

Everything from the enclosed case (case.py) stays: the same base, nuts, M2x4 screws, reset lever,
light pipe, USB-C and power-switch openings, and the top's 2.2 mm plate with the Forager's switch
cut-outs, clip chamfers, puller grooves and countersinks. The top shell adds a rim that rises to
just under the keycap tops, so every key sits in a well (ErgoMech's Totemist, GEIST's TOTEM).
Shell geometry: sandwich.py, shared with the Sweep and Forager repos.

Needs KiCad 10 and `pip install -r ergogen/tools/requirements.txt` (plus trimesh and rtree for the
pictures).
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import case as C  # noqa: E402
import sandwich as sw  # noqa: E402

OUT = C.ROOT / 'case' / 'sandwich'
TOWARD_USER = (0.0, -1.0)


def keys_of(half):
    out = []
    for k in half.keys:
        ang = math.degrees(math.atan2(k.ea[1], k.ea[0])) % 180
        out.append(sw.Key(k.o, k.ea, thumb=min(ang, 180 - ang) > 18))
    return out


def plate_cuts(half):
    """The enclosed top's plate details, exactly as case.py cuts them."""
    cuts = [half.switch_cut(k) for k in half.keys]
    for c in half.top_screws:
        cuts += [C.cone(c, C.SCREW_D / 2, C.Z_PCB - 1, C.SCREW_D / 2, C.Z_TOP + 1),
                 C.cone(c, C.SCREW_D / 2, C.Z_TOP - C.TOP_CSK_DEPTH, C.TOP_CSK_D / 2 + 0.1, C.Z_TOP + 0.1)]
    cuts += [C.cone(c, d / 2, C.Z_PCB - 1, d / 2, C.Z_PCB + C.POCKET_DEPTH) for c, d in half.solder]
    return C.union(cuts)


def build(board, rim):
    half = C.Half(board)
    keys = keys_of(half)
    screws = [dict(c=tuple(c), bore=C.TOP_CSK_D + 0.3) for c in half.top_screws]
    s = sw.Sandwich(half.outline, C.Z_PCB, keys, TOWARD_USER, plate_cuts(half), screws=screws, rim=rim)
    top = sw.trim_thin(s.build(), 0.8)
    s.info['trimmed_mm3'] = round(s.solid.volume() - top.volume(), 2)
    return half, keys, s, top, half.base()


def pictures(built):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    shell, base, cap, gold, green = (0.16, 0.17, 0.19), (0.55, 0.62, 0.72), (0.82, 0.82, 0.84), (0.85, 0.65, 0.25), (0.15, 0.45, 0.25)
    half, keys, s, top, bot = built['fortemis_left']
    _, keys_r, _, top_r, bot_r = built['fortemis_right']
    pcb = C.prism(half.board, 0, C.Z_PCB)
    fig, ax = plt.subplots(2, 2, figsize=(18, 13), dpi=90)
    sw.render(ax[0, 0], [(bot, base), (top, shell), (sw.keycaps(keys, C.Z_PCB), cap)], sw.look(30, -105),
              'Left half assembled, MBK keycaps')
    sw.render(ax[0, 1], [(bot, base), (pcb, green), (sw.switches(keys, C.Z_PCB), gold),
                         (top.translate([0, 0, 24]), shell)], sw.look(35, -60), 'Top shell lifted off')
    H, (x0, x1, y0, y1) = sw.heightmap(top)
    im = ax[1, 0].imshow(H - C.Z_PCB, origin='lower', extent=[x0, x1, y0, y1], cmap='viridis')
    fig.colorbar(im, ax=ax[1, 0], shrink=0.8, label='height above the PCB (mm)')
    ax[1, 0].set_title('Top shell from above: rim (yellow), thumb shelf and well floors (purple)', fontsize=10)
    ax[1, 0].set_aspect('equal')
    ax[1, 0].axis('off')
    sw.render(ax[1, 1], [(bot_r, base), (top_r, shell), (sw.keycaps(keys_r, C.Z_PCB), cap)], sw.look(30, -75),
              'Right half assembled')
    fig.tight_layout()
    fig.savefig(OUT / 'fortemis_sandwich_preview.png')
    plt.close(fig)

    main = [k for k in keys if not k.thumb]
    xm = np.median([k.c[0] for k in main])
    col = sorted(main, key=lambda k: abs(k.c[0] - xm))[:3]
    home = sorted(col, key=lambda k: k.c[1])[1]
    thumb = sorted([k for k in keys if k.thumb], key=lambda k: k.c[0])[1]
    style = lambda colr: dict(facecolor=colr, edgecolor='k', lw=0.5)
    fig, ax = plt.subplots(2, 2, figsize=(16, 8.5), dpi=100)
    for j, (name, tp) in enumerate((('Enclosed (Forager-style)', half.top()), ('Sandwich (Totemist-style)', top))):
        parts = [(bot, style('#8d9db8')), (pcb, style('#2a7a3e')), (tp, style('#2a2b30'))]
        sw.profile(ax[0, j], home, C.Z_PCB, parts, f'{name}: middle-finger column, you are on the right', TOWARD_USER, span=34)
        sw.profile(ax[1, j], thumb, C.Z_PCB, parts, f'{name}: middle thumb key, you are on the right', TOWARD_USER, span=24)
    for a in ax.flat:
        a.set_ylim(-5.5, 14.5)
    for a in ax[:, 1]:
        a.axhline(s.info['rim_z'], color='#d62728', lw=0.8, ls=':')
        a.text(a.get_xlim()[0] + 0.5, s.info['rim_z'] - 0.9, f'sandwich rim {s.info["rim_above_pcb"]:.2f} mm above the PCB',
               color='#d62728', fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / 'fortemis_sandwich_profile.png')
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('boards', nargs='*', default=C.BOARDS)
    ap.add_argument('--rim', type=float, default=sw.TOTEM['rim'],
                    help=f'rim height above the PCB top (default {sw.TOTEM["rim"]}, like the TOTEM/Totemist; '
                         f'{sw.MBK["top"]} = level with MBK keycap tops)')
    ap.add_argument('--no-preview', action='store_true')
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    report, built, ok = dict(rim_above_pcb=a.rim, mbk_top_above_pcb=sw.MBK['top'], halves={}), {}, True
    for board in a.boards:
        print(board)
        half, keys, s, top, bot = build(board, a.rim)
        ok &= half.check({'top': top, 'base': bot})          # case.py's component models
        r = sw.report('top', top, {'switches': sw.switches(keys, C.Z_PCB),
                                   'keycaps, full travel': sw.keycap_sweep(keys, C.Z_PCB)})
        r['closed_pockets'] = sw.closed_pockets(top, half.outline, C.Z_PCB, a.rim)
        r['ok'] = r['ok'] and not r['closed_pockets']
        print(f"  top vs Choc v1 switches and MBK keycaps over full travel: gaps {r['gap_mm']}; "
              f"closed pockets {len(r['closed_pockets'])} -> {'OK' if r['ok'] else 'CHECK'}")
        ok &= r['ok']
        for name, solid in (('top', top), ('base', bot)):
            closed = sw.write_stl(solid, OUT / f'{board}_{name}.stl')
            print(f'  wrote {board}_{name}.stl, watertight after reload: {closed}')
            ok &= closed
        report['halves'][board] = dict(shell=s.info, keycap_check=r, top_screws=len(half.top_screws), nuts=len(half.nuts))
        built[board] = half, keys, s, top, bot
    (OUT / 'fortemis_sandwich_report.json').write_text(json.dumps(report, indent=1, default=str))
    if not a.no_preview and set(C.BOARDS) <= set(built):
        pictures(built)
    print('checks', 'passed' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
