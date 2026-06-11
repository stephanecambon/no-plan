"""Exact-rational :class:`cnp.certificate.Scene` builders for the regression scenes.

The S4 counterpart of tests/eng_scenes.py: it turns the frozen planar oracle scenes
(``regref``: UP/DOWN/MID obstacles, hand / learned barrier) into the EXACT-rational
scene model that the certificate generator and the independent verifier share. The
planar 2-link arm is expressed as a generic revolute chain (axes +z, unit links), and
the 2-D obstacle boxes are embedded as 3-D boxes extruded over z in [-1, 1] (exactly
the S2 embedding) so the certified partition reproduces the oracle (E3 = 46 leaves,
E4 = 78 leaves). ``regref`` itself stays pristine.

Start/goal are given as EXACT rational s-images on opposite sides of the slab: the
disconnection theorem is certified between two genuine configurations
q = q* + 2 arctan(s), and condition (i) is then checkable in exact arithmetic (the
true tan(theta/2) of the demo angles is irrational; we pin rational witnesses, which
is what the certificate proves — CLAUDE.md rule 6, honest scope).
"""
from fractions import Fraction as F

import regref
from cnp import certificate as cert

NAMES = ["UP", "DOWN", "MID"]


def _box3_hrep(bb, den=1000):
    """2-D box (xlo,xhi,ylo,yhi) -> exact 3-D H-rep extruded over z in [-1, 1]."""
    xlo, xhi, ylo, yhi = (F(v).limit_denominator(den) for v in bb)
    A = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, 0, 0], [0, -1, 0], [0, 0, -1]]
    b = [xhi, yhi, F(1), -xlo, -ylo, F(1)]
    return A, b


def _robot():
    return cert.Robot(kind="planar_revolute", link_lengths=[1, 1], q_star=[0, 0])


def _obstacles():
    return {nm: _box3_hrep(bb)
            for nm, bb in zip(NAMES, [regref.UP, regref.DOWN, regref.MID])}


def e3_scene(start_s=(F(-9, 10), F(0)), goal_s=(F(9, 10), F(0))) -> cert.Scene:
    """E3: hand barrier phi = s0, delta = 1/20, three relaying obstacles (46 leaves)."""
    return cert.Scene(robot=_robot(), body_link=1, hull_vertices=[[0, 0, 0], [1, 0, 0]],
                      obstacles=_obstacles(), phi={(1, 0): 1}, phi_degree=2,
                      delta=F(1, 20), box=[(-1, 1), (-1, 1)],
                      start_s=list(start_s), goal_s=list(goal_s), pairs=list(NAMES))


def e4_scene(den=10 ** 6, start_s=(F(-9, 10), F(0)),
             goal_s=(F(9, 10), F(0))) -> cert.Scene:
    """E4: learned (least-squares) barrier, rationalised to denominators <= ``den``
    (78 leaves, reproducing the oracle)."""
    phi_fit, delta_f, _start, _goal = regref.fit_phi_e4(
        [regref.UP, regref.DOWN, regref.MID])
    phi = {}
    for i in range(phi_fit.shape[0]):
        for j in range(phi_fit.shape[1]):
            c = float(phi_fit[i, j])
            if abs(c) > 1e-12:
                phi[(i, j)] = F(c).limit_denominator(den)
    delta = F(float(delta_f)).limit_denominator(den)
    return cert.Scene(robot=_robot(), body_link=1, hull_vertices=[[0, 0, 0], [1, 0, 0]],
                      obstacles=_obstacles(), phi=phi, phi_degree=2, delta=delta,
                      box=[(-1, 1), (-1, 1)], start_s=list(start_s),
                      goal_s=list(goal_s), pairs=list(NAMES))
