"""S11 [A40] — invariant TESTÉ de l'artefact 3D PARTAGEABLE.

`benchmarks/figures/share/*_3d.html` est un artefact d'ARGUMENT : c'est lui qu'un lecteur ouvre,
et il quitte le repo pour vivre sa vie dans un deck. Il doit donc être adossé à un test qui
reproduit l'oracle de vérité (règle 11 / A40) — sur le FICHIER LIVRÉ, pas sur une re-génération.

Ce que le test vérifie, sur chacun des trois artefacts :
  (1) **structure** — le fichier embarque bien la chaîne GELÉE (19 joints, 12 verrouillés, 7
      curseurs), la coque 40 sommets DU certificat, la barrière sur `s1`, les dims actives
      re-mesurées, un ancrage par lien, et les étiquettes d'axes PHYSIQUES corrigées
      (lacet, tangage, lacet, … — finding S10-quater : lire l'axe brut mettrait « lacet » sur
      le séparateur q2, une viz qui ment) ;
  (2) **le corps dessiné est celui du certificat** — la coque embarquée est, coefficient par
      coefficient, celle de la scène ;
  (3) **la page ne peut pas mentir sur la collision** — sa couche JS (cinématique de la chaîne
      + GJK) est rejouée sous `node` sur des configurations seedées et doit rendre EXACTEMENT
      le verdict de `scenes.convex_collision_oracle` (A43), y compris aux coins distaux de la
      dalle où la thèse « robuste à la redondance » se joue ;
  (4) **l'ancrage des liens sur la chaîne** est consigné et sous tolérance (l'export échoue
      au-delà — c'est là qu'un robot « qui bouge faux » serait attrapé).

`node` est optionnel : le volet (3) SKIPPE si node est absent, il n'échoue jamais pour ça.
"""
from __future__ import annotations

import itertools
import json
import os
import shutil
import subprocess

import numpy as np
import pytest

from cnp import certificate as _cert
from cnp import scenes, viz

CASES = [("benchmarks/figures/share/S6_iiwa_real_shelf_3d.html",
          "scenes/S6_iiwa_real_shelf.yaml"),
         ("benchmarks/figures/share/usecase_binpicking_iiwa7_3d.html",
          "scenes/usecase_binpicking_iiwa7.yaml"),
         ("benchmarks/figures/share/usecase_capot_surete_iiwa7_3d.html",
          "scenes/usecase_capot_surete_iiwa7.yaml")]
POSE_TOL = 5e-6


def _page(path: str) -> tuple:
    """(données embarquées, couche JS pure) du fichier LIVRÉ."""
    assert os.path.exists(path), f"artefact manquant {path} (lancer scripts/export_flagship_3d_html.py)"
    src = open(path).read()
    body = src.split("<script>", 1)[1]                      # après le <script src=CDN>
    data = json.loads(body.split("const SC = ", 1)[1].split(";\n", 1)[0])
    compute = body.split("// ── rendu", 1)[0]               # FK + GJK, sans une ligne de Three.js
    return data, compute


@pytest.mark.parametrize("html,scene_path", CASES)
def test_share_html_structure_and_body(html, scene_path):
    data, compute = _page(html)
    sc, _ = scenes.load(scene_path)

    assert data["scene"] == os.path.basename(scene_path)
    assert data["panel_names"] == list(sc.obstacles)
    assert len(data["joints"]) == 19
    assert sum(j["locked"] is not None for j in data["joints"]) == 12
    assert data["body_link"] == sc.body_link == 7
    assert data["barrier_dim"] == viz._barrier_dim(sc) == 1
    assert data["active_dims"] == [0, 1, 2] and data["passive_dims"] == [3, 4, 5, 6]

    # (1) un curseur par joint DÉBLOQUÉ, étiqueté par l'axe EFFECTIF (pas l'axe-chaîne brut)
    assert len(data["joint_names"]) == len(sc.box) == 7
    assert [n.split()[0] for n in data["joint_names"]] == \
        ["lacet", "tangage", "lacet", "tangage", "lacet", "tangage", "lacet"]
    assert len(data["limits_deg"]) == 7                                     # A25

    # (2) le corps dessiné EST la coque du certificat, verbatim
    hull = np.array([[float(_cert.Q(c)) for c in v] for v in sc.hull_vertices])
    assert np.array_equal(np.array(data["hull"], dtype=float), hull)
    assert len(data["hull"]) == 40 and len(data["body_faces"]) > 0

    # (4) ancrage des liens sur la chaîne gelée : 8 liens, un seul certifié, erreur sous tolérance
    assert len(data["links"]) == 8
    assert sum(L["certified"] for L in data["links"]) == 1
    assert all(len(L["C"]) == 16 for L in data["links"])
    assert data["links"][0]["chain"] == -1                                  # base soudée au monde
    assert float(data["pose_err"]) <= POSE_TOL

    # la page n'embarque QUE Three.js comme ressource externe
    src = open(html).read()
    assert src.count("<script src=") == 1 and "cdnjs.cloudflare.com" in src


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
@pytest.mark.parametrize("html,scene_path", CASES)
def test_share_html_js_matches_convex_oracle(html, scene_path):
    """(3) A40 : la couche JF FK+GJK de la page LIVRÉE rend exactement le verdict de l'oracle
    corps-convexe Python, y compris aux coins distaux de la dalle (thèse de la redondance)."""
    data, compute = _page(html)
    sc, _ = scenes.load(scene_path)
    oracle = scenes.convex_collision_oracle(sc)
    n = len(sc.box)
    lo = np.array([float(l) for l, _ in sc.box])
    hi = np.array([float(h) for _, h in sc.box])
    delta = float(sc.delta)

    rng = np.random.default_rng(20260908)
    cfgs = [list(rng.uniform(lo, hi)) for _ in range(250)]
    cfgs += [[float(x) for x in sc.start_s], [float(x) for x in sc.goal_s]]   # idx 250, 251
    others = [i for i in range(n) if i != 1]
    for combo in itertools.product(*[(lo[i] + 1e-6, hi[i] - 1e-6) for i in others]):
        s = [0.0] * n
        for i, v in zip(others, combo):
            s[i] = v
        cfgs.append(list(s))                                                 # coins de dalle, idx>=252

    js = compute + "\nconst CFG=%s;console.log(JSON.stringify(CFG.map(collide)));\n" % json.dumps(cfgs)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        jp = os.path.join(td, "check.js")
        open(jp, "w").write(js)
        res = subprocess.run(["node", jp], capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, res.stderr
    js_res = json.loads(res.stdout)
    py_res = [oracle(c) for c in cfgs]
    mism = [i for i, (a, b) in enumerate(zip(js_res, py_res)) if a != b]
    assert not mism, f"{len(mism)} écarts JS/Python, ex. cfg {mism[0]}: {cfgs[mism[0]]}"

    assert py_res[250] is False and py_res[251] is False                     # start / goal libres
    assert all(js_res[252:]), "une config de dalle aux extrêmes distaux est libre (évasion ?)"
    assert len(js_res[252:]) == 2 ** 6
