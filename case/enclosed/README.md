# Enclosed case: Fortemis

The Forager-style case (requirements C1–C3): a 2.2 mm top plate that sits on the PCB and holds the
switches, and a base tray with the battery recess, the print-in-place reset lever, the light pipe and
the openings for USB-C and the power switch. One of the two designs in [`case/`](../README.md); the
other is the [sandwich case](../sandwich/README.md).

![Fortemis case](../../docs/img/case.png)

| File | What it is |
|---|---|
| `fortemis_left_top.stl`, `fortemis_right_top.stl` | Top plates: 147.9 × 122.1 × 2.2 mm |
| `fortemis_left_base.stl`, `fortemis_right_base.stl` | Bases: 147.9 × 122.1 × 6.2 mm |

The parts are in the assembly's coordinates (z = 0 is the PCB's bottom face), so a top and base
loaded together line up.

- Parts list: [build guide, Case](../../docs/build-guide.md#case)
- Printing and fitting: [build guide](../../docs/build-guide.md#printing-the-case)
- How it was designed and checked: [design log](../../docs/design-log.md#2026-10-08-case-ergogentoolscasepy)

Rebuild from the PCBs (needs KiCad 10 and `pip install -r ergogen/tools/requirements.txt`):

```sh
python3 ergogen/tools/case.py        # case/enclosed/*.stl and docs/img/case.png
```
