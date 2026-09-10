"""Figure 1 of the paper — the KUKA iiwa7 flagship certificate (publication version, S14).

Three panels, readable without an oral explanation:

  (a) a 3-D rendering of the real robot (convex silhouettes of Drake's visual meshes), the
      overhead shelf, start and goal as ghosts (arm inclined, free) and the upright transit
      pose, where the certified link (the 40-vertex hull of the certificate, verbatim) strikes
      the shelf;
  (b) a configuration-space cut along the separating joint (shoulder pitch) against base yaw:
      the slab is a full-height collision wall between start and goal;
  (c) the certificate's numbers — every one READ from the S14 reproduce benchmark
      (``benchmarks/results/<stamp>/reproduce.json``), never retyped.

Collision colours come from the convex-body oracle, and the drawing asserts that the pose it
colours as colliding does collide: the figure cannot show a free body inside the obstacle.

S14: rewritten in English with no internal annotation codes; numbers from reproduce.json
(the S11 version read the pre-export-contract benchmark and was in French).

Run: python scripts/make_paper_fig1.py [--reproduce PATH]  ->  benchmarks/figures/paper/fig1.png
"""
from __future__ import annotations

import glob
import json
import math
import os

import numpy as np

from cnp import scenes, viz

SCENE = "scenes/S6_iiwa_real_shelf.yaml"
OUT = os.path.join("benchmarks", "figures", "paper", "fig1.png")
REPRODUCE_GLOB = "benchmarks/results/*/reproduce.json"
ESCAPE = [(-0.6, 0.0), (-0.3, 0.45), (-0.1, 0.6), (0.0, 0.62), (0.1, 0.6), (0.3, 0.45),
          (0.6, 0.0)]                               # (s2, s1): a detour through base yaw
START, GOAL, TRANSIT = "#4a90d9", "#3faa78", "#b8bcc4"
HIT, FREE_BODY = "#c62828", "#e0a93b"


def latest_reproduce(path=None) -> tuple:
    paths = [path] if path else sorted(glob.glob(REPRODUCE_GLOB))
    if not paths:
        raise SystemExit(f"no reproduce benchmark found ({REPRODUCE_GLOB}); run `make reproduce`")
    with open(paths[-1]) as f:
        return json.load(f), paths[-1]


def deg(s) -> float:
    return math.degrees(2.0 * math.atan(float(s)))


def english_joint_names(sc) -> list:
    """Physical joint type per UNLOCKED joint from its effective world axis at the reference
    configuration. A vertical axis is the base YAW for the first such joint and a ROLL about
    the (then vertical) link axis for every later one — the effective axis alone cannot tell
    the two apart (iiwa7: yaw, pitch, roll, pitch, roll, pitch, roll). The joint right after
    the certified link, when unlocked, is the elbow."""
    if sc.robot.kind != "spatial_revolute":
        return [f"joint {i + 1}" for i in range(sc.robot.n)]
    word = {(0, 0, 1): "yaw", (0, 1, 0): "pitch", (1, 0, 0): "roll"}
    locked = sc.robot.locked_angles
    names, seen_yaw = [], False
    for i, e in enumerate(viz._effective_axes(sc)):
        w = word.get(tuple(abs(round(float(v))) for v in e), "rotation")
        if w == "yaw" and i not in locked:
            w, seen_yaw = ("roll" if seen_yaw else "yaw"), True
        names.append(w)
    bl1 = sc.body_link + 1
    if 0 <= bl1 < len(names) and bl1 not in locked:
        names[bl1] = "elbow"
    return [names[i] for i in range(len(names)) if i not in locked]


def joint_box_text(sc) -> str:
    """e.g. 'q1 yaw ±70°, q2 pitch ±70°, q3 roll ±70°; q4–q7 ±143°' (consecutive equal
    symmetric ranges are grouped)."""
    names = english_joint_names(sc)
    items = []
    for i, (lo, hi) in enumerate(sc.box):
        a, b = deg(lo), deg(hi)
        rng = f"±{round(max(abs(a), abs(b)))}°" if abs(a + b) < 1.0 else f"{round(a)}–{round(b)}°"
        items.append((i, names[i], rng))
    out, k = [], 0
    while k < len(items):
        j = k
        while j + 1 < len(items) and items[j + 1][2] == items[k][2] and j + 1 >= 3:
            j += 1
        if j > k:
            out.append(f"q{items[k][0] + 1}–q{items[j][0] + 1} {items[k][2]}")
        else:
            out.append(f"q{items[k][0] + 1} {items[k][1]} {items[k][2]}")
        k = j + 1
    return ", ".join(out)


def plt_patch(colour, label):
    import matplotlib.patches as mpatches
    return mpatches.Patch(facecolor=colour, edgecolor="none", label=label)


def _hull_faces(V):
    """Hull triangles oriented outwards (otherwise the rendering looks hollow)."""
    from scipy.spatial import ConvexHull
    V = np.asarray(V, float)
    c = V.mean(axis=0)
    out = []
    for tri in ConvexHull(V).simplices:
        a, b, d = V[tri[0]], V[tri[1]], V[tri[2]]
        if np.dot(np.cross(b - a, d - a), (a + b + d) / 3.0 - c) < 0:
            tri = [tri[0], tri[2], tri[1]]
        out.append(list(tri))
    return out


def _drake_arm():
    """(link hulls in link frame, pose function) of the real iiwa7, via Drake — the same
    visual meshes and support decimation as the shareable 3-D page."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "export_flagship_3d_html", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "export_flagship_3d_html.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    plant, sg, ctx = mod._plant()
    hulls = mod._link_hulls(plant, sg)

    def posed(s):
        plant.SetPositions(ctx, 2.0 * np.arctan(np.asarray(s, float)))
        out = {}
        for L in mod.LINKS:
            X = plant.EvalBodyPoseInWorld(ctx, plant.GetBodyByName(L)).GetAsMatrix4()
            out[L] = (X[:3, :3] @ hulls[L].T).T + X[:3, 3]
        return out

    return mod.LINKS, mod.CERTIFIED_LINK, posed


_LIGHT = np.array([0.45, -0.72, 0.53])
_LIGHT = _LIGHT / np.linalg.norm(_LIGHT)


def _shade(tri, base):
    import matplotlib.colors as mcolors
    a, b, c = tri
    n = np.cross(b - a, c - a)
    nn = np.linalg.norm(n)
    k = 0.42 if nn == 0 else 0.42 + 0.58 * max(0.0, float(np.dot(n / nn, _LIGHT)))
    r, g, bl = mcolors.to_rgb(base)
    return (min(1, r * k + 0.06), min(1, g * k + 0.06), min(1, bl * k + 0.06))


def _panel_3d(ax, sc, oracle):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    body = scenes._body_fk(sc)
    hv = [[float(c) for c in v] for v in sc.hull_vertices]
    st = np.array([float(v) for v in sc.start_s])
    go = np.array([float(v) for v in sc.goal_s])
    mid = 0.5 * (st + go)
    links, cert_link, posed = _drake_arm()
    zmax = 0.0

    def draw_arm(s, base, alpha, upto=None):
        nonlocal zmax
        W = posed(s)
        tris, cols = [], []
        for L in (links if upto is None else links[:upto]):
            if L == cert_link:
                continue
            V = W[L]
            zmax = max(zmax, float(V[:, 2].max()))
            for f in _hull_faces(V):
                t = [V[i] for i in f]
                tris.append(t)
                cols.append(_shade(t, base))
        B = np.array([body.eval_world_point(v, s) for v in hv])     # the CERTIFICATE's hull
        hit = bool(oracle(s))
        assert hit == (base == TRANSIT), "the figure would contradict the collision oracle"
        for f in _hull_faces(B):
            t = [B[i] for i in f]
            tris.append(t)
            cols.append(_shade(t, HIT if hit else FREE_BODY))
        ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolor="none",
                                             alpha=alpha, zsort="average", rasterized=True))

    draw_arm(st, START, 0.42, upto=4)          # ghosts: base, shoulder and the certified link
    draw_arm(go, GOAL, 0.42, upto=4)
    for _nm, (A, b) in sc.obstacles.items():
        bnds = viz._box_bounds(A, b)
        if bnds is None:
            continue
        (x0, x1), (y0, y1), (z0, z1) = bnds
        x1 = min(x1, 0.5); y1 = min(y1, 0.42); x0 = max(x0, -0.5); y0 = max(y0, -0.42)
        z1 = min(z1, z0 + 0.05)                   # only the useful underside is drawn
        c = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
             [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
        faces = [[c[i] for i in f] for f in
                 ([0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6],
                  [1, 2, 6, 5], [0, 3, 7, 4])]
        ax.add_collection3d(Poly3DCollection(faces, facecolor="0.55", edgecolor="0.3",
                                             alpha=0.32, lw=0.5, zsort="average"))
        ax.text2D(0.60, 0.545, f"overhead shelf\nunderside z = {z0:.2f} m",
                  transform=ax.transAxes, fontsize=7.2, weight="bold", ha="left",
                  va="center", color="#2b2b2b",
                  bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="0.7", alpha=0.85))
    draw_arm(mid, TRANSIT, 0.97)

    handles = [plt_patch(START, "start pose (free): base, shoulder and certified link"),
               plt_patch(GOAL, "goal pose (free): base, shoulder and certified link"),
               plt_patch(TRANSIT, "transit: the arm passes upright (full arm drawn)"),
               plt_patch(HIT, "certified link 3 in collision (40-vertex convex hull)"),
               plt_patch(FREE_BODY, "certified link 3, free")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.02), fontsize=7.0,
              framealpha=0.94, borderpad=0.35, handlelength=1.4)
    ax.set_xlim(-0.4, 0.4); ax.set_ylim(-0.4, 0.4); ax.set_zlim(0, max(1.05, zmax + 0.06))
    ax.set_box_aspect((1, 1, 1.35))
    ax.view_init(elev=15, azim=-62)
    ax.set_xlabel("x (m)", labelpad=-8, fontsize=7)
    ax.set_ylabel("y (m)", labelpad=-8, fontsize=7)
    ax.set_zlabel("z (m)", labelpad=-6, fontsize=7)
    ax.tick_params(labelsize=5.5, pad=-3)
    ax.set_title("(a) KUKA iiwa7: the certified link cannot pass upright",
                 fontsize=9.5, pad=0)


def _panel_cspace(ax, sc, oracle, n=110):
    """Cut along shoulder pitch (the barrier joint) x base yaw, other joints at 0, in degrees."""
    bdim, other = 1, 0
    names = english_joint_names(sc)
    qx = np.linspace(deg(sc.box[bdim][0]), deg(sc.box[bdim][1]), n)
    qy = np.linspace(deg(sc.box[other][0]), deg(sc.box[other][1]), n)
    grid = np.zeros((n, n))
    s = np.zeros(sc.robot.n)
    for b, y in enumerate(qy):
        for a, x in enumerate(qx):
            s[:] = 0.0
            s[bdim], s[other] = math.tan(math.radians(x) / 2), math.tan(math.radians(y) / 2)
            grid[b, a] = 1.0 if oracle(s) else 0.0
    ax.imshow(grid, origin="lower", extent=[qx[0], qx[-1], qy[0], qy[-1]], aspect="auto",
              cmap="Greys", vmin=0, vmax=1.7, alpha=0.85)
    half = deg(sc.delta)
    ax.axvspan(-half, half, color="gold", alpha=0.35, zorder=2)
    ax.text(0, qy[-1] * 0.80, f"slab |φ| ≤ {sc.delta}\n(|q2| ≤ {half:.1f}°)", ha="center",
            fontsize=7.5, weight="bold", zorder=6,
            bbox=dict(boxstyle="round", fc="#fff7e0", ec="#e0c060", alpha=0.95))
    P = np.array([[deg(a), deg(b)] for a, b in ESCAPE])
    ax.plot(P[:, 0], P[:, 1], "--", lw=1.8, color="#7f0000", zorder=4,
            label="attempted detour through base yaw")
    st = [deg(v) for v in sc.start_s]
    go = [deg(v) for v in sc.goal_s]
    ax.plot(st[bdim], st[other], "*", color="#1f77b4", ms=17, mec="k", zorder=5, label="start")
    ax.plot(go[bdim], go[other], "P", color="#2ca02c", ms=13, mec="k", zorder=5, label="goal")
    ax.set_xlabel(f"q2, shoulder {names[bdim]} (deg) — the separating joint", fontsize=8.5)
    ax.set_ylabel(f"q1, base {names[other]} (deg)", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3, fontsize=7.0,
              framealpha=0.95)
    ax.set_title("(b) configuration-space cut: start and goal lie\nin two free components "
                 "(grey = collision)", fontsize=9.5)
    ax.text(0.5, -0.115, "frame = the joint box; cut at q3 = … = q7 = 0",
            transform=ax.transAxes, ha="center", fontsize=7.0, style="italic")


def _sci(x: float) -> str:
    m, e = f"{x:.2e}".split("e")
    return f"{m}e{int(e)}"


def _panel_stats(ax, sc, rep, rep_path):
    import textwrap
    row = rep["rows"]["flagship"]
    gt = row["groundtruth"]
    fid = rep.get("kinematic_fidelity", {})
    st = row["by_status"]
    n_act, n = len(row["active_dims"]), row["dof"]
    passive = row["passive_dims"]
    lines = [
        ("Verdict", f"PROOF, re-checked in exact rational arithmetic by an independent "
                    f"verifier in {row['verify_s']:.2f} s"),
        ("Certificate", f"{row['leaves']} leaves ({st.get('collision', 0)} collision, "
                        f"{st.get('outside', 0)} outside)"),
        ("Active dimensions", f"{n_act} of {n} (q{row['active_dims'][0] + 1}–"
                              f"q{row['active_dims'][-1] + 1}); q{passive[0] + 1}–"
                              f"q{passive[-1] + 1} are covered by the proof at no extra cost"),
        ("LP size per leaf", f"{row['lp_reduced']['rows']:,} rows in the active dimensions "
                             f"vs {row['lp_full']['rows']:,} in full dimension "
                             f"({row['reduction_x']:.0f}× smaller)"),
        ("Separation margins", f"trapping band {gt['slab_penetration_mm']} mm inside the "
                               f"shelf; start and goal clear it by "
                               f"{gt['startgoal_clearance_mm']} mm"),
        ("Fidelity", f"URDF-faithful kinematics: {_sci(fid['chain_flange_position_error_m'])} m "
                     f"at the flange; link-3 hull: {_sci(fid['body_vertex_position_error_m'])} m"
         if "chain_flange_position_error_m" in fid else "(kinematic fidelity not measured)"),
        ("Joint box", joint_box_text(sc)),
    ]
    y = 0.985
    ax.axis("off")
    ax.text(0.0, y, "(c) what the certificate establishes", fontsize=10.5, weight="bold",
            va="top")
    y -= 0.075
    for k, v in lines:
        ax.text(0.0, y, k, fontsize=8.2, weight="bold", va="top", color="#1a237e")
        y -= 0.036
        for chunk in textwrap.wrap(v, 64):
            ax.text(0.025, y, chunk, fontsize=7.6, va="top")
            y -= 0.031
        y -= 0.016
    y -= 0.01
    ax.text(0.0, y, "What it does NOT establish", fontsize=8.2, weight="bold", va="top",
            color="#7a2020")
    y -= 0.036
    for chunk in textwrap.wrap(
            "anything outside this joint box or the modelled geometry; anything about "
            "dynamics, sensing or moving obstacles; fidelity beyond that of the published "
            "URDF. An undecided run would not mean infeasible.", 64):
        ax.text(0.025, y, chunk, fontsize=7.6, va="top", style="italic", color="#7a2020")
        y -= 0.031
    clean = "clean tree" if rep.get("git_dirty_at_start") is False else "DIRTY tree"
    ax.text(0.0, y - 0.02, f"source: {os.path.relpath(rep_path)} · commit "
                           f"{rep['commit'][:7]} · {clean}",
            fontsize=6.0, va="top", color="#666")


def main(reproduce_path=None, out=OUT) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(os.path.dirname(out), exist_ok=True)
    rep, rep_path = latest_reproduce(reproduce_path)
    sc, _ = scenes.load(SCENE)
    oracle = scenes.convex_collision_oracle(sc)

    fig = plt.figure(figsize=(14.4, 6.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.0, 1.05], wspace=0.20,
                          left=0.02, right=0.985, top=0.86, bottom=0.13)
    _panel_3d(fig.add_subplot(gs[0, 0], projection="3d"), sc, oracle)
    _panel_cspace(fig.add_subplot(gs[0, 1]), sc, oracle)
    _panel_stats(fig.add_subplot(gs[0, 2]), sc, rep, rep_path)
    fig.suptitle("Certified infeasibility on a redundant 7-DOF arm: start and goal are free, "
                 "yet no continuous path connects them", fontsize=12.5, y=0.975)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"written {out}  ({os.path.getsize(out) / 1024:.0f} KB)  from {rep_path}")
    return {"figure": out, "reproduce": rep_path, "commit": rep["commit"]}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--reproduce", default=None)
    main(ap.parse_args().reproduce)
