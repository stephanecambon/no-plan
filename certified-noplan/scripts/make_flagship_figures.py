"""S10 — V6 figures for the 7-DOF flagship (scenes/S5_iiwa_shelf.yaml).

Two static complements to the interactive A24 artifact:
  - C-space cut (base yaw s0 × shoulder pitch s1): slab in gold, collision wall separating
    home from cible, a dashed escape attempt that detours over the top yet plunges into the
    wall (A20: shows why one would believe a path exists), A25 joint limits footer;
  - SWEEP (A20 NON NÉGOCIABLE): the arm at poses interpolated home->cible, colliding poses in
    red — the arm appears to almost reach (cible proche/visible), then every mid pose collides.

PLAUSIBILITÉ / intention (rule 11). The proof is `cnp certify` + `cnp verify` (exact).
Run: ``python scripts/make_flagship_figures.py`` -> benchmarks/figures/S10_flagship/*.png
"""
from __future__ import annotations

import os

from cnp import scenes, viz

OUT = os.path.join("benchmarks", "figures", "S10_flagship")
SCENE = os.path.join("scenes", "S5_iiwa_shelf.yaml")

ESCAPE = [(-0.6, 0.0), (-0.45, 0.6), (-0.2, 0.68), (0.0, 0.68), (0.2, 0.68), (0.45, 0.6), (0.6, 0.0)]


def main():
    os.makedirs(OUT, exist_ok=True)
    sc, _ = scenes.load(SCENE)
    oracle = scenes.collision_oracle(sc, n_samples=60)

    cpath = os.path.join(OUT, "S5_iiwa_shelf_cspace.png")
    viz.save_cspace_figure(
        sc, oracle, cpath, axes=(0, 1), n=160,
        title="FLAGSHIP étagère pharma (7-DOF tous libres) — casier haut inatteignable"
              "\n[apparence faisable A20 ; plausibilité — preuve : cnp certify + cnp verify]",
        axis_labels=("lacet base  s0  (q0 = 2·arctan s0)", "tangage épaule  s1"),
        paths=[("tentative d'évasion (détour par le haut)", ESCAPE)],
        footer=viz.limits_caption(sc),
    )
    print("wrote", cpath)

    spath = os.path.join(OUT, "S5_iiwa_shelf_sweep.png")
    viz.save_sweep_figure(
        sc, oracle, spath, n=11, project=(0, 1),
        title="Sweep home->cible (vue de dessus) — poses en collision en ROUGE (A20)")
    print("wrote", spath)


if __name__ == "__main__":
    main()
