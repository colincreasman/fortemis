#!/usr/bin/env python3
"""Verify the layout study against the measured reference geometry."""
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ergogen" / "tools"))
from check_layout import measure, run

points = run((ROOT / "ergogen" / "config.yaml").read_text())
drop, angles, thumbs, gap = measure(points)
for name, expected in {"pinky": 17.026, "ring": 5, "middle": 0, "index": 3, "inner": 5}.items():
    assert math.isclose(drop[name], expected, abs_tol=0.01), (name, drop[name])
assert angles == {"pinky": 10, "ring": 4, "middle": 0, "index": 0, "inner": 0}
for name, expected in {
    "thumbs_near_thumb": (2.749, 21.6, -25),
    "thumbs_far_thumb": (17.372, 32.832, -25),
}.items():
    assert all(math.isclose(a, b, abs_tol=0.01) for a, b in zip(thumbs[name], expected)), name
assert len(thumbs) == 2
assert gap[0] >= 0.49, gap

keys = {name: p for name, p in points.items() if name.startswith(("matrix_", "thumbs_"))}
axis_twice = points["matrix_inner_top"]["x"] + points["mirror_matrix_inner_top"]["x"]
for name, p in keys.items():
    mirror = points["mirror_" + name]
    assert math.isclose(p["x"] + mirror["x"], axis_twice, abs_tol=0.001), name
    assert math.isclose(p["y"], mirror["y"], abs_tol=0.001), name
    assert math.isclose(p["r"], -mirror["r"], abs_tol=0.001), name
print("Home-key drops from middle (mm):", drop)
print("Column angles (degrees):", angles)
print("Thumbs relative to inner bottom (x, y down, degrees):", thumbs)
print("Minimum modeled keycap clearance (mm):", round(gap[0], 3))
print("Both halves mirror correctly; 17 keys per half.")

study = run(pathlib.Path(__file__).with_name("config.yaml").read_text())
for name, p in keys.items():
    for coordinate in ("x", "y", "r"):
        assert math.isclose(p[coordinate], study[name][coordinate], abs_tol=0.001), (name, coordinate)
print("Hardware generator matches the layout-only reference.")
