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

---

## 2026-06-10 — S1 (Claude Code) — FK rationnelle 3D vert

**Fait** :
- G0' re-vérifié vert avant démarrage (43 tests, 64 s).
- Drake 1.46.0 installé (wheel macOS arm64, `pip install drake`), `pydrake`
  + `RationalForwardKinematics` importables sans friction.
- `src/cnp/ratfk.py` implémenté : pour chaque body, pose monde en fonctions
  **rationnelles de s = tan((q−q*)/2)**, numérateurs (rotation 3×3 + position 3)
  sur **dénominateur commun canonique D(s) = ∏(1+s_i²) > 0**, degré ≤2/var.
  - Container back-end-agnostique `BodyRatFK` (n, s_chain, D, pos_num, rot_num ;
    `point_numerator(p_B)` = position monde d'un point body-frame = combinaison
    linéaire des numérateurs sur D ; `vertex_numerators`, `eval_world_point`).
  - Back-end Drake `DrakeRatFK(plant, locked, q_star)` ; back-end repli sympy
    `SympyRatFK(joints, locked, q_star)` (chaîne révolute générique), **même
    interface**.
- `tests/test_ratfk.py` (8 tests) — critères de sortie S1 atteints :
  - **FK numérique vs tenseurs, 1000 configs iiwa aléatoires** (dans les limites
    usine ⊂ (−π,π)), 7 links × 3 points body-frame : **erreur max < 1e-9**
    (typiquement ~3e-15).
  - **joints verrouillés** : `locked={1,4}`, n=5, FK reproduite < 1e-9.
  - **degré ≤2/var** par tenseur ; chaîne croissante (link_k dépend de s_0..s_{k-1},
    EE de tous les 7).
  - **repli sympy** validé vs FK numérique homogène indépendante (1000 configs,
    chaîne spatiale 3-DOF aléatoire) + variante verrouillée + degré ≤2.
  - **parité Drake↔sympy** sur cinématique identique (plant Drake construit par
    programme, sans réseau) : tenseurs égaux à 1e-9.
- `make test` complet : **51 passed** (43 régression + 8 ratfk), 77 s, mêmes
  5 warnings Clarabel bénins.

**Décisions** :
- **Substitution rationnelle faite maison (Approche C), pas le dénominateur de
  Drake.** `ConvertMultilinearPolynomialToRationalFunction` rend des dénominateurs
  réduits **distincts par entrée** (4 différents sur une pose) → inutilisable comme
  dénominateur commun. On part du polynôme **multilinéaire** (indéterminées
  `cos_delta[i]`/`sin_delta[i]`) et on dégage soi-même le demi-angle sur le
  dénominateur commun canonique : cos→(1−s²), sin→2s, joint absent→(1+s²). C'est
  exactement la substitution que `verify.py` recalculera indépendamment en S4 → FK
  auditable, pas « de confiance » (règle 4).
- **Dénominateur commun par link** (∏ sur les joints débloqués de la chaîne du
  body) — SPEC §2 « dénominateur commun » s'entend par link. Le témoin (S2) utilise
  le D du link concerné.
- **Joints verrouillés** : substitués par leurs cos/sin numériques, **sans variable
  s ni facteur (1+s²)** ; les débloqués sont ré-indexés 0..n−1.
- **Sommets d'enveloppe convexe en paramètre** (`point_numerator`/`vertex_numerators`)
  plutôt qu'extraits de la géométrie ici : l'extraction depuis la scène est S6 et le
  témoin (S2) fournira les sommets. Le livrable S1 = les tenseurs FK rationnels.
- `sympy` ajouté aux deps de base (repli) ; **Makefile installe `.[drake,dev]`**
  dès maintenant (Drake nécessaire au cœur à partir de S1) ; `importorskip` garde
  la suite gracieuse si le wheel Drake échoue un jour.
- Réutilisation du seul noyau partagé `cnp.polylin` pour l'algèbre tensorielle
  (mono/tmul/teval/zeros).

**Pièges rencontrés** :
- **Matrice homogène et dénominateur** (bug sympy, attrapé par les tests) : le
  coin (3,3) de la transfo homogène de rotation doit valoir `den`, pas 1, sinon la
  colonne translation est silencieusement divisée par (1+s²). Construire `den·I`
  puis écraser le bloc rotation.
- **Ordre de composition** : X_parent_child = X_pj · Rot(axe,θ) (offset puis
  rotation), pas l'inverse.
- **Mosek tiré en transitif par le wheel Drake** (8 Mo) : jamais importé, règle 3
  respectée (aucun `import mosek` dans le cœur). À surveiller qu'aucun chemin Drake
  ne le réveille.
- **Dépendance réseau** : le modèle iiwa est téléchargé une fois par Drake
  (`package://drake_models`, cache local) ; les tests iiwa **skippent proprement**
  hors-ligne (fixture try/except), le repli sympy et la parité tournent sans réseau.
- Hypothèse de portée assumée : chaîne révolute série, base soudée ⟹ index de
  position = index de joint/delta (asserté via limites ⊂ (−π,π) et n=positions).

**Prochaine étape** : S2 — témoin 3D (`witness.py`) : LP témoin slab-aware générique
n-dim (corps convexe mobile vs polytope statique H-rep), degré de λ paramétrable,
back-end cvxpy d'abord. Entrée : `BodyRatFK.vertex_numerators` + D par link.
