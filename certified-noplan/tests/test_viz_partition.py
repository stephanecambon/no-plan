"""S11 [A11 + A40] — invariant TESTÉ de la figure de partition slab-aware.

A40 (revue G4') : tout artefact de viz qui porte un ARGUMENT doit être adossé à un test qui
reproduit l'oracle de vérité et asserte l'égalité. La figure de partition porte l'argument
central du projet (« voici ce que le certificat prouve »), et la dette A11 (depuis V1) est
précisément qu'une partition peinte en plein ferait croire qu'on certifie de la collision en
zone LIBRE : le témoin est slab-aware (``g - mu·T >= 0``), il n'impose rien là où ``T < 0``.

Trois invariants, tous sur le certificat ARCHIVÉ du flagship réel :
  (1) **honnêteté** — tout point peint « prouvé » est dans la dalle ET dans une feuille
      collision (c'est la définition, vérifiée indépendamment du code de dessin) ;
  (2) **non-mensonge** — tout point peint « prouvé » est en collision d'après l'ORACLE
      CORPS-CONVEXE (A43). Si la figure peignait du certifié en zone libre, ce test tombe ;
  (3) **suffisance** — la dalle de la coupe est ENTIÈREMENT couverte : c'est ce qui fait la
      déconnexion (un trou dans le mur = pas de preuve).
"""
from __future__ import annotations

import numpy as np

from cnp import certificate, scenes, viz

SCENE = "scenes/S6_iiwa_real_shelf.yaml"
CERT = "scenes/S6_iiwa_real_shelf.cert.json"


def test_partition_mask_is_honest_and_does_not_lie():
    sc, _ = scenes.load(SCENE)
    cert = certificate.load(CERT)
    bdim = viz._barrier_dim(sc)                       # s1 = q2 (shoulder pitch)
    other = 0
    axes = (bdim, other)
    n = 34
    xs = np.linspace(float(sc.box[bdim][0]), float(sc.box[bdim][1]), n)
    ys = np.linspace(float(sc.box[other][0]), float(sc.box[other][1]), n)
    certified, in_slab, leaf_of = viz.certified_collision_mask(sc, cert["leaves"], axes, xs, ys)

    assert certified.any() and in_slab.any()
    # (1) honnêteté : certifié ⊆ dalle, et certifié ⊆ union des feuilles collision
    assert not (certified & ~in_slab).any(), "un point 'prouvé' hors de la dalle"
    coll_leaf = {k for k, lf in enumerate(cert["leaves"]) if lf["status"] == "collision"}
    assert all(leaf_of[b, a] in coll_leaf
               for b in range(n) for a in range(n) if certified[b, a])

    # (2) non-mensonge : certifié ⟹ l'oracle CORPS-CONVEXE voit une collision (A43)
    orac = scenes.convex_collision_oracle(sc)
    s = np.zeros(sc.robot.n)
    checked = 0
    for b in range(0, n, 3):
        for a in range(0, n, 3):
            if not certified[b, a]:
                continue
            s[:] = 0.0
            s[bdim], s[other] = xs[a], ys[b]
            assert orac(s), f"figure ment : 'prouvé' mais libre à s={s}"
            checked += 1
    assert checked > 20, "échantillon de contrôle trop maigre"

    # (3) suffisance : toute la dalle de la coupe est couverte (le mur n'a pas de trou)
    assert not (in_slab & ~certified).any(), "trou dans le mur certifié — pas de déconnexion"
