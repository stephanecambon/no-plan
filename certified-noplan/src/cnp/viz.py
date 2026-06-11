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


def save_planar_figure(scene: _cert.Scene, path: str, poses=None, title=None):
    """Top-down 2-D figure of a planar scene (the natural view for design inspection,
    V3): obstacle teeth as labelled rectangles, the arm drawn at each pose as a thick
    polyline with joint dots. ``poses`` is a list of ``(label, s_array, colour)``;
    defaults to start (blue) and goal (green). Returns ``path``.

    Unlike the 3-D Meshcat view, this reads at a glance for a planar arm and lets us
    show an in-slab pose (where the body link is caught in the comb) next to the free
    start/goal — the story the certificate proves."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    if poses is None:
        poses = [("start", _config_q_to_s(scene, "start"), "#1f77b4"),
                 ("goal", _config_q_to_s(scene, "goal"), "#2ca02c")]

    fig, ax = plt.subplots(figsize=(7, 7))
    for nm, (A, b) in scene.obstacles.items():
        bnds = _box_bounds(A, b)
        if bnds is None:
            continue
        (xlo, xhi), (ylo, yhi) = bnds[0], bnds[1]
        ax.add_patch(Rectangle((xlo, ylo), xhi - xlo, yhi - ylo,
                               facecolor="0.6", edgecolor="0.3", alpha=0.7))
        ax.text((xlo + xhi) / 2, (ylo + yhi) / 2, nm, ha="center", va="center",
                fontsize=9, weight="bold")

    for label, s, colour in poses:
        pts = _joint_world_positions(scene, np.asarray(s, dtype=float))
        ax.plot(pts[:, 0], pts[:, 1], "-", color=colour, lw=3, label=label, zorder=3)
        ax.plot(pts[:, 0], pts[:, 1], "o", color=colour, ms=7, zorder=4)
    ax.plot(0, 0, "ks", ms=9, zorder=5)            # base
    ax.set_aspect("equal")
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="upper left")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(title or "scene (top-down)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def save_cspace_figure(scene: _cert.Scene, oracle, path, axes=(0, 1), n=140,
                       fixed=None, title=None):
    """Configuration-space figure (the view that shows 'goal free but UNREACHABLE'):
    a 2-D slice over two s-axes, collision shaded grey, the slab ``{|phi|<=delta}``
    in gold, start (★) and goal (✚) marked. When the slab is a full COLLISION WALL
    spanning the box between start and goal, they sit in different free components —
    no continuous free path connects them. That separation IS the disconnection the
    certificate proves; here the eye can see it (the certificate, not the eye, is the
    proof — CLAUDE.md rule 11).

    ``oracle(s)`` is the collision predicate (e.g. ``scenes.planar_collision_oracle``);
    ``axes`` picks the two plotted s-variables; ``fixed`` sets the others (default 0)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    i, j = axes
    fixed = fixed or {}
    (xlo, xhi) = (float(scene.box[i][0]), float(scene.box[i][1]))
    (ylo, yhi) = (float(scene.box[j][0]), float(scene.box[j][1]))
    xs = np.linspace(xlo, xhi, n)
    ys = np.linspace(ylo, yhi, n)
    grid = np.zeros((n, n))
    s = np.zeros(scene.robot.n)
    for k, v in fixed.items():
        s[k] = v
    for a, sx in enumerate(xs):
        for b, sy in enumerate(ys):
            s[i], s[j] = sx, sy
            grid[b, a] = 1.0 if oracle(s) else 0.0

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    ax.imshow(grid, origin="lower", extent=[xlo, xhi, ylo, yhi], aspect="auto",
              cmap="Greys", vmin=0, vmax=1.6, alpha=0.85)        # grey = collision

    # slab |phi| <= delta: when phi = s_i (the relay barrier), it is the vertical
    # band |s_i| <= delta on this slice — a full-height COLLISION WALL if disconnected.
    delta = float(scene.delta)
    phi_is_axis_i = set(scene.phi) == {tuple(1 if t == i else 0 for t in range(scene.robot.n))}
    if phi_is_axis_i:
        ax.axvspan(-delta, delta, color="gold", alpha=0.35, zorder=2,
                   label=f"dalle |phi|<={scene.delta}")

    st = [float(v) for v in scene.start_s]
    go = [float(v) for v in scene.goal_s]
    ax.plot(st[i], st[j], "*", color="#1f77b4", ms=20, mec="k", zorder=5, label="start")
    ax.plot(go[i], go[j], "P", color="#2ca02c", ms=16, mec="k", zorder=5, label="goal")
    ax.set_xlabel(f"s{i}")
    ax.set_ylabel(f"s{j}")
    ax.legend(loc="upper right", framealpha=0.95)
    ax.set_title(title or "C-space slice (grey = collision)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


_CONFIG_COLOUR = {"start": 0x1f77b4, "goal": 0x2ca02c}   # start = blue, goal = green


def _draw_robot(vis, scene, config, colour):
    """Draw the arm at one config as a polyline skeleton + joint spheres."""
    import meshcat.geometry as g
    import meshcat.transformations as tf

    pts = _joint_world_positions(scene, _config_q_to_s(scene, config))
    root = vis["robot"][config]
    root["links"].set_object(
        g.Line(g.PointsGeometry(pts.T.astype(np.float32)),
               g.LineBasicMaterial(color=colour, linewidth=4)))
    for i, p in enumerate(pts):
        node = root["joints"][str(i)]
        node.set_object(g.Sphere(0.04), g.MeshLambertMaterial(color=colour))
        node.set_transform(tf.translation_matrix(list(p)))


def show_scene(scene: _cert.Scene, config: str = "both"):
    """Open ONE Meshcat view of ``scene`` and the obstacles, drawing the arm at the
    requested config(s): ``"both"`` (default — start in blue AND goal in green in the
    same scene, so the two poses are compared without launching two servers),
    ``"start"`` or ``"goal"`` for a single pose. Returns the viewer URL (string)."""
    import meshcat
    import meshcat.geometry as g
    import meshcat.transformations as tf

    vis = meshcat.Visualizer()
    vis.delete()

    # --- obstacles (boxes) ---
    for nm, (A, b) in scene.obstacles.items():
        bounds = _box_bounds(A, b)
        if bounds is None:                      # non-box H-rep: skip with no crash
            continue
        size = [hi - lo for lo, hi in bounds]
        center = [0.5 * (lo + hi) for lo, hi in bounds]
        node = vis["obstacles"][nm]
        node.set_object(g.Box(size),
                        g.MeshLambertMaterial(color=0xB0B0B0, opacity=0.55,
                                              transparent=True))
        node.set_transform(tf.translation_matrix(center))

    # --- robot at the requested config(s), all in the same viewer ---
    configs = ["start", "goal"] if config == "both" else [config]
    for cfg in configs:
        _draw_robot(vis, scene, cfg, _CONFIG_COLOUR[cfg])

    return vis.url()
