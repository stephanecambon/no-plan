# JOURNAL.md — certified-noplan

Convention : une entrée par session Claude Code. Format : Fait / Décisions /
Pièges rencontrés / Prochaine étape. Ne jamais réécrire l'historique.

---

## 2026-06-10 — Session amont (claude.ai, pré-S0)

**Fait** : campagne expérimentale E1-E4 dans le bac à sable claude.ai (voir
docs/CAMPAGNE-E1-E4-RESULTATS.md). Témoin affine validé (n=3..6), back-end
Bernstein-LP validé (t* identique au SOS, scaling jusqu'à n=10 synthétique),
déconnexion multi-paires certifiée end-to-end en 2-DOF (46 feuilles, 3 paires en
relais), pipeline φ-appris certifié. Contrôles de soundness OK. SPEC.md et
CLAUDE.md rédigés.

**Décisions** : Bernstein-LP comme back-end unique du chemin critique (pas de
SDP/Mosek) ; vérificateur indépendant en arithmétique exacte obligatoire ;
obstacles statiques en v1 ; plan en 13 sessions S0-S13, portes G0'-G4'.

**Pièges (à ne pas repayer)** : signe de Putinar (g − μT, jamais g + μT) ;
coupes dyadiques vs frontières de dalle non dyadiques (⟹ certificat slab-aware
obligatoire) ; la grille d'échantillonnage ne fait pas foi (micro-canal raté par
41 points, attrapé par le certificateur) ; profondeur = coût, pas faisabilité.

**Prochaine étape** : S0 — environnement, squelette, portage régression
(critères de sortie dans CLAUDE.md).

---

## 2026-06-10 — S0 (Claude Code) — **G0' vert**

**Fait** :
- venv Python 3.12 Homebrew (`.venv`) + `pyproject.toml` (deps SPEC §3) ;
  `make setup` idempotent (deuxième appel = no-op), `make test`, `make clean`.
- Arborescence `src/cnp/` complète (SPEC §3) : `polylin.py` porté du bac à sable
  (numérique inchangé) ; `ratfk/witness/engine/phifit/certificate/verify/scenes/viz`
  en stubs datés par session.
- Suite régression pytest : **43 tests, `make test` vert en 63 s**.
  - `test_polylin.py` : les self-tests du `__main__` de polylin convertis.
  - `test_exp12_ladder.py` : E1/E2 rejoués depuis `sandbox_reference/exp12_results.json`
    (16 lignes bern-LP reproduites à **1e-6** — souvent <1e-9 ; 14 lignes SOS-SDP à
    1e-5 ; accord LP=SOS vérifié). t* identiques : const −0.090, affine/multilin
    +0.220, contrôle négatif −0.190.
  - `test_exp34_multipair.py` : E3 **certified=True, 46 feuilles** (38 collision —
    UP 12 / DOWN 12 / MID 14 ; 8 outside ; 0 fail) ; contrôle négatif (obstacles
    rétrécis 30 %) **refusé** (soundness) ; E4 (φ appris) **78 feuilles, 76 collision**.
  - `test_putinar_sign.py` : **fige le signe g − μT**. Instance trouvée (pair UP
    rétréci, cell s1∈[−0.125,0], s2∈[0.875,1]) où la prémisse est réellement fausse
    (configs libres présentes) : le bon signe refuse (t*=−0.039), `g + μT` certifie
    **faussement** (t*=+0.029). Flipper le défaut casse le test.
  - Scènes planaires E3/E4 = fixtures réutilisables (`conftest.py`).

**Décisions** :
- Le code de régression du bac à sable vit sous `tests/regref.py`, **pas** dans
  `src/cnp` (witness/engine sont S2/S3) ; seul noyau partagé : `cnp.polylin`.
- SOS-SDP conservé pour le cross-check E2 mais isolé dans `regref` (jamais importé
  par le cœur — règle 3) ; tol SOS 1e-5 (point intérieur), tol LP 1e-6.
- `certify_cell_pair(..., putinar_sign=-1)` : le paramètre n'existe **que** pour le
  test de signe ; le défaut est le signe sound (soustraction).
- **Drake non installé en S0** : déplacé dans l'extra `[drake]` du pyproject ; non
  nécessaire pour la régression planaire, wheel macOS arm64 traitée en S1.

**Pièges rencontrés** :
- Le dépôt git est la racine `no-plan/` ; le projet est dans `certified-noplan/`.
  Tout le squelette est sous ce sous-dossier.
- `exp12_ladder.py` écrit `exp12_results.json` dans le cwd : le rejouer pour vérifier
  pouvait écraser un fichier ; la référence `sandbox_reference/` n'a jamais été
  touchée et le test rejoue en mémoire sans rien écrire.
- 5 avertissements Clarabel « Solution may be inaccurate » (cas multilinéaires /
  négatifs) : bénins, t* reproduit dans la tolérance. **Non supprimés** par choix
  d'honnêteté — les masquer cacherait une dégradation future. À surveiller en S8.

**Prochaine étape** : S1 — FK rationnelle 3D (`ratfk.py`) ; installer l'extra
`[drake]` (`pip install -e ".[drake,dev]"`) ou activer le repli sympy si friction.
