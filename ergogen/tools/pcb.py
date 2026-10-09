#!/usr/bin/env python3
"""Build, check, route and export the Fortemis PCBs.

  python3 ergogen/tools/pcb.py build     # ergogen -> pcb/<name>.kicad_pcb + .kicad_pro (JLCPCB rules)
  python3 ergogen/tools/pcb.py drc       # KiCad DRC summary for every board in pcb/
  python3 ergogen/tools/pcb.py route     # Freerouting + GND pours -> pcb/<name>.kicad_pcb, then DRC
                                         # (routed again with other settings until it passes)
  python3 ergogen/tools/pcb.py fab       # gerbers + drill files -> pcb/fab/<name>.zip,
                                         # JLCPCB assembly files -> pcb/fab/<name>_bom.csv, _cpl.csv

Needs: node (npx), KiCad 10 (kicad-cli and KiCad's bundled Python with pcbnew), Java 25+ for
Freerouting 2.5 (downloaded to ~/.cache/fortemis on first use; set JAVA to pick a java binary).
"""
import csv, json, os, pathlib, re, shutil, subprocess, sys, tempfile, urllib.request, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
ERGOGEN = ROOT / 'ergogen'
PCB = ROOT / 'pcb'
BOARDS = ['fortemis_left', 'fortemis_right']
KICAD_PY = os.environ.get('KICAD_PYTHON',
    '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3')
FREEROUTING = 'https://github.com/freerouting/freerouting/releases/download/v2.5.0/freerouting-2.5.0.jar'
# Freerouting settings tried in turn until a board passes KiCad's DRC. Freerouting gives the same
# result for the same board every time, so a board it gets wrong is routed again with other costs.
ROUTER_TRIES = [
    [],
    ['--router.scoring.via_costs=100'],
    ['--router.scoring.via_costs=30'],
    ['--router.scoring.start_ripup_costs=300'],
]
CACHE = pathlib.Path.home() / '.cache' / 'fortemis'

# JLCPCB 2-layer standard capabilities, with some margin
RULES = {
    'min_clearance': 0.2,
    'min_connection': 0.15,
    'min_copper_edge_clearance': 0.3,
    'min_hole_clearance': 0.25,
    'min_hole_to_hole': 0.25,
    'min_through_hole_diameter': 0.3,
    'min_track_width': 0.15,
    'min_via_annular_width': 0.13,
    'min_via_diameter': 0.6,
    'min_text_height': 0.8,
    'min_text_thickness': 0.12,
    'min_silk_clearance': 0.0,
    'solder_mask_to_copper_clearance': 0.0,
    'min_microvia_diameter': 0.2,
    'min_microvia_drill': 0.1,
    'min_resolved_spokes': 2,
    'max_error': 0.005,
    'use_height_for_length_calcs': True,
}
SEVERITIES = {
    'lib_footprint_issues': 'ignore',     # footprints come from ergogen, not a KiCad library
    'lib_footprint_mismatch': 'ignore',
    'footprint_symbol_mismatch': 'ignore',
    'missing_footprint': 'ignore',
    'extra_footprint': 'ignore',
    'net_conflict': 'ignore',
}
NETCLASSES = [
    {'name': 'Default', 'clearance': 0.2, 'track_width': 0.2, 'via_diameter': 0.6, 'via_drill': 0.3},
    {'name': 'Power', 'clearance': 0.2, 'track_width': 0.4, 'via_diameter': 0.7, 'via_drill': 0.35},
]
NETCLASS_PATTERNS = [{'netclass': 'Power', 'pattern': p} for p in ('GND', 'BAT_RAW', 'BAT_P')]
# Footprint -> (BOM comment, part, LCSC number) for the parts JLCPCB can assemble
ASSEMBLY = {
    'switch_choc_v1_v2': ('Kailh Choc v1 hot-swap socket', 'CPG135001S30', 'C5333465'),
    'nut_smd_m2': ('M2 SMD nut, 2 mm', 'SMTSO2020MTJ', 'C2916384'),
    'power_switch_msk12c02_side': ('SPDT slide switch', 'MSK12C02', 'C431540'),
}


def project(name):
    classes = []
    for c in NETCLASSES:
        classes.append({
            'name': c['name'], 'clearance': c['clearance'], 'track_width': c['track_width'],
            'via_diameter': c['via_diameter'], 'via_drill': c['via_drill'],
            'microvia_diameter': 0.3, 'microvia_drill': 0.1, 'diff_pair_gap': 0.25,
            'diff_pair_via_gap': 0.25, 'diff_pair_width': 0.2, 'line_style': 0, 'pcb_color': 'rgba(0, 0, 0, 0.000)',
            'schematic_color': 'rgba(0, 0, 0, 0.000)', 'wire_width': 6, 'bus_width': 12, 'priority': 2147483647,
        })
    return {
        'board': {'design_settings': {
            'rules': RULES,
            'rule_severities': SEVERITIES,
            'track_widths': [0.0, 0.2, 0.4],
            'via_dimensions': [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.6, 'drill': 0.3}],
        }},
        'net_settings': {'classes': classes, 'meta': {'version': 4}, 'netclass_patterns': NETCLASS_PATTERNS},
        'meta': {'filename': f'{name}.kicad_pro', 'version': 3},
    }


def build():
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(['npx', '--yes', 'ergogen@4.2.1', str(ERGOGEN), '-o', d], check=True,
                       capture_output=True)
        PCB.mkdir(exist_ok=True)
        for b in BOARDS:
            shutil.copy(pathlib.Path(d) / 'pcbs' / f'{b}.kicad_pcb', PCB / f'{b}.kicad_pcb')
            (PCB / f'{b}.kicad_pro').write_text(json.dumps(project(b), indent=2) + '\n')
            print(f'pcb/{b}.kicad_pcb')


def drc(board, quiet=False):
    out = pathlib.Path(tempfile.gettempdir()) / f'{board}_drc.json'
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '--severity-all', '-o', str(out),
                    str(PCB / f'{board}.kicad_pcb')], check=True, capture_output=True)
    rep = json.loads(out.read_text())
    errors = [v for v in rep['violations'] if v['severity'] == 'error']
    warnings = [v for v in rep['violations'] if v['severity'] == 'warning']
    unconnected = rep.get('unconnected_items', [])
    print(f'{board}: {len(errors)} errors, {len(warnings)} warnings, {len(unconnected)} unconnected')
    if not quiet:
        for v in errors + warnings:
            items = '; '.join(f"{i['description']} @({i['pos']['x']:.2f},{i['pos']['y']:.2f})" for i in v['items'])
            print(f"  {v['severity']:7s} {v['type']}: {v['description']} | {items}")
    return errors, warnings, unconnected


def kicad(mode, board, path):
    subprocess.run([KICAD_PY, str(pathlib.Path(__file__).with_name('pcb_kicad.py')), mode,
                    str(PCB / f'{board}.kicad_pcb'), str(path)], check=True)


def freerouting():
    jar = CACHE / pathlib.Path(FREEROUTING).name
    if not jar.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FREEROUTING, jar)
    return jar


def java(min_version=25):
    found = [os.environ.get('JAVA'), '/opt/homebrew/opt/openjdk/bin/java', shutil.which('java')]
    if pathlib.Path('/usr/libexec/java_home').exists():
        home = subprocess.run(['/usr/libexec/java_home', '-v', f'{min_version}+'], capture_output=True, text=True)
        found.insert(1, home.stdout.strip() + '/bin/java' if home.returncode == 0 else None)
    for j in filter(None, found):
        if not pathlib.Path(j).exists():
            continue
        v = subprocess.run([j, '-version'], capture_output=True, text=True).stderr
        m = re.search(r'version "(\d+)', v)
        if m and int(m.group(1)) >= min_version:
            return j
    sys.exit(f'Freerouting needs Java {min_version}+; install it or set JAVA=/path/to/bin/java')


def route(board):
    """Route the board, retrying with the next ROUTER_TRIES settings until KiCad's DRC is clean.
    Returns True if it is."""
    jar, java_bin = freerouting(), java()
    with tempfile.TemporaryDirectory() as d:
        dsn, ses = pathlib.Path(d) / f'{board}.dsn', pathlib.Path(d) / f'{board}.ses'
        kicad('dsn', board, dsn)
        for extra in ROUTER_TRIES:
            ses.unlink(missing_ok=True)
            # one optimizer thread: slower, but the same board every time
            r = subprocess.run([java_bin, '-jar', str(jar), '-de', str(dsn), '-do', str(ses), '-mt', '1',
                                '--gui.enabled=false', *extra], cwd=d, capture_output=True, text=True)
            log = r.stdout + r.stderr
            done = re.findall(r'Auto-routing stage completed.*?\(\d+ unrouted and \d+ violations\)', log)
            print(f'{board}{" (" + " ".join(extra) + ")" if extra else ""}: '
                  + (done[-1] if done else 'Freerouting did not finish'))
            failed = log[log.find('could not be routed'):].split('\n')[1:20] if 'could not be routed' in log else []
            for line in failed:
                if line.strip().startswith(('Net', '-')):
                    print('  ' + line.strip())
            if r.returncode or not ses.exists():
                sys.exit(log[-3000:])
            kicad('ses', board, ses)
            if not any(drc(board)):
                return True
    print(f'{board}: no router settings gave a clean board')
    return False


def geom(board):
    """The board's outline, footprints and pads (pcb_kicad.py geom), quietly unless it fails."""
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / 'geom.json'
        r = subprocess.run([KICAD_PY, str(pathlib.Path(__file__).with_name('pcb_kicad.py')), 'geom',
                            str(PCB / f'{board}.kicad_pcb'), str(path)], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)
        return json.loads(path.read_text())


def assembly(board):
    """Parts JLCPCB can place, all on the back: [(ref, lib, x, y, rot)] in placement-file axes (mm, y up,
    like the Gerbers). The switch footprints are excluded from KiCad's own placement export, so each
    one stands in for its hot-swap socket, centred between the socket's two pads."""
    rows = []
    for f in geom(board)['footprints']:
        if f['lib'] not in ASSEMBLY:
            continue
        assert f['back'], f['ref']
        x, y = f['x'], f['y']
        if f['lib'].startswith('switch_'):
            pads = [p for p in f['pads'] if p['kind'] == 'smd']
            assert len(pads) == 2, f['ref']
            x, y = (pads[0]['x'] + pads[1]['x']) / 2, (pads[0]['y'] + pads[1]['y']) / 2
        rows.append((f['ref'], f['lib'], x, -y, f['rot'] % 360))
    order = list(ASSEMBLY)
    return sorted(rows, key=lambda r: (order.index(r[1]), int(re.sub(r'\D', '', r[0]))))


def fab(board):
    out = PCB / 'fab' / board
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    pcb = str(PCB / f'{board}.kicad_pcb')
    layers = 'F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'
    subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers', '-l', layers, '--no-protel-ext', '-o', f'{out}/', pcb],
                   check=True, capture_output=True)
    subprocess.run(['kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
                    '--generate-map', '--map-format', 'gerberx2', '-o', f'{out}/', pcb], check=True, capture_output=True)
    z = PCB / 'fab' / f'{board}.zip'
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(out.iterdir()):
            zf.write(f, f.name)
    print(z.relative_to(ROOT))

    # JLCPCB's assembly files. The XIAO and the battery are soldered by hand, so they're left out.
    rows = assembly(board)
    bom, cpl = PCB / 'fab' / f'{board}_bom.csv', PCB / 'fab' / f'{board}_cpl.csv'
    with bom.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for lib, (comment, footprint, lcsc) in ASSEMBLY.items():
            w.writerow([comment, ','.join(r[0] for r in rows if r[1] == lib), footprint, lcsc])
    with cpl.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for ref, _, x, y, rot in rows:
            w.writerow([ref, f'{x:.4f}', f'{y:.4f}', 'Bottom', f'{rot:g}'])
    print(bom.relative_to(ROOT))
    print(cpl.relative_to(ROOT))


def main():
    sys.stdout.reconfigure(line_buffering=True)  # keep our lines in order with KiCad's and Java's
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'
    boards = sys.argv[2:] or BOARDS
    if cmd == 'build':
        build()
    elif cmd == 'drc':
        for b in boards: drc(b)
    elif cmd == 'route':
        if not all([route(b) for b in boards]):
            sys.exit(1)
    elif cmd == 'fab':
        for b in boards: fab(b)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
