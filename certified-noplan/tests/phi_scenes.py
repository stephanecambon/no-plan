"""Shared S5 phi-pipeline scenes: collision oracle + problem builder for phifit.

Single source of truth for tests/test_phifit.py and scripts/make_figures.py, so the
certified result and the V2 figure are built from the SAME barrier the pipeline fit.

Two scenes:
  * **E4-planaire** — the frozen 2-link relay geometry (reused from cert_scenes); the
    barrier is fit automatically by the pipeline (NO hand hint) and certified
    end-to-end through the EXACT verifier (planar path, full pipeline).
  * **3-DOF spatial** — a generic 3R chain (axes z, y, y). A tall front wall traps the
    distal segment's PROXIMAL endpoint (which depends only on the base yaw s0 and the
    first pitch s1, not on s2) over a band of s0, so every config with |s0| small
    collides for ALL pitches: any path from start (s0<0) to goal (s0>0) must cross the
    colliding band => a genuine disconnection. Certified by the ENGINE (PROOF) and
    cross-checked by dense sampling; the exact verifier stays planar until S9.
"""
from fractions import Fraction as F

import numpy as np

import cert_scenes
import regref
from cnp import certificate as cert, engine, witness
from cnp.ratfk import RevoluteJoint, SympyRatFK

# --------------------------------------------------------------------------- #
# E4 planar (full pipeline -> exact verify)
# --------------------------------------------------------------------------- #

E4_BOXES = [regref.UP, regref.DOWN, regref.MID]
E4_BOX = [(F(-1), F(1)), (F(-1), F(1))]
E4_START = (F(-9, 10), F(0))
E4_GOAL = (F(9, 10), F(0))


def e4_collision(s):
    """Planar 2-link collision oracle in s-space (q = 2 arctan(s), q* = 0)."""
    return regref.in_collision(2 * np.arctan(s[0]), 2 * np.arctan(s[1]), E4_BOXES)


def e4_scene_with(phi: dict, degree: int, delta) -> cert.Scene:
    """E4 geometry (robot/obstacles/body from cert_scenes) with the fitted barrier."""
    sc = cert_scenes.e4_scene()
    sc.phi = {tuple(int(x) for x in e): F(c) for e, c in phi.items()}
    sc.phi_degree = degree
    sc.delta = F(delta)
    return sc


def e4_build_problem(phi, degree, delta) -> engine.Problem:
    return cert.scene_to_problem(e4_scene_with(phi, degree, delta))


# --------------------------------------------------------------------------- #
# 3-DOF spatial (engine PROOF + dense-sampling soundness)
# --------------------------------------------------------------------------- #

def _tr(x, y, z):
    T = np.eye(4)
    T[:3, 3] = [x, y, z]
    return T


def spatial3_body():
    """Generic 3R chain (axes z, y, y) and its distal segment body (the S2 chain)."""
    joints = [RevoluteJoint("j0", _tr(0, 0, 0), np.array([0, 0, 1.0])),
              RevoluteJoint("j1", _tr(0, 0, 0.3), np.array([0, 1.0, 0])),
              RevoluteJoint("j2", _tr(0.3, 0, 0), np.array([0, 1.0, 0]))]
    return SympyRatFK(joints).body("j2")


SP_VBF = [[0.0, 0.0, 0.0], [0.3, 0.0, 0.0]]   # distal link as a 2-vertex segment
# Tall front wall: x in [0.08,0.32], y in [-0.10,0.10], z in [-0.05,0.62].
SP_A = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1],
                 [-1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=float)
SP_B = np.array([0.32, 0.10, 0.62, -0.08, 0.10, 0.05])
SP_BOX = [(F(-7, 10), F(7, 10))] * 3
SP_START = (F(-6, 10), F(0), F(0))
SP_GOAL = (F(6, 10), F(0), F(0))

_SP_BODY = spatial3_body()


def sp_collision(s):
    """Segment-vs-wall collision oracle (sample 40 points along the link segment)."""
    p0 = _SP_BODY.eval_world_point(SP_VBF[0], s)
    p1 = _SP_BODY.eval_world_point(SP_VBF[1], s)
    ts = np.linspace(0, 1, 40)[:, None]
    seg = p0 * (1 - ts) + p1 * ts
    return bool(np.any(np.all(seg @ SP_A.T <= SP_B + 1e-12, axis=1)))


def sp_pair(scale: float = 1.0) -> engine.Pair:
    """The (link, wall) pair. ``scale`` shrinks the wall about its centre for the
    soundness negative control (a shrunk wall opens a free path => no disconnection)."""
    lo = np.array([-SP_B[3], -SP_B[4], -SP_B[5]])
    hi = np.array([SP_B[0], SP_B[1], SP_B[2]])
    mid = 0.5 * (lo + hi)
    lo2, hi2 = mid - (mid - lo) * scale, mid + (hi - mid) * scale
    b = np.array([hi2[0], hi2[1], hi2[2], -lo2[0], -lo2[1], -lo2[2]])
    verts = _SP_BODY.vertex_numerators(SP_VBF)
    return engine.Pair("WALL", verts, _SP_BODY.D, witness.Polytope(SP_A, b))


def sp_build_problem(phi, degree, delta, scale: float = 1.0) -> engine.Problem:
    pt = np.zeros((degree + 1,) * 3)
    for e, c in phi.items():
        pt[tuple(int(x) for x in e)] = float(c)
    return engine.Problem(box=[(float(lo), float(hi)) for lo, hi in SP_BOX], phi=pt,
                          delta=float(delta), pairs=[sp_pair(scale)],
                          lam_degree="affine")
