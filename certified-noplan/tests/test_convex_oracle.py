"""S10-quater Tâche 1 — the convex-body vs H-rep ground-truth oracle (A43).

The faithful iiwa silhouette is a 40-vertex convex body; `scenes.collision_oracle` only samples
the SEGMENT hull[0]..hull[-1] (blind to a K-vertex body — S10-ter finding). `convex_collision_oracle`
tests conv(vertices) ∩ {Ay<=b} via an LP. Hand-checkable cube-vs-box cases pin the LP core; an
integration case exercises the real frozen iiwa body (FK via sympy + frozen hull — no Drake)."""
from __future__ import annotations

import os
import sys
from fractions import Fraction as F

import numpy as np

from cnp import scenes

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

# unit cube [0,1]^3 (8 corners) and a box H-rep helper
CUBE = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], dtype=float)


def _box_hrep(lo, hi):
    A = np.vstack([np.eye(3), -np.eye(3)])
    b = np.array(list(hi) + [-v for v in lo], dtype=float)
    return A, b


def test_convex_hrep_intersect_handcases():
    # overlapping box [0.5,2]^3 shares [0.5,1]^3 with the unit cube -> intersect
    A, b = _box_hrep([0.5, 0.5, 0.5], [2, 2, 2])
    assert scenes._convex_hrep_intersect(CUBE, A, b) is True
    # disjoint box [2,3]^3 -> no intersection
    A, b = _box_hrep([2, 2, 2], [3, 3, 3])
    assert scenes._convex_hrep_intersect(CUBE, A, b) is False
    # touching box [1,2]^3 meets the cube at the corner (1,1,1) -> intersect (closed polytope)
    A, b = _box_hrep([1, 1, 1], [2, 2, 2])
    assert scenes._convex_hrep_intersect(CUBE, A, b) is True
    # a thin slab that slices through the cube's interior -> intersect
    A, b = _box_hrep([0.4, -5, -5], [0.6, 5, 5])
    assert scenes._convex_hrep_intersect(CUBE, A, b) is True


def _iiwa_body_scene(panel_b):
    """The real frozen iiwa link-3 body on the frozen chain (no Drake: sympy FK + frozen hull)."""
    import json
    import build_iiwa7_scene as bs
    body = json.load(open(bs.BODY_OUT))
    hull = [[F(x) for x in v] for v in body["hull_vertices"]]
    box = [["-7/10", "7/10"], ["-1/4", "1/4"], ["-1/4", "1/4"],
           ["-3", "3"], ["-3", "3"], ["-3", "3"], ["-3", "3"]]
    data = bs.emit_scene(hull, panel_b, box, ["-3/5"] + ["0"] * 6, ["3/5"] + ["0"] * 6)
    import yaml
    sc, _ = scenes.parse_scene(yaml.safe_load(yaml.safe_dump(data)))
    return sc


def test_convex_oracle_on_real_iiwa_body():
    """At s=0 the link-3 body sits near (x,y)~0, z in [~0.5,0.8] (frozen-chain FK). A panel
    enclosing that region collides; the same panel pushed to z in [5,6] is free."""
    s0 = [0.0] * 7
    # panel covering the body's q=0 world region -> collision
    near = _iiwa_body_scene(["1", "1", "9/10", "1", "1", "-2/5"])     # x,y in [-1,1], z in [2/5,9/10]
    assert scenes.convex_collision_oracle(near)(s0) is True
    # same shape pushed far up in z -> free
    far = _iiwa_body_scene(["1", "1", "6", "1", "1", "-5"])           # z in [5,6]
    assert scenes.convex_collision_oracle(far)(s0) is False
