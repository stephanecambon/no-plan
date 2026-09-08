"""S11 [A40] — invariant TESTÉ de l'artefact 3D PARTAGEABLE.

`benchmarks/figures/share/*_3d.html` est un artefact d'ARGUMENT : c'est lui qu'un prospect
ouvre. Il doit donc être adossé à un test qui reproduit l'oracle de vérité (règle 11 / A40),
d'autant qu'il quitte le repo et vit sa vie dans un deck.

Le test relit le JSON EMBARQUÉ dans le HTML livré (pas une re-génération : l'objet réel), et
vérifie que :
  (1) le CORPS dessiné à chaque pose est bien celui de la chaîne du CERTIFICAT (les sommets
      monde stockés = FK de la coque gelée à cette configuration, à 1e-9 près) ;
  (2) le VERDICT de collision affiché coïncide avec `scenes.convex_collision_oracle` (A43) —
      la page ne recalcule aucune collision, elle affiche celui-ci, et s'il divergeait
      l'artefact mentirait ;
  (3) les poses start/goal annoncées sont bien celles de la scène, et l'obstacle dessiné est
      bien celui du certificat.
Ne demande NI Drake NI réseau (le fichier livré suffit).
"""
from __future__ import annotations

import json
import os
import re

import numpy as np
import pytest

from cnp import scenes, viz

CASES = [("benchmarks/figures/share/S6_iiwa_real_shelf_3d.html",
          "scenes/S6_iiwa_real_shelf.yaml"),
         ("benchmarks/figures/share/usecase_binpicking_iiwa7_3d.html",
          "scenes/usecase_binpicking_iiwa7.yaml"),
         ("benchmarks/figures/share/usecase_capot_surete_iiwa7_3d.html",
          "scenes/usecase_capot_surete_iiwa7.yaml")]


def _embedded(path: str) -> dict:
    src = open(path).read()
    m = re.search(r"^const D = (\{.*\});$", src, re.M)
    assert m, f"{path}: bloc de données embarqué introuvable"
    return json.loads(m.group(1))


@pytest.mark.parametrize("html,scene_path", CASES)
def test_share_html_does_not_lie(html, scene_path):
    assert os.path.exists(html), f"artefact manquant {html}"
    D = _embedded(html)
    sc, _ = scenes.load(scene_path)
    fk = scenes._body_fk(sc)
    hull = [[float(c) for c in v] for v in sc.hull_vertices]
    orac = scenes.convex_collision_oracle(sc)

    assert D["scene"] == os.path.basename(scene_path)
    assert set(D["obstacles"]) == set(sc.obstacles)
    assert len(D["links"]) == 8 and sum(L["certified"] for L in D["links"]) == 1
    assert len(D["body_hull_faces"]) > 0

    for k, P in enumerate(D["poses"]):
        s = np.asarray(P["s"], float)
        # (1) le corps dessiné EST le corps du certificat, posé par la chaîne du certificat
        W = np.array([fk.eval_world_point(v, s) for v in hull])
        assert np.abs(W - np.asarray(P["body_world"], float)).max() < 1e-9, \
            f"{html}: pose {k} — corps dessiné != FK de la coque certifiée"
        # (2) le verdict affiché EST celui de l'oracle corps-convexe (A43)
        assert bool(P["colliding"]) is bool(orac(s)), \
            f"{html}: pose {k} — verdict de collision affiché != oracle"
        assert abs(P["phi"] - viz.phi_eval(sc, s)) < 1e-12

    st = np.array([float(v) for v in sc.start_s])
    go = np.array([float(v) for v in sc.goal_s])
    assert np.allclose(D["poses"][D["start_idx"]]["s"], st)
    assert np.allclose(D["poses"][D["goal_idx"]]["s"], go)
    # le récit tient : les deux poses sont libres, et le transit central est en collision
    assert not D["poses"][D["start_idx"]]["colliding"]
    assert not D["poses"][D["goal_idx"]]["colliding"]
    assert D["poses"][len(D["poses"]) // 2]["colliding"]
