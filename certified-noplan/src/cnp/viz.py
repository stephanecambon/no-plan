"""viz — Meshcat 3D viewer (minimal, S6) + C-space/partition figures (S11).

S6 ships only ``show_scene`` — a *design-inspection* view of a parsed scene: the
planar builtin arm drawn at its start or goal configuration, plus the obstacles, in
Meshcat. It exists so a human can eyeball, BEFORE certifying, that the scene is the
one we mean to prove (V3, CLAUDE.md rule 11). It proves nothing about soundness — the
certificate + :mod:`cnp.verify` are the only arbiters of mathematical truth.

The full ``cnp viz <cert>`` (partition animation, failed leaves, paper figures) is S11.
"""
from __future__ import annotations

import numpy as np

from . import certificate as _cert
from .ratfk import SympyRatFK


def _config_q_to_s(scene: _cert.Scene, which: str):
    s = scene.start_s if which == "start" else scene.goal_s
    return np.array([float(v) for v in s])


def _joint_world_positions(scene: _cert.Scene, s):
    """World positions of every joint origin + the end-effector, for the planar
    builtin arm at s-config ``s`` (all joints assumed unlocked here)."""
    if scene.robot.kind != "planar_revolute":
        raise NotImplementedError(f"show_scene for {scene.robot.kind!r} is S9+")
    fk = SympyRatFK(_cert._planar_joints(scene.robot),
                    locked={k: float(v) for k, v in scene.robot.locked.items()},
                    q_star=[float(v) for v in scene.robot.q_star])
    pts = []
    n_joints = scene.robot.n_joints
    for i in range(n_joints):
        body = fk.body(f"link{i}")
        pts.append(body.eval_world_point([0.0, 0.0, 0.0], s))
    # end-effector = distal endpoint of the last link
    last = fk.body(f"link{n_joints - 1}")
    pts.append(last.eval_world_point([float(scene.robot.link_lengths[-1]), 0.0, 0.0], s))
    return np.array(pts)


def _box_bounds(A, b):
    """Recover ``[(lo,hi)]`` per axis if ``(A,b)`` is an axis-aligned box, else None."""
    A = np.array([[float(x) for x in row] for row in A])
    b = np.array([float(x) for x in b])
    dim = A.shape[1]
    lo = [None] * dim
    hi = [None] * dim
    for row, bj in zip(A, b):
        nz = np.nonzero(row)[0]
        if len(nz) != 1 or abs(abs(row[nz[0]]) - 1.0) > 1e-9:
            return None
        ax = int(nz[0])
        if row[ax] > 0:
            hi[ax] = bj
        else:
            lo[ax] = -bj
    if any(v is None for v in lo + hi):
        return None
    return list(zip(lo, hi))


def show_scene(scene: _cert.Scene, config: str = "start"):
    """Open a Meshcat view of ``scene`` with the arm at ``config`` ('start'|'goal')
    and the obstacles drawn as boxes. Returns the viewer URL (string)."""
    import meshcat
    import meshcat.geometry as g
    import meshcat.transformations as tf

    vis = meshcat.Visualizer()
    vis.delete()

    # --- obstacles (boxes) ---
    for nm, (A, b) in scene.obstacles.items():
        bounds = _box_bounds(A, b)
        node = vis["obstacles"][nm]
        if bounds is None:                      # non-box H-rep: skip with no crash
            continue
        size = [hi - lo for lo, hi in bounds]
        center = [0.5 * (lo + hi) for lo, hi in bounds]
        node.set_object(g.Box(size),
                        g.MeshLambertMaterial(color=0xB0B0B0, opacity=0.55,
                                              transparent=True))
        node.set_transform(tf.translation_matrix(center))

    # --- robot at the chosen config (polyline skeleton + joint spheres) ---
    s = _config_q_to_s(scene, config)
    pts = _joint_world_positions(scene, s)
    colour = 0x1f77b4 if config == "start" else 0x2ca02c
    vis["robot"]["links"].set_object(
        g.Line(g.PointsGeometry(pts.T.astype(np.float32)),
               g.LineBasicMaterial(color=colour, linewidth=4)))
    for i, p in enumerate(pts):
        node = vis["robot"]["joints"][str(i)]
        node.set_object(g.Sphere(0.04),
                        g.MeshLambertMaterial(color=colour))
        node.set_transform(tf.translation_matrix(list(p)))

    return vis.url()
