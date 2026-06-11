"""Engine-side adapters for the frozen regression scenes (E3/E4).

Single source of truth for turning the planar oracle scenes (``regref``: UP/DOWN/MID
obstacles, hand/learned barrier) into ``cnp.engine.Problem`` instances. Imported by
both tests/test_engine.py and scripts/make_figures.py so the certified partition and
the figure are built from the *same* problem. ``regref`` itself stays pristine (the
frozen G0' oracle); the 3D embedding here is exactly the S2 one (planar body at z=0,
obstacles extruded over z in [-1, 1], the two z-faces slack).
"""
import numpy as np

import regref
from cnp import engine, witness
from cnp.polylin import mono

LIM = [(-1.0, 1.0), (-1.0, 1.0)]
NAMES = ["UP", "DOWN", "MID"]


def _body():
    """Distal segment of the 2-link planar arm as a 3D body (two hull vertices at
    z=0), numerators over the common denominator D — the S2 embedding."""
    D, P1X, P1Y, C12, S12 = regref.fk_tensors()
    Z = np.zeros_like(P1X)
    return [[P1X, P1Y, Z], [P1X + C12, P1Y + S12, Z]], D


def _box3(b, zh=1.0):
    xlo, xhi, ylo, yhi = b
    return witness.Polytope.box([xlo, ylo, -zh], [xhi, yhi, zh])


def pairs(boxes, names):
    verts, D = _body()
    return [engine.Pair(nm, verts, D, _box3(b)) for b, nm in zip(boxes, names)]


def e3_problem(**kw):
    """E3: hand barrier phi = s1, delta = 0.05, three relaying obstacles."""
    boxes = [regref.UP, regref.DOWN, regref.MID]
    return engine.Problem(box=[tuple(c) for c in LIM], phi=mono(2, 2, [1, 0]),
                          delta=0.05, pairs=pairs(boxes, NAMES), **kw)


def heavy_problem(dup=10, **kw):
    """E3 with each obstacle duplicated ``dup`` times: identical coverage (still a
    true premise ⇒ PROOF) but ``3*dup`` LP solves per cell — a deliberately heavy,
    well-balanced load to demonstrate the multiprocessing speedup (CLAUDE.md S3). A
    realistic proxy for the per-leaf LP cost of n>=5 scenes (more pairs/faces)."""
    boxes = [regref.UP, regref.DOWN, regref.MID]
    prs = []
    for d in range(dup):
        prs.extend(pairs(boxes, [f"{nm}{d}" for nm in NAMES]))
    return engine.Problem(box=[tuple(c) for c in LIM], phi=mono(2, 2, [1, 0]),
                          delta=0.05, pairs=prs, **kw)


def e4_problem(**kw):
    """E4: learned (least-squares) barrier over the same obstacles. Returns
    ``(problem, start, goal)`` (start/goal in joint space, for the figure)."""
    boxes = [regref.UP, regref.DOWN, regref.MID]
    phi, delta, start, goal = regref.fit_phi_e4(boxes)
    prob = engine.Problem(box=[tuple(c) for c in LIM], phi=phi, delta=delta,
                          pairs=pairs(boxes, NAMES), **kw)
    return prob, start, goal
