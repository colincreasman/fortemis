# Sandwich case: Fortemis

The [enclosed case](../enclosed/README.md) with a Totemist-style top (requirement C4). The keycaps sit
in wells and the rim comes up to just under their tops, so from the side the keyboard reads as one
solid block, the profile of ErgoMech's Totemist and of GEIST's TOTEM it's derived from. ErgoMech
calls this a sandwich case.

![preview](fortemis_sandwich_preview.png)

## What it keeps from the enclosed case

Everything from requirements C1–C3:

- **The top's plate:** the same 2.2 mm plate on the PCB, cut exactly like the enclosed top: switch
  cut-outs with the clip chamfers, switch-puller grooves, the four top-screw countersinks and the
  pockets over solder joints. Switches clip in and screws seat exactly as before.
- **The base:** identical, with its battery recess, reset lever, light pipe, USB-C slot and
  power-switch notch. `fortemis_<half>_base.stl` here is the enclosed base.
- **Screws and nuts:** the same 9 × M2×4 countersunk screws per half (4 top, 5 bottom) into the five
  SMD nuts. The top screws sit on the same seats, at the bottom of a 4.8 mm hole in the rim.
- **Size:** the same 147.9 × 122.1 mm outline.

## What's new: the height

The rim's height is copied from the TOTEM case (measured from GEIST's STEP files), and the Totemist
follows the TOTEM:

| Above the PCB top | Height |
|---|---|
| Plate top (well floor) | 2.2 mm |
| Choc v1 stem top, unpressed | 8.0 mm |
| **Rim top** | **9.05 mm** (TOTEM's: 6.85 mm above the plate) |
| MBK keycap top | 10.5 mm, so the caps stand **1.45 mm** above the rim, as on the Totemist |

On the desk it's 15.3 mm to the rim and 16.7 mm to the keycap tops, the same keycap height as the
enclosed case and just under the Totemist's 17 mm. For a rim exactly level with MBK tops, rebuild
with `--rim 10.5`.

![side profile: enclosed vs sandwich](fortemis_sandwich_profile.png)

Also copied from the TOTEM and Totemist:

- **Wells:** 1.0 mm between every keycap and the wall, a 0.5 mm chamfer on the rim's inside edges
  and a 1.5 mm round on its outside edge. Where columns are staggered or splayed, the wall steps with
  them.
- **Thumb shelf:** in front of the three thumb keys there is no rim, just the plate, so the wall
  can't catch your thumbs.
- **Hollow rim:** a 1.5 mm roof on walls and on ribs every 12 mm that rest on the PCB, open
  underneath. It's light, it feels as solid as a plate, and no bridge is wider than 10.4 mm, so it
  prints on an FDM printer without supports. There are no closed cavities.

## Files

| File | What it is |
|---|---|
| `fortemis_left_top.stl`, `fortemis_right_top.stl` | Top shells: 147.9 × 122.1 × 9.05 mm, 23.7 cm³ each |
| `fortemis_left_base.stl`, `fortemis_right_base.stl` | Bases: the enclosed case's, 147.9 × 122.1 × 6.2 mm |
| `fortemis_sandwich_preview.png`, `fortemis_sandwich_profile.png` | Renders and side views |
| `fortemis_sandwich_report.json` | Check results |

Like the enclosed parts, they're in the assembly's coordinates (z = 0 is the PCB's bottom face).

## Parts, printing and fitting

Follow the [build guide](../../docs/build-guide.md): the parts list is the same, and so is the base.
For the top:

- **Printing:** print it the way it's oriented, plate down. No supports needed: the wells' walls are
  vertical and the roof bridges at most 10.4 mm between ribs. To order it instead, upload the four
  STLs to JLCPCB's 3D printing (SLA resin) and ask in the remark to keep supports off the top of the
  rim and the well floors; supports inside the hollow underside are fine.
- **Fitting** (build guide step 2): the top screws go down the four holes in the rim, so use a
  1.3 mm hex key at least 8 mm long. Press a few switches through their wells first, to line the
  top up.
- **Keycaps:** MBK, or any Choc-spaced cap up to 17.5 × 16.5 mm. Each has 1 mm to the wall; lift
  one off with a fingernail or a thin plastic pry tool, or use the switch puller.

## Rebuilding

```sh
pip install -r ergogen/tools/requirements.txt          # needs KiCad 10, like case.py
python3 ergogen/tools/case_sandwich.py                 # case/sandwich/*, about 15 s
python3 ergogen/tools/case_sandwich.py --rim 10.5      # rim level with MBK keycap tops
```

`case_sandwich.py` loads the board, the plate cuts and the base from `case.py`, then adds the rim
with `sandwich.py`, which is the same file in the Sweep and Forager repos. Its `Sandwich(...)`
settings include `cap_clear` (1.0), `roof` (1.5), `wall` / `inner_wall` (1.6 / 1.2), `shelf` (True)
and `ribs` (12 mm pitch, 1.2 mm wide).

Every run repeats `case.py`'s checks against the component models, and also checks the top against
Choc v1 switches and MBK keycaps over their full travel, and for closed pockets. All of them pass.

## Limits

- **Sweat:** the plate still covers the PCB everywhere but under the switches. But the wells hold drops
  on the plate where a flat plate lets them run off its edge, the same as on the Totemist, so wipe it
  down.
- **Not built yet:** like the rest of Fortemis, untested on hardware.
- **Keycaps:** the height is set for MBK. Taller caps stand further above the rim.
