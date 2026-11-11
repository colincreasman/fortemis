# Forager-based redesign

The PCB, fabrication outputs, both case styles and 34-key ZMK shield in this branch implement
this geometry. The small config here is a layout-only reference; `ergogen/config.yaml` is the
complete hardware generator. The prior 36-key design remains on `main`.

![34-key layout](layout.svg)

The starting reference is the stock Forager rev 2 PCB in
`forager/case/pcb/forager-pcb.kicad_pcb`, from `carrefinho/forager` at
`a6e6b5b4e09cf1c4d99fe2387fd1cc714d6ae394`. Sweep measurements come from the Bling LP
board in `sweep/case/pcb/sweepbling-lp.kicad_pcb`. The pre-existing Fortemis angles are
retained, not copied from the flat-column Sweep.

| Home-key drop below middle (mm) | Pinky | Ring | Index | Inner |
|---|---:|---:|---:|---:|
| Stock Forager | 11 | 5 | 3 | 5 |
| Sweep reference | 18.884 | 6.858 | 5.334 | 7.874 |
| This study | 17.026 | 5 | 3 | 5 |

The Sweep pinky sits 12.026 mm below its ring home key; the Forager's sits 6 mm below.
Here the pinky-to-ring drop is 12.026 mm, while the other Forager home-row drops remain
unchanged. This interprets the request to move **only** the outer column as controlling:
matching every Sweep column drop would require changing the other Forager columns too.
Splaying the ring and pinky also changes their horizontal positions, so this is not a
literal rigid copy of the stock board.

The finger angles from inner to outer are 0, 0, 0, 4 and 10 degrees. Both thumbs retain
the Forager's 25-degree orientation and their measured positions relative to the inner
bottom key; no extra thumb or outward extension is included. The halves are mirrored.
The model uses 18 by 17 mm switch spacing and 17.5 by 16.5 mm keycaps.

Recheck the study (requires Node/npx, PyYAML and Shapely):

```sh
python3 design/forager-sweep-stagger/check.py
```

The SVG shows keycap outlines, not a PCB or a case. Its separation between halves is only
for visualization.

Both PCBs have been rerouted with zero KiCad DRC errors, warnings or unconnected nets.
Both case styles pass modeled component-fit checks, and the sandwich shells clear modeled
MBK keycaps over full travel. All eight STLs reload watertight. All six firmware targets
build locally; UF2s are in `firmware/forager-sweep-stagger/`. Physical printing, assembly and
electrical operation remain untested.

This is a Forager-based ergonomic redesign, not a literal circuit or case copy: Fortemis's
XIAO Plus, diodeless wiring, accessible power switch, Choc v1/v2 footprints, reset lever and
light pipe are retained. The stock Forager instead uses a regular XIAO and diode matrix.
The battery bay moves 2 mm left and 4 mm upward from the previous Fortemis position to clear
the shorter case; the right half mirrors that move. Magnetic tenting legs are not included.
