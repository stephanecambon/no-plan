"""make_scene_figures — top-down 2-D scene figures for design inspection (S6, V3).

Generates ``benchmarks/figures/scene_S2_peigne.png``: the planar 3-DOF comb with the
free start/goal poses AND two in-slab poses (s0=0) showing the middle link caught in
the comb — the story the certificate proves. A planar scene reads far better top-down
than in 3-D Meshcat; ``cnp show <scene> --png`` produces the plain start/goal view.

Run: ``python scripts/make_scene_figures.py`` (or ``make figures``).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cnp import scenes, viz                     # noqa: E402

HERE = os.path.dirname(__file__)
SCENES = os.path.join(HERE, "..", "scenes")
OUT = os.path.join(HERE, "..", "benchmarks", "figures")


def peigne_figure():
    scene, _ = scenes.load(os.path.join(SCENES, "S2_peigne.yaml"))
    poses = [
        ("start (libre, bras vers le bas)", scene.start_s, "#1f77b4"),
        ("dalle s0=0, s1=0  -> link median pris dans MID", [0.0, 0.0, 0.0], "#d62728"),
        ("dalle s0=0, s1=+0.7 -> pris dans UP (relais)", [0.0, 0.7, 0.0], "#ff7f0e"),
        ("goal (libre, bras vers le haut)", scene.goal_s, "#2ca02c"),
    ]
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "scene_S2_peigne.png")
    viz.save_planar_figure(
        scene, path, poses=poses,
        title="S2 peigne 3-DOF : start/goal libres ; toute traversee (s0=0) "
              "prend le link median dans le peigne")
    print("written", os.path.normpath(path))


if __name__ == "__main__":
    peigne_figure()
