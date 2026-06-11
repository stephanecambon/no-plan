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

---

## 2026-06-10 — S2 (Claude Code) — Témoin 3D vert

**Fait** :
- S1 re-vérifié vert avant démarrage (51 tests, 77 s).
- `src/cnp/witness.py` implémenté : LP témoin slab-aware **générique n-dim**, corps
  convexe mobile (sommets = numérateurs FK sur dénominateur commun, via `ratfk`) vs
  polytope statique en **H-rep** (`Polytope`, fabrique `box`).
  - Témoin x(s) = Σ_k λ_k(s)·v_k(s), Σλ_k≡1, λ_k≥0 (Bernstein) ; face j de O :
    g_j = b_j·D − a_jᵀX ≥ 0 ; slab `T = δ²−φ²` ; contrainte **Bernstein(g_j − μ_j·T) ≥ t**,
    μ_j ≥ 0 ; maximise t. Tout linéaire en (coeffs λ, μ, t) → **LP** (aucun SDP/Mosek).
  - **Degré de λ paramétrable** : `const`/`affine`/`quadratic` (base à degré total
    borné ; défaut affine).
  - **Interface back-end isolée** : `build_witness_lp` rend un `WitnessLP`
    solveur-agnostique (numpy pur) ; `LPBackend`/`CvxpyBackend` (CLARABEL) le
    consomment. S8 branchera highspy sur le **même** `WitnessLP`.
  - `eval_witness_point` : reconstruit x(s) batch (numpy vectorisé) depuis la solution,
    pour le contrôle vérité-terrain échantillonnée.
- `tests/test_witness.py` (14 tests) — critères de sortie S2 atteints :
  - **Exit #1** — **S1-planaire embarquée en 3D reproduit le certificat E3** : b&b
    (même flot que l'oracle `regref.certify_slab`, seul le certifieur change) →
    **46 feuilles, 38 collision (UP 12 / DOWN 12 / MID 14), 8 outside, 0 fail**,
    identique à E3. Parité t* par cellule **< 1e-7** vs oracle 2D (cas `unbounded`
    inclus). Les 2 faces z extrudées sont esclaves (z=0), la marge vient des faces x/y.
  - **Exit #2** — **3-DOF spatial minimal** (chaîne révolute générique 3R, back-end
    **sympy**, sans réseau) : lien dans une boîte obstacle → **certifié (t=0.079)** ;
    sur **1e5 échantillons** de la cellule, le point témoin est **toujours dans
    l'obstacle (0 violation)** ⟹ aucun point libre.
  - **Gel du signe de Putinar** (rule 2) sur le nouveau témoin : sur prémisse
    réellement fausse (UP rétréci, cellule s1∈[−0.125,0]×s2∈[0.875,1], 4 configs
    libres), `g − μT` refuse (t=−0.039), `g + μT` certifie **faussement** (t=+0.029).
  - **Contrôles négatifs (soundness)** : E3 obstacles rétrécis 30 % → b&b **refuse**
    (feuilles FAIL) ; 3-DOF obstacle rétréci ×0.5 → témoin **refuse** (t=−0.015) ET
    188 configs libres trouvées (prémisse fausse confirmée).
  - **Isolation back-end** prouvée : un second solveur indépendant (`scipy.linprog`,
    HiGHS) sur le **même** `WitnessLP` donne le même t* (< 1e-6).
  - λ quadratique certifie aussi ; `Polytope.box` et bases de degré testées.
- `make test` complet : **65 passed** (43 régression + 8 ratfk + 14 témoin), 100 s,
  mêmes 5 warnings Clarabel bénins.

**Décisions** :
- **K sommets explicites avec Σλ_k≡1, λ_k≥0** (au lieu du `0≤λ≤1` scalaire de l'oracle
  E3) : la version K=2 redonne exactement le segment x=p1+λ(p2−p1) → parité E3 exacte ;
  généralise au corps convexe quelconque (enveloppe à K sommets).
- **D^p = D (p=1)** : sommets sur dénominateur commun unique D du link ; g_j = b_j·D − a_jᵀX
  avec X = Σλ_k N_k numérateur sur D. Pas besoin de l'exposant p>1 du SPEC ici.
- **Σλ=1 en coefficients bruts** (identité polynomiale), λ≥0 et faces en **Bernstein**
  sur la cellule — même base que l'oracle, t* reproduit à 1e-7.
- **`_putinar_sign` test-only** (défaut −1 sound), à l'identique de l'oracle `regref` :
  le signe est figé par `test_witness_sign_is_frozen` ; production ne le touche jamais.
- **Embarquement 3D de S1** = sommets planaires à z=0 + boîtes extrudées z∈[−1,1] :
  les faces z restent esclaves (marge ≫ t*), donc certificat **identique** à E3.
- **Back-end b&b reste dans le test**, pas dans `engine.py` : le moteur n-dim est S3 ;
  le scaffold b&b du test reprend volontairement le flot de l'oracle pour isoler le
  témoin comme seule variable.
- **3-DOF spatial via sympy** (pas Drake) : pas de dépendance réseau dans la suite,
  vérité-terrain reproductible et seedée.

**Pièges rencontrés** :
- **Matrice homogène / `PolyLin.__add__`** : addition de PolyLin de degrés différents
  OK (slicing dans `zeros(n,d)`), mais bien **padder D et φ²** au degré de travail
  `DPAD = max(d_λ+d_N, 2·d_φ)` (=4 ici, comme E3) avant Bernstein — sinon recouvrement
  de tenseurs incohérent.
- **Faces esclaves** : les 2 faces z (z=0, D>0 ⟹ b·D≥1≫t*) ne lient jamais ; c'est ce
  qui garantit la parité E3 quand on embarque le planaire en 3D. Vérifié numériquement.
- **Contrôle négatif 3-DOF** : un rétrécissement ×0.5 de la boîte (autour du centre)
  ouvre 188 configs **entièrement** libres (segment hors boîte) sur grille 9³ — assez
  pour le contrôle ; testé f∈[0.3,0.6], tous donnent prémisse fausse + refus.

**Prochaine étape** : S3 — moteur branch-and-bound n-dim (`engine.py`) : généraliser
le moteur E3 à n dims, heuristique d'axe (frontière de dalle puis pire marge LP),
checkpoint/resume disque, parallélisme multiprocessing sur les feuilles, budget +
verdict UNDECIDED propre. Entrée : `cnp.witness.certify_cell_pair`. Le scaffold b&b
de `test_witness.py` documente le flot de référence (axe + test outside) à généraliser.

---

## 2026-06-10 — Revue de supervision S0-S2 (claude.ai) — **plan révisé v1.1**

**Verdict** : les trois sessions sont validées. Qualité au-dessus de l'attendu sur
quatre points : (1) test_putinar_sign démontre le faux certificat du mauvais signe
sur une instance à prémisse *réellement* fausse — c'est un test de soundness en
acte, pas un test de non-régression ; (2) la parité E3 est à valeurs égales
(t* < 1e-7 par cellule), pas seulement à verdict égal ; (3) l'isolation back-end
de S2 (WitnessLP + cross-check scipy/HiGHS < 1e-6) dérisque par anticipation la
partie conception de S8 ; (4) le choix S1 de la substitution demi-angle « maison »
(approche C) plutôt que le dénominateur Drake est exactement le bon arbitrage pour
l'auditabilité de verify.py — les dénominateurs réduits distincts de Drake auraient
rendu la vérification indépendante pénible.

**Points relevés (annotations, actions injectées dans le plan v1.1)** :
- [A1 → S4] **q_star** : l'implémentation est s = tan((q − q*)/2), la SPEC dit
  tan(θ/2). Divergence légitime (et plus générale) mais elle touche l'énoncé du
  théorème (wrap-around : |q_i − q*_i| < π), le schéma de certificat et verify.py.
  SPEC §2/§4 à amender en S4 ; q_star et les valeurs exactes des joints verrouillés
  entrent dans le certificat. Nouvelle règle 12 (anti-dérive de spec) pour que ce
  cas reste l'exception traitée, pas le précédent silencieux.
- [A2 → S3] **Garde Mosek automatisée** : le wheel Drake l'embarque en transitif ;
  « aucun import dans le cœur » doit être un test (sys.modules après import cnp +
  un solve), pas une vigilance humaine.
- [A3 → S3] **Temps de suite** : 63 → 77 → 100 s en trois sessions. `make test-fast`
  (< 30 s) pour le quotidien, `make test` complet requis aux sorties de session.
- [A4 → règle 13] **Skips réseau** : légitimes au quotidien, interdits sur les tests
  requis aux sorties de session (décompte exact passed/skipped/warnings au journal).
  Pré-télécharger les modèles Drake avant S9-S10.
- [A5 → S8] Les 5 warnings Clarabel « non supprimés par honnêteté » : bon réflexe ;
  l'élucidation (résoudre ou expliquer structurellement) devient une tâche S8.
- [A6, sans action] L'embarquement 3D de l'exit #1 (faces z esclaves) est un test de
  parité, pas un test de 3D-ité — c'est l'exit #2 (3-DOF spatial, 1e5 échantillons,
  0 violation du témoin) qui porte la validation spatiale. Couverture jugée
  suffisante pour S2.
- [A7, demande produit] **Validation visuelle humaine** : à la demande de Stéphane,
  protocole formalisé (règle 11, points [V1]-[V7] dans le plan) — la session
  s'arrête, donne la commande exacte, la checklist de ce qu'il faut regarder et le
  critère binaire, puis attend « VALIDÉ S<X>-V<k> ». Portée explicite : intention
  et conception seulement ; jamais la soundness (l'œil rate les micro-canaux,
  leçon E3). `cnp show` avancé de S11 à S6 pour servir ces validations.

**Prochaine étape** : S3 — moteur b&b n-dim, selon CLAUDE.md v1.1 (tâches 1-6,
validation V1 incluse).

---

## 2026-06-11 — S3 (Claude Code) — Moteur b&b n-dim (**code vert, V1 en attente**)

**Fait** :
- S2 re-vérifié vert avant démarrage (65 passed, 100 s).
- `src/cnp/engine.py` : branch-and-bound **n-dim** générique. `Problem` (box, phi,
  delta, `Pair`s, lam_degree, tol, max_depth), `Budget`, `EngineResult`
  (verdict PROOF/UNDECIDED, leaves, failed exportées, stats). Test outside par
  Bernstein de φ (`cell_outside_slab`, ré-exprimé via `cnp.polylin`, identique à
  l'oracle). Verdict **UNDECIDED** propre (jamais « infaisable ») sur budget
  (temps/feuilles) ou profondeur épuisée, cellules ouvertes exportées.
- **Heuristiques d'axe** : dalle-d'abord (split qui pousse un enfant hors dalle),
  puis fallback `axis="oracle"` (axe le plus large = choix de l'oracle ⇒ partition
  E3/E4 identique) ou `axis="margin"` (pire marge LP).
- **Parallélisme = work-queue dynamique** (défaut `n_workers>1`) : les workers
  partagent une file ; quand une cellule se découpe, ses **deux enfants repartent
  dans la file**, donc même un sous-arbre lourd s'étale sur tous les cœurs. L'arbre
  exploré est l'arbre déterministe du serial ⇒ **certificat octet-identique au
  serial, zéro inflation** (`test_workqueue_matches_serial`).
- **Checkpoint/resume** : chemin *frontier* (pré-découpe uniforme déterministe en
  2^d sous-cellules, chaque sous-arbre écrit atomiquement `done/<i>.json` via
  tmp+`os.replace`+fsync). `meta.json` à empreinte SHA : reprise refusée si le
  problème diffère (soundness). `test_resume_after_kill_same_certificate` lance un
  fils, le **SIGKILL en cours de run**, reprend, et obtient le même certificat.
- **Backend HiGHS par défaut** (`witness.HighsBackend`, scipy.linprog) : reproduit
  E3=46/E4=78 **exactement** (t* = CLARABEL < 1e-6, aucun flip à tol=1e-6), plus
  rapide (pas de compile cvxpy), et **mosek-free** (voir piège). cvxpy reste dispo
  en `backend=` pour cross-check.
- **Garde Mosek** (`tests/test_mosek_guard.py`, 3 tests, en **sous-process frais**) :
  import du cœur sans mosek/cvxpy ; solve par défaut (HiGHS) sans mosek ; + 1 test
  qui **documente** que le backend cvxpy, lui, réveille mosek.
- **Figures** : `scripts/make_figures.py` + `make figures` → `benchmarks/figures/
  partition_{E3,E4}.png` (panneau vérité-terrain + partition certifiée colorée par
  paire). Adaptateur de scènes DRY `tests/eng_scenes.py` (l'oracle `regref` reste
  intact).
- **Makefile** : `make test-fast` (`-m "not slow"`, **33 passed en 4.95 s**),
  `make test-slow`, `make figures`. Marqueurs `slow` posés sur les rejouages lourds
  (exp12 SOS 28 s, exp34 34 s, ratfk iiwa ~14 s, contrôle négatif témoin 37 s).
- `make test` complet : **82 passed, 0 skipped, 25 warnings, 130 s**
  (65 régression + 14 engine + 3 garde Mosek).

**Décisions** :
- **Work-queue plutôt que frontier statique pour le parallélisme.** Une pré-découpe
  statique de la dalle (fine) ne donne qu'une poignée de cellules *lourdes* → un
  worker hérite d'un gros sous-arbre, speedup plafonné ~2×. Mesuré honnêtement :
  round-robin ~1.4-1.9×, découpe tangente-à-la-dalle 0.16× (re-isole la dalle dans
  chaque colonne → explosion à 154 feuilles), gradient-d'abord 1.1× (explosion à
  1042 feuilles). Le work-queue **3.56× (dup=20) / 3.68× (dup=30)** sur 8 workers,
  10 cœurs, sans inflation. Le chemin frontier est **conservé** mais réservé au
  checkpoint/resume (déterministe, reprenable).
- **`start_method="fork"` pour le work-queue.** Sûr ici car **le parent ne résout
  aucun LP** (les workers possèdent tout le calcul cvxpy/BLAS) ⇒ aucun thread de lib
  vivant au fork ; et fork évite le ré-import cvxpy par worker qui écrase « spawn »
  à ~1.4-1.7×. Surchargeable (`start_method="spawn"`).
- **HiGHS = défaut du moteur** (pas cvxpy). Triple gain : mosek-free (règle 3),
  rapide, workers fork instantanés. L'isolation back-end de S2 (WitnessLP
  solveur-agnostique) rend ça gratuit ; c'est aussi la direction S8 (highspy direct),
  avancée ici par nécessité règle 3. cvxpy/CLARABEL reste le solveur de l'oracle
  `regref` (la reproduction 46/78 est vérifiée contre lui).
- **`axis="oracle"` reste le défaut** (reproduction exacte = critère de sortie). La
  margin est l'enhancement S3, journalisée comme « écart » (voir ci-dessous).

**Pièges rencontrés** :
- **cvxpy réveille mosek à l'import.** `import cvxpy` énumère tous les solveurs
  installés, dont le mosek transitif du wheel Drake — alors qu'on ne résout qu'en
  CLARABEL. Donc la garantie règle 3 (« aucun Mosek dans le chemin critique »)
  **impose d'éviter cvxpy** sur le chemin critique : d'où HiGHS par défaut. Le cœur
  (`import cnp.engine/witness`) n'importe PAS cvxpy (lazy dans le backend) ⇒ import
  cœur mosek-free. Garde automatisée à 3 volets, en sous-process frais (la pollution
  inter-tests masquait la régression sinon).
- **Heuristique margin = piège de coût, pas de soundness.** Premières variantes
  désastreuses : worst-margin par point de contrôle Bernstein et minimax 1-pas →
  **E4 UNDECIDED (263 FAIL), boucle ~10 min**. La bonne formulation est le lookahead
  **relais** (max de la marge du meilleur enfant : carve une cellule certifiable,
  récurse le reste) → certifie E3 (54 feuilles) **et** E4 (56 feuilles, < oracle 78).
  Écart journalisé : margin ≠ oracle en nombre de feuilles, jamais en soundness
  (rule 9). `axis="oracle"` reproduit 46/78 à l'identique.
- **`multiprocessing` exige un guard `__main__`.** Mes scripts de mesure appelaient
  `solve(n_workers>1)` au niveau module sans guard → sous spawn chaque worker
  re-exécute le script → explosion récursive de process / deadlock (10 min muets).
  Bug de script, pas du moteur (cibles du pool au niveau module = picklables).
- **`fork()` multi-threaded** : 20 `DeprecationWarning` macOS « use of fork() may
  lead to deadlocks ». Non observé (suite complète verte, work-queue déterministe,
  resume OK) ; **non supprimé** par honnêteté (comme les 5 Clarabel). Mitigation
  dispo : `start_method="spawn"` (sûr, ~1.5×). À reconsidérer en S8 (highspy direct
  ⇒ workers mono-thread, fork sûr).
- **Mesures de speedup faussées par la charge** : machine de bureau partagée
  (windowserver, VM, 9 users) + mes process résiduels → une mesure serial à 982 s
  (contention). Toujours mesurer process unique, foreground. Test durci (meilleur
  de 2 runs parallèles) contre les à-coups du scheduler.

**Décompte exact (sortie de session)** : `make test` = **82 passed, 0 skipped,
25 warnings, 130 s** (20 fork-deprecation + 5 Clarabel, tous documentés).
`make test-fast` = 33 passed, 49 deselected, 4.95 s.

**Critères de sortie S3** : E3/E4 via le moteur = oracle (46/78, mode oracle) ✓ ;
resume kill-9 même certificat ✓ ; speedup 8 cœurs **3.56×** ✓ ; garde Mosek verte ✓ ;
décompte exact journalisé ✓ ; **V1 VALIDÉE par Stéphane (« VALIDÉ S3-V1 »)** ✓.
**S3 vert, tous critères acquis.**

- [A11 → S11] **Annotation produit (Stéphane, à la validation V1)** : sur le panneau
  partition (b), **rogner/hachurer les feuilles slab-aware hors-dalle** (une feuille
  certifiée n'est en collision que sur sa portion ∩ dalle, pas sur toute la cellule)
  et **tracer la frontière de dalle** {|φ|=δ}. À faire dans `viz.py`/`make_figures`
  en S11 (figures prêt-papier, [V7]). Ne change rien à la soundness — lisibilité.

**Prochaine étape** : S4 — certificat JSON + verify.py exact (amender SPEC §2/§4 :
q_star, D par link, p=1 ; substitution demi-angle maison ré-implémentée). NB pour S4 :
le moteur émet déjà `partition_records()` (cell/status/pair/margin) — base du champ
`leaves` du certificat. NB pour S8 : HiGHS est déjà le défaut du moteur (avance la
tâche back-end direct ; reste highspy sans scipy + warnings Clarabel à élucider).

## 2026-06-11 — Revue de supervision S3 (claude.ai) — **CLAUDE.md v1.2**

**Verdict** : S3 validée sur le fond ; V1 en attente côté Stéphane (figures
prêtes). Trois points au-dessus de l'attendu : (1) work-queue parallèle à
certificat octet-identique au serial, avec mesure honnête des alternatives
écartées (round-robin 1.4-1.9×, tangente 0.16× + explosion, gradient 1.1×) —
3.56×/8 workers sans inflation ; (2) découverte que `import cvxpy` réveille le
mosek transitif du wheel Drake ⟹ HiGHS par défaut, garde 3 volets en
sous-process frais (la pollution inter-tests masquait la régression) ;
(3) resume à empreinte SHA qui refuse la reprise si le problème diffère.

**Annotations (intégrées à CLAUDE.md v1.2)** :
- [A8 → règle 11] La validation visuelle ne bloque jamais le commit du code :
  commit immédiat « S<X> — V<k> pending », validation = micro-commit de
  clôture. Une V en attente bloque la session suivante, pas la sauvegarde.
- [A9 → S8] Re-scope : défaut HiGHS déjà acté (S3, scipy.linprog) ; S8 =
  highspy direct + warm starts, sparsité, dims passives, degré adaptatif,
  fork/spawn à ré-évaluer workers mono-thread, solder 20 warnings fork +
  5 Clarabel.
- [A10 → S9] Heuristique d'axe à trancher sur données : margin-relais bat
  l'oracle sur E4 (56 vs 78 feuilles), perd sur E3 (54 vs 46) — levier
  anti-explosion n°1 pour G2'. Micro-tâche ajoutée : mesurer feuilles(n) à
  n = 3,4,5,6 joints sur la même scène (exposant empirique du modèle de coût).

**V1 — instructions transmises à Stéphane** : `make figures`, ouvrir
`benchmarks/figures/partition_E3.png` et `partition_E4.png` ; vérifier
(1) bande dalle continue ★→✚ sans cellule FAIL noire, (2) relais des trois
couleurs de paires cohérent avec la vérité-terrain, (3) raffinement concentré
aux frontières de dalle et zones de relais. Répondre « VALIDÉ S3-V1 » à Code,
qui committe (rule 11 amendée) et ouvre S4.

**Prochaine étape** : V1, micro-commit, puis S4 — certificat JSON + verify.py
exact (le schéma §4 est pré-amendé dans SPEC v1.1, S4 le finalise).

---

## 2026-06-11 — S4 (Claude Code) — Certificat exact + vérificateur indépendant

**Fait** :
- S3 re-vérifié vert avant démarrage (82 passed, 0 skip, 130 s).
- `src/cnp/certificate.py` (GÉNÉRATEUR) : modèle `Scene` exact-rationnel (robot
  révolute, obstacles H-rep, φ, δ, boîte P, start/goal en espace-s), `scene_to_problem`
  (construit le `engine.Problem` flottant via `cnp.ratfk.SympyRatFK`), `make_certificate`
  (sérialise un JSON 100 % rationnels exacts), `certify`, `save/load`. Schéma SPEC §4
  finalisé.
- `src/cnp/verify.py` (VÉRIFICATEUR, **SACRÉ**) : **498 lignes**, `fractions.Fraction`
  uniquement, **zéro import** du générateur (audit AST en test). Ré-implémente
  *from scratch* : algèbre tensorielle creuse + transformée de Bernstein exacte ; FK
  demi-angle révolute indépendante (accumulation de transfos homogènes 4×4 en
  tenseurs Fraction) ; les 5 contrôles SPEC §2 — (0) hypothèses, (i) φ(s_start)<−δ ∧
  φ(s_goal)>+δ STRICT, (ii) pavage exact de P (cover disjoint re-dérivé par récursion
  sur les bissections au milieu — l'arbre n'est pas stocké), (iii) feuilles outside
  (Bernstein φ±δ ≥ 0), (iv) feuilles collision (Σλ_k ≡ 1 exact, Bernstein(λ_k) ≥ 0,
  μ_j ≥ 0, Bernstein(g_j − μ_j·T) ≥ 0). **Le vérificateur FORME lui-même g − μT** ⟹ un
  certificat ne peut pas y glisser le signe unsound g + μT (règle 2).
- `src/cnp/cli.py` + `__main__.py` + `[project.scripts] cnp = cnp.cli:main` :
  `cnp verify cert.json` (et `python -m cnp verify`) → PROOF (exit 0) / UNDECIDED
  (exit 1), verdict honnête (règles 5/6). `scene` en argument optionnel (S6).
- `tests/cert_scenes.py` : builders `Scene` E3/E4 (pendant S4 de `eng_scenes.py`).
- `tests/test_certificate.py` (7 tests) : round-trip E3 (**46 feuilles** 38c/8o,
  test-fast ~0.7 s) et E4 (**78 feuilles** 76c, @slow) reproduisant l'oracle, tous deux
  vérifiés exactement ; certificat 100 % rationnels (pas de float qui fuit) ; save/load ;
  refus d'un résultat UNDECIDED ; **audit verify** : < 500 lignes + imports stdlib only.
- `tests/test_verify.py` (28 tests) : **26 mutations adversariales** (μ<0, μ énorme, Σλ≠1,
  λ mis à l'échelle/négatif, coupe décalée, feuille manquante=trou, feuille dupliquée=
  recouvrement, q*≠0, δ×20, δ<0, start/goal du mauvais côté, signe φ, b/A d'obstacle,
  sommet de coque, longueur de link, body_link, collision↔outside relabellisées,
  obstacle permuté, theorem/substitution corrompus, boîte rétrécie, cellule hors-boîte)
  **toutes rejetées** ; le vérificateur ne lève jamais sur entrée corrompue (renvoie
  `(False, raison)`).
- `make test` complet : **117 passed, 0 skipped, 25 warnings, 135 s** (82 + 35 S4).
  `make test-fast` = **67 passed, 50 deselected, 7.77 s**. Garde Mosek verte (3/3).

**Décisions** :
- **FK générateur via `SympyRatFK`, FK vérificateur ré-implémentée en Fraction.**
  Vérifié : le bras planaire 2R exprimé en chaîne révolute z-axe reproduit EXACTEMENT
  (diff 0.0) les tenseurs `regref.fk_tensors()`, donc le moteur via le modèle `Scene`
  redonne 46/78. La duplication générateur↔vérificateur est le but (SPEC §5), pas un
  défaut : deux chemins de code indépendants qui doivent CONCORDER.
- **Pavage prouvé sans stocker l'arbre.** Le moteur n'émet qu'une liste plate de
  feuilles ; plutôt que modifier `engine.py` (⟹ re-run adversarial, règle 1), verify
  RECONSTRUIT le pavage par récursion sur les bissections au milieu (le moteur ne coupe
  qu'au milieu ⟹ exact). Prouve trou ET recouvrement (mutations dédiées le confirment).
- **Arrondi des multiplicateurs = mélange-au-barycentre + `limit_denominator`.** Le
  min des points de contrôle Bernstein de λ est un **zéro STRUCTUREL** (le témoin est
  sur un sommet du corps) ; l'arrondi indépendant des coeffs le rendait légèrement
  négatif. Fix : λ ← (1−α)λ + α·barycentre (le barycentre somme à 1 ⟹ Σλ≡1 préservé ;
  les zéros remontent à α/K>0), α ≪ marge de face (0.0063 sur E3) ⟹ faces restent > 0.
  Dernier sommet DÉRIVÉ par soustraction ⟹ Σλ≡1 exact par construction. max_den=1e6 :
  la poussière numérique (~1e-13) tombe sur 0, les marges (~1e-2) survivent.
- **Condition (i) en espace-s.** tan(θ/2) des angles de démo est irrationnel ⟹
  invérifiable en exact. On certifie entre deux configs RÉELLES d'images s_start,
  s_goal RATIONNELLES (q = q*+2·arctan(s)), test STRICT. Restriction de portée
  honnête (règle 6), SPEC §2 amendée.
- **Certificat auto-suffisant en S4** : il embarque la scène exacte (robot+obstacles)
  que verify recalcule ; le croisement avec un YAML externe est S6. Faire confiance à
  l'ÉNONCÉ du problème (géométrie, q*) ≠ faire confiance à la PREUVE (numérateurs, λ,
  μ, partition) — seule la preuve est recalculée/contrôlée.
- **`cnp verify` n'utilise pas cvxpy** (verify = stdlib pur) ; `make_certificate`
  re-résout via le backend HiGHS du moteur (mosek-free). La garde Mosek reste verte.

**Pièges rencontrés** :
- **q* est absorbé dans s pour les joints débloqués.** Changer q* dans le cert ne
  changeait RIEN au verdict (les numérateurs FK en s n'en dépendent pas). Ré-injecter
  q*≠0 exige Rot(q*_i) ⟹ cos/sin(q*_i) rationnels (irrationnels en général). Choix
  honnête : le vérificateur exact planaire n'admet que **q*=0** et REFUSE q*≠0 (règle 5 :
  ne jamais « vérifier » ce qu'on ne peut pas recalculer). C'est ce refus qui rend la
  mutation q* rejetable. q*≠0 viendra avec Drake (S9+, cos/sin verrouillés rationnels).
  NB : `SympyRatFK` ignore aussi le q* des joints débloqués — latent, sans effet à
  q*=0 (S4), à traiter pour le chemin sympy si q*≠0 un jour ; Drake le gère déjà.
- **`link_lengths[1]` n'entre PAS dans la FK de `body_link=1`** : seule
  `link_lengths[0]` (offset du joint 1) compte ; la longueur du link distal est portée
  par `hull_vertices`. Première mutation « link_length » (indice 1) passait à tort ;
  corrigée à l'indice 0.
- **Bernstein au MÊME degré que le générateur** (DPAD = max(d_λ+2, 2·d_φ) = 4 en
  affine) : un degré plus bas donnerait une borne plus lâche ⟹ FAUX rejet d'un cert
  valide (la soundness, elle, tiendrait). verify calcule au degré du générateur ⟹
  décision d'acceptation identique.
- **Audit d'imports par regex piégeux** : `^\s*from` matchait « from scratch » en
  prose. Remplacé par un parcours **AST** (Import/ImportFrom) — robuste.
- **verify.py a frôlé 500 lignes** (516 → 498) : suppression des helpers Bernstein
  min/max inutilisés et condensation des commentaires. La limite « < 500 » (règle 4)
  est testée (`test_verify_under_500_lines`).

**Décompte exact (sortie de session)** : `make test` = **117 passed, 0 skipped,
25 warnings, 135 s** (mêmes 20 fork-deprecation + 5 Clarabel, documentés S0/S3).
`make test-fast` = 67 passed, 50 deselected, 7.77 s.

**Critères de sortie S4** : round-trip generate→verify OK sur E3 et E4 ✓ ;
≥ 20 certificats corrompus rejetés (**26**) ✓ ; audit imports de verify (stdlib only,
< 500 lignes) ✓ ; SPEC §2/§4/§5 amendée (règle 12) ✓ ; décompte exact journalisé ✓.
Pas de point [V*] en S4 (la prochaine validation visuelle est V2 en S5). **S4 vert.**

**Prochaine étape** : S5 — pipeline φ (`phifit.py`) : échantillonnage C_free/C_obs
(collision checker Drake, seedé), fit SVM + approx polynomiale deg ≤2/var, sélection δ
auto, boucle de retry. **[V2]** : figure « C-space + lignes de niveau φ + dalle » pour
E4-planaire puis 3-DOF. NB S5 : `certificate.Scene` + `verify` attendent un φ rationnel
et des obstacles H-rep exacts ; phifit devra rationaliser son φ appris (cf. `e4_scene`
qui rationalise à 1e-6). NB S6 : brancher `cnp verify cert scene.yaml` (croisement scène
externe), et `cnp certify`.

## 2026-06-11 — Revue de supervision S4 (claude.ai) — **CLAUDE.md v1.3**

**Verdict** : S4 validée — la session la plus structurante du projet. Trois
points au-dessus de l'attendu : (1) le vérificateur **forme lui-même g − μT**
(le certificat ne transporte que λ et μ) ⟹ le signe unsound devient
structurellement impossible à glisser dans une preuve, plus seulement testé ;
(2) pavage prouvé par RECONSTRUCTION (récursion sur bissections au milieu)
plutôt qu'en modifiant engine.py — règle 1 respectée, trou ET recouvrement
prouvés ; (3) refus honnête de q*≠0 par le vérificateur planaire plutôt qu'une
fausse vérification (règle 5), et condition (i) restreinte aux s rationnels
(SPEC amendée). 26 mutations rejetées, audit AST, 498 lignes, 117 tests 0 skip.

**Annotations (intégrées à CLAUDE.md v1.3)** :
- [A12 → ouverture S5] `SympyRatFK` IGNORE silencieusement q* des joints
  débloqués (« sans effet à q*=0 » — vrai aujourd'hui, mine pour S9). Garde
  bruyante exigée : ValueError si q*≠0 sur le chemin sympy, + 1 test.
- [A13 → ouverture S5] L'arrondi mélange-au-barycentre est calibré en dur sur
  la marge d'E3 (α=0.0063 vs marge ~1e-2). À 7-DOF les marges visent ~1e-3 :
  α doit être adaptatif (fraction de la marge mesurée par feuille) + boucle de
  re-résolution si verify rejette après arrondi (promesse SPEC §4) + test à
  marge fine.
- [A14 → règle 9, contrat] La reconstruction du pavage par verify suppose que
  le moteur ne coupe QU'AU MILIEU. Désormais contrat explicite engine↔verify :
  changer l'un = amender l'autre + SPEC dans le même commit. Corollaire
  documenté : verify calcule Bernstein au même degré que le générateur (plus
  bas = faux rejets).
- [A11 → S11, issu de V1] Figures de publication : rogner/hachurer la partie
  hors-dalle des feuilles slab-aware et tracer la frontière de dalle sur le
  panneau partition (les grandes feuilles E4 débordant en zone libre sont
  sound — la couleur ne vaut que sur cellule∩dalle — mais piégeuses pour un
  lecteur).

**V1 (clôturée)** : figures partition_E3/E4 validées par Stéphane sur les trois
points de la checklist (continuité de dalle sans FAIL, relais des paires
conforme à la vérité-terrain, raffinement concentré aux frontières/relais).

**Prochaine étape** : S5 — tâches d'ouverture A12+A13 (< 30 min), puis pipeline
φ (échantillonnage seedé, fit SVM, approximation polynomiale RATIONALISÉE,
δ auto avec s_start/s_goal rationnels, boucle de retry). V2 en fin de session.

---

## 2026-06-11 — S5 (Claude Code) — Pipeline φ (**code vert, V2 en attente**)

**Fait** :
- S4 re-vérifié vert avant démarrage (117 passed, 0 skip, 135 s) ; au passage,
  réconciliation des docs de la revue S4 (CLAUDE.md v1.3 incohérent : le bloc
  A14/contrat était ajouté mais l'« État d'avancement » avait été reverté en
  pré-S4 ; header v1.2→v1.3 ; commit doc séparé avant S5).
- **Gardes d'ouverture** :
  - **A12** — `SympyRatFK` lève désormais `ValueError` si q*≠0 sur un joint
    **débloqué** (il ne pose pas la pré-rotation Rot(axe, q*) ⟹ q* serait ignoré
    en silence, FK fausse). Joints **verrouillés** : q* replié dans cos/sin
    numériques, q*≠0 toléré (testé). Drake gère q*≠0 nativement (inchangé).
  - **A13** — l'arrondi λ mélange-au-barycentre devient **adaptatif** : α =
    fraction de la marge de face MESURÉE par feuille (`(0.2,0.05,0.01,0.002)·marge`
    au lieu de constantes calibrées sur E3). `make_certificate` exécute le
    **vérificateur exact** et **escalade max_den** jusqu'à acceptation (promesse
    SPEC §4 « re-résolution »), sinon lève honnêtement. Test à marge fine
    (δ=3/40 ⟹ min marge ~1.9e-3) round-trip OK.
- **`src/cnp/phifit.py`** (pipeline φ) : échantillonnage seedé de la s-boîte +
  étiquetage par un **oracle de collision GÉNÉRIQUE passé en argument** (robot-
  agnostique : le checker Drake est branché aux scènes Drake en S9+) ; deux fits
  sur la base monomiale deg ≤2/var — **SVM linéaire** (`LinearSVC` sur les points
  LIBRES étiquetés par côté start/goal ⟹ la fonction de décision est une barrière
  dont le zéro traverse l'obstacle) et **moindres carrés** à cible signée (recette
  E4 généralisée n-dim) ; **δ auto** = fraction (`safety`) d'un bas quantile de
  |φ| sur les libres (marge du libre le plus proche), plafonnée par ½·borne de
  condition (i) — δ PETIT (dalle fine ⊆ collision) ; **rationalisation** exacte +
  ré-assertion de (i) en Fraction ; **boucle propose→certifie→raffine** : sur
  UNDECIDED, on pénalise (×8) les échantillons libres tombant dans les cellules en
  échec exportées par le moteur ET on amincit la dalle (safety/2), refit.
- **E4-planaire via le pipeline complet** : φ trouvé automatiquement (sans hint),
  certifié end-to-end et **vérifié en exact** (lstsq : 76 feuilles, δ≈0.264 ;
  svm : 76 feuilles, δ≈0.505 ; oracle hand-tuné = 78). Les deux passent
  `verify.verify`.
- **Scène 3-DOF spatiale** (chaîne 3R sympy axes z,y,y, la « scène de S2 ») :
  mur frontal **piégeant le point PROXIMAL du segment** (j2-origine, fonction de
  s0,s1 seulement) sur une bande de lacet de base ⟹ tout chemin franchissant s0=0
  est en collision pour TOUT tangage = **vraie déconnexion**. Le pipeline trouve
  φ≈s0 automatiquement → **moteur-PROOF** (lstsq 9 feuilles après 1 retry ;
  svm 8) ; **cond. (i) exacte** OK ; **0 point libre dans la dalle sur 300k
  échantillons** (contrôle vérité-terrain, style S2 exit #2). Le vérificateur
  exact reste planaire jusqu'à S9 (décision actée avec Stéphane : fidélité au
  calendrier ; le 3-DOF est étiqueté « moteur-PROOF + échantillonnage », PAS
  « certifié » au sens règle 5).
- **Contrôle négatif (soundness)** : mur rétréci ×0.4 ⟹ chemin libre autour ⟹ le
  pipeline ne renvoie **jamais PROOF** (UNDECIDED sur budget).
- **Figures V2** (`scripts/make_figures.py` étendu, `phi_scenes.py` DRY) :
  `benchmarks/figures/phi_E4.png` et `phi_3dof.png` — C-space échantillonné
  (gris=collision) + lignes de niveau de φ (bleu) + dalle {|φ|≤δ} (or) +
  start (★) / goal (✚).
- `make test` : **130 passed, 0 skipped, 25 warnings, 195 s** (117 + 2 A12 +
  2 A13 + 9 phifit). `make test-fast` = **76 passed, 54 deselected, 17.4 s**.

**Décisions** :
- **Oracle de collision en argument, pas Drake en dur** (amendé SPEC §3, règle 12).
  Garde phifit robot-agnostique et sans réseau (chemin planaire = regref, chemin
  3-DOF = sympy 3R), cohérent avec la décision S2. Drake = scènes S9+.
- **δ petit = bon** : la dalle fine ⊆ collision est plus facile à certifier (et
  moins de feuilles) ; le piège initial était δ=0.5·borne (≈0.6 sur E4) qui
  avalait du libre → UNDECIDED à >1000 feuilles. La sélection finale prend une
  fraction de la marge du libre le plus proche (quantile), pas 0.5·borne.
- **SVM sur les LIBRES étiquetés par côté** (pas free/collision) : un SVM
  free/collision donnerait la frontière de l'obstacle, pas une barrière le
  traversant. Étiqueter les libres start-côté/goal-côté met le séparateur DANS le
  gap de collision. Les deux fits livrés (svm + lstsq) ; lstsq reproduit la
  recette E4.
- **Disconnexion 3-DOF par piégeage proximal** : le point proximal du segment ne
  dépend pas de s2 ⟹ une bande pleine sur (s1,s2) est garantie, donc une vraie
  déconnexion topologique (vs un mur frontal que le bras contourne en tangage —
  testé, échoue : 64/225 libres à s0=0).
- **`make_certificate(verify_loop=True)` par défaut** : le générateur s'auto-
  vérifie à l'exact et escalade max_den (A13). Coût doublé par cert, accepté
  (c'est la garantie SPEC §4).

**Pièges rencontrés** :
- **δ=0.5·borne est le mauvais réflexe** (hérité de E4 où la borne était évaluée à
  ±0.577 ; ici start/goal à ±0.9 ⟹ borne ~1.1, δ~0.55 trop épais). Diagnostic par
  balayage de δ : 0.03–0.3 PROOF (14–76 feuilles), 0.5 UNDECIDED (549 feuilles).
- **Mur frontal contournable** : un bras 3R à joint distal libre se rétracte/tangue
  pour éviter un obstacle frontal (même haut). Il faut piéger une partie **proximale**
  (indépendante du joint distal) pour garantir une bande pleine. Plusieurs géométries
  écartées avant le piège proximal (collision frac 0.07→0.23→0.37).
- **Overflow Fraction × numpy.int64** dans un script de debug : `tuple(e)` issu de
  `np.argwhere` donne des exposants numpy ⟹ `Fraction ** np.int64` déclenche un
  overflow scalaire silencieux. Le pipeline convertit en `int` natif (`tuple(int(x)
  for x in e)`) — pas affecté ; piège de debug seulement.
- **Colormap inversée** dans la figure V2 (Greys : 0=blanc) : première version avait
  gris=libre alors que le titre disait gris=collision. Corrigé (collision→0.55).
- **test-fast trop lent** (52 s) : le contrôle négatif 3-DOF (moteur jusqu'à 400
  feuilles sur dalle libre) coûtait 41 s. Budget réduit à 80 feuilles + 1 retry
  (UNDECIDED atteint vite de toute façon) ⟹ test-fast 17.4 s.

**Décompte exact (sortie de session)** : `make test` = **130 passed, 0 skipped,
25 warnings, 195 s** (mêmes 20 fork-deprecation + 5 Clarabel, documentés S0/S3).
`make test-fast` = 76 passed, 54 deselected, 17.4 s.

**Critères de sortie S5** : E4-planaire reproduit via le pipeline complet
(generate→verify exact) ✓ ; 3-DOF spatial : φ auto + certifié moteur-PROOF +
0 point libre / 300k (étiqueté honnêtement, verify exact = S9) ✓ ; gardes A12/A13
✓ ; SPEC §3 amendée (règle 12) ✓ ; décompte journalisé ✓. **V2 VALIDÉE par
Stéphane (« VALIDÉ S5-V2 »)** sur les trois points (dalle or ⊆ collision sur les
deux figures et les deux coupes du 3-DOF ; start/goal de part et d'autre dans le
libre ; bande franche non dégénérée). Code commité « S5 — V2 pending » (b07519c),
clôture par micro-commit. **S5 vert, tous critères acquis.**

**Prochaine étape** : V2, micro-commit de clôture, puis S6 — scenes.py + parser
YAML + `cnp show` Meshcat + `cnp certify` bout-en-bout + suite adversariale
initiale (porte G1'). NB S6 : `phi_scenes.py` (oracle + build_problem) est la base
du branchement scène→pipeline ; le 3-DOF spatial attend `spatial_revolute` dans
certificate+verify (S9) pour une certification exacte.

## 2026-06-11 — Revue de supervision S5 (claude.ai) — **annotations A15-A17, nouveau circuit doc**

**Mea culpa (incident doc v1.3)** : l'incohérence réconciliée en ouverture de S5
venait du superviseur, pas de Code. Le patch v1.3 livré depuis claude.ai
s'appliquait en deux scripts ; le premier a avorté sans écrire (tout-ou-rien),
le second n'a écrit que le bloc règle 9 — fichier livré à moitié patché, sans
vérification finale avant remise. La réconciliation de Code depuis le journal
était la bonne réaction (trace faisant foi, commit doc séparé, signalement).
Deux résidus que Code ne pouvait pas deviner restent à appliquer (diffs D1-D2
ci-dessous).

**Verdict S5** : validée. Trois points au-dessus de l'attendu :
(1) A13 implémentée mieux que demandé — `make_certificate(verify_loop=True)`
par défaut : auto-vérification exacte + escalade max_den, promesse SPEC §4
tenue en standard ; (2) insight SVM : étiqueter les LIBRES par côté start/goal
(et non libre/collision) place le séparateur DANS le gap de collision — bonne
formulation du problème de barrière ; (3) déconnexion 3-DOF par piégeage
PROXIMAL, géométries écartées documentées chiffres à l'appui (mur frontal
contourné en tangage : 64/225 libres). Étiquetage honnête « moteur-PROOF, pas
certifié » (règle 5 appliquée spontanément). Trouvaille à retenir : δ PETIT est
le bon réflexe (dalle fine ⊆ collision ; balayage 0.03-0.3 PROOF vs 0.5
UNDECIDED 549 feuilles) — l'inverse de l'intuition « marge confortable ».
Nit de tenue de journal : le titre de l'entrée S5 dit « V2 en attente » alors
que la clôture dit « V2 VALIDÉE » — mettre le titre à jour au micro-commit de
clôture.

**Annotations** :
- [A15 — gouvernance CLAUDE.md] Code PEUT modifier CLAUDE.md pour :
  (a) réconcilier avec des décisions de supervision journalisées,
  (b) tenir l'« État d'avancement », (c) le changelog. Code ne modifie JAMAIS
  de sa propre initiative une règle, un critère de sortie ou une porte. Tout
  diff de CLAUDE.md est listé dans l'entrée de journal de la session.
  (→ devient la règle 14, diff D3.)
- [A16 — circuit de révision doc] Les revues de supervision ne livrent plus de
  fichiers CLAUDE.md entiers (risque de copie périmée, cause racine de
  l'incident) : elles livrent une entrée de journal + instructions de diff
  explicites, que Code applique au CLAUDE.md DU REPO en tâche d'ouverture de la
  session suivante. Le repo est l'unique source de vérité.
- [A17 — verdicts mécaniques] Trois statuts produit dès S6 (CLI, sorties,
  README) : PROOF (vérifié exact) ; ENGINE-PROOF (moteur OK, vérification
  exacte indisponible — ex. 3-DOF spatial avant S9, toujours affiché avec son
  avertissement) ; UNDECIDED. La règle 5 devient visible dans le produit.
  (→ diff D4.)

**Diffs à appliquer par Code en ouverture de S6 (CLAUDE.md du repo)** :
- D1 [résidu v1.3] Section S11, tâche figures : ajouter « **[A11, V1]** :
  rogner ou hachurer la partie hors-dalle des feuilles slab-aware et tracer la
  frontière de dalle sur le panneau partition (sans quoi un lecteur croit qu'on
  certifie de la collision en zone libre) ».
- D2 [cosmétique] En-tête du plan : « révisé v1.1 » → « tenu à jour (voir
  changelog) ».
- D3 [A15] Nouvelle règle 14 « Gouvernance de CLAUDE.md » : texte de
  l'annotation A15 ci-dessus.
- D4 [A17] Section S6, ajouter aux tâches CLI : « verdicts à trois statuts
  PROOF / ENGINE-PROOF / UNDECIDED (A17) ; ENGINE-PROOF toujours accompagné de
  son avertissement ; README et messages alignés (règles 5/6) ».
- D5 Header : version 1.4, ligne de changelog « v1.3→v1.4 (revue S5, A15-A17) :
  gouvernance CLAUDE.md (règle 14) ; circuit doc par diffs journalisés ;
  verdicts à trois statuts ; résidus v1.3 appliqués (A11→S11) ».

**Prochaine étape** : S6 — ouverture : appliquer D1-D5 (+ commit doc séparé),
puis scenes.py + YAML + `cnp show` + `cnp certify` + adversarial initial
(porte G1', validation V3).

---

## 2026-06-11 — S6 (Claude Code) — Scènes + CLI + adversarial (**code vert, V3 en attente**)

**Fait** :
- **Ouverture** : diffs de revue S5 D1-D5 appliqués au CLAUDE.md du repo (circuit
  A16, repo = source de vérité), commit doc séparé (3904640) : règle 14
  (gouvernance CLAUDE.md, A15), verdicts à trois statuts dans la tâche S6 (A17),
  note figures slab-aware S11 (A11/D1), en-tête plan (D2), header v1.4 + changelog
  (D5). S5 re-vérifié vert avant démarrage (130 passed, 0 skip).
- **`src/cnp/scenes.py`** : parser YAML rationnel → `certificate.Scene` exact.
  Obstacles en **boîte axis-aligned (lo/hi par axe)** ou **H-rep brute (A,b)** ;
  enveloppe convexe du corps **extraite de la géométrie du link** (planaire =
  segment `[0,0,0]→[len,0,0]`) si `hull_vertices` absent ; budget (depth, leaves,
  temps, **heuristique d'axe**). `is_exactly_verifiable` (planaire q*=0),
  `scene_matches_cert` (cross-check scène↔cert, comparaison de rationnels en
  chaîne), `planar_collision_oracle` (oracle générique pour phifit/vérité-terrain),
  `build_problem` (dispatch planaire→certificate / spatial→ici).
- **`src/cnp/cli.py`** réécrit : `cnp certify <scene> [-o cert]` bout-en-bout
  (parse→build_problem→solve→make_certificate auto-vérifié→write) ; `cnp verify
  cert [scene]` (re-vérif exacte + cross-check scène externe optionnel) ; `cnp show
  <scene>` (Meshcat). **Verdicts à trois statuts (A17)** : PROOF (vérifié exact) /
  ENGINE-PROOF (moteur OK, vérif. exacte indisponible — TOUJOURS avec son
  avertissement) / UNDECIDED. Erreurs propres (exit 2).
- **`src/cnp/viz.py`** (minimal S6) : `show_scene` — bras planaire (squelette
  polyline + sphères aux joints) aux configs start/goal + obstacles boîtes en
  Meshcat ; URL retournée. (viz complet `cnp viz <cert>` = S11.)
- **Scènes** : `scenes/S1_relais.yaml` (E3, 46 feuilles, régression rapide),
  `scenes/S2_peigne.yaml` (**peigne 3-DOF planaire**), `scenes/S2b_spatial3.yaml`
  (3-DOF spatiale → ENGINE-PROOF).
- **G1' — S2-peigne 3-DOF certifié end-to-end** : `cnp certify scenes/S2_peigne.yaml`
  → PROOF, `cnp verify … scene` → OK (54 feuilles : 46 collision + 8 outside) +
  cross-check scène ; **0 point libre dans la dalle sur 300k échantillons**
  (vérité-terrain). Construction : E3 **relevé en 3-DOF par piégeage proximal**
  (le link MÉDIAN, fonction de s0,s1 seulement, est relayé par 3 dents ; joint
  distal s2 passif). Genuinement n=3, multi-paires, exactement vérifiable
  (planaire, q*=0).
- **`src/cnp/certificate.py`** : `Robot` reçoit un champ optionnel `joints`
  (builtin `spatial_revolute` côté moteur) ; sinon inchangé (verify ne lit jamais
  Robot). Schéma cert inchangé (spec_version 1.2).
- **Suite adversariale `tests/test_adversarial.py`** (zéro faux certificat, G1') :
  dents rétrécies ×0.7 (chemin libre) → moteur UNDECIDED, `make_certificate` lève ;
  **micro-canal** ×0.95 : grille grossière 11³ trouve **0 libre dans la dalle**
  (la grille est dupée) mais échantillonnage dense en trouve (prémisse réellement
  fausse) ET le moteur **REFUSE** (UNDECIDED) — le certificateur > la grille
  (règle 9) ; CLI refuse une prémisse fausse (exit 1, aucun cert écrit).
- **`tests/test_scenes.py`** (16 tests) : round-trip S1 reproduit l'oracle + vérifié ;
  peigne 3-DOF certifié+vérifié exact ; box≡hrep ; hull dérivé ; cross-check
  accepte/rejette (4 mutations) ; 5 scènes malformées lèvent proprement ; spatial
  → ENGINE-PROOF ; CLI certify→verify, ENGINE-PROOF spatial, rejet cross-check
  mauvaise scène ; helpers viz (positions joints + bornes boîte).
- `make test` complet : **149 passed, 0 skipped, 25 warnings, 184 s**
  (130 S5 + 16 scenes + 3 adversarial). `make test-fast` = **88 passed,
  61 deselected, 25.6 s**.

**Décisions** :
- **Peigne = E3 relevé par piégeage proximal** (pas une déconnexion distale).
  Une déconnexion 3-DOF pilotée par le joint DISTAL est défaite par la redondance
  (leçon S5 : « mur frontal contourné en tangage »). Le link médian (indépendant
  de s2) piégé sur une bande garantit une collision pour TOUT s2 → vraie
  déconnexion topologique dans la boîte 3D. Sound, peu coûteux, exactement
  vérifiable. Construction endorsée par la supervision S5.
- **`axis: margin` requis pour le peigne** : s2 est une dimension PASSIVE
  (collision/outside constants en s2) ; le défaut `oracle` (axe le plus large)
  gaspille la profondeur à découper s2 → 736 feuilles, 256 FAIL, UNDECIDED. Le
  lookahead-relais `margin` ne découpe pas la dimension passive → 54 feuilles,
  PROOF. L'heuristique ne touche jamais la soundness (règle 9) ; la mitigation
  « dims passives par intervalles » propre est S8 (SPEC §9.1). Le budget de scène
  porte donc `axis`.
- **Verdicts à trois statuts réels et testés (A17)** : ENGINE-PROOF n'est pas du
  code mort — le builtin `spatial_revolute` (chaîne 3R par joints offset/axe,
  géométrie de S5) est solvable par le moteur mais le vérificateur exact reste
  planaire jusqu'à S9 ⟹ `cnp certify scenes/S2b_spatial3.yaml` rend ENGINE-PROOF
  avec son avertissement. Rule 5 visible dans le produit.
- **φ baké, pas fité par cnp certify** : le hint φ rationnel est obligatoire dans
  la scène (le peigne = φ=s0 à la main, naturel pour un E3 relevé). Le fit
  automatique (phifit/S5) reste disponible hors-ligne pour produire le φ rationnel
  à baker ; testé sur le peigne (lstsq surajuste le bruit en s2 → φ=s0 à la main
  est le bon barrière). cnp certify reste déterministe.
- **Cross-check scène hors de verify.py** : `verify.py` reste SACRÉ (intouché,
  498 lignes, stdlib, zéro import générateur) ; le croisement scène↔cert (qui lit
  du YAML, côté générateur) vit dans `scenes.scene_matches_cert`, appelé par la
  CLI APRÈS la vérif exacte. Séparation des préoccupations : verify prouve la
  PREUVE (λ,μ,partition), le cross-check lie l'ÉNONCÉ au fichier scène.

**Pièges rencontrés** :
- **Dimension passive = explosion de feuilles** (risque #1 SPEC §9 rencontré en
  vrai) : φ=s0 sur la boîte 3D du peigne avec axe `oracle` → 256 FAIL (la
  profondeur part dans s2 inutile). Diagnostic immédiat (collision indépendante de
  s2) ; correctif `axis=margin` (54 feuilles). Pas un bug de soundness : le moteur
  refuse honnêtement quand la profondeur manque.
- **Suite adversariale d'abord à 433 s** : les solves moteur sur scènes à dalle
  LIBRE explorent profond (chaque cellule = 3 LP témoins) + échantillonnage dense
  60k. Resserré à **22.7 s** : budget feuilles borné (80 — il suffit d'UN FAIL
  pour ≠ PROOF), profondeur 12, échantillonnage dense 15k, micro-canal marqué
  `slow`. Le critère « zéro faux certificat » ne demande pas d'épuiser l'arbre,
  juste de prouver que le certificateur ne délivre pas de fausse preuve.
- **lstsq surajuste les dimensions passives** : sur le peigne 3D, le fit moindres
  carrés met du degré-2 partout (bruit en s2) → φ tordu → UNDECIDED (2 FAIL). Le
  barrière à la main φ=s0 est net et certifie. (À garder pour S9 : pénaliser/
  contraindre les coeffs des dims passives au fit.)
- **test-fast repassé sous 30 s** : les tests de scène refaisant un solve E3
  complet (cross-check, CLI certify→verify) marqués `slow` ; restent rapides le
  round-trip S1, le spatial (8 feuilles), un contrôle adversarial. 25.6 s.

**Décompte exact (sortie de session)** : `make test` = **149 passed, 0 skipped,
25 warnings, 184 s** (mêmes 20 fork-deprecation + 5 Clarabel, documentés S0/S3).
`make test-fast` = 88 passed, 61 deselected, 25.6 s.

**Critères de sortie S6** : parser YAML + scenes S1/peigne ✓ ; `cnp show` Meshcat ✓ ;
`cnp certify` bout-en-bout + verdicts 3 statuts (A17) ✓ ; suite adversariale
zéro faux certificat ✓ ; **G1' — S2-peigne certifié end-to-end (certify→verify OK) +
0 faux cert sur l'adversarial ✓** ; SPEC §6 amendée (règle 12) ✓ ; décompte
journalisé ✓. **V3 EN ATTENTE** (validation visuelle Meshcat du peigne). Code
commité « S6 — V3 pending » ; clôture par micro-commit après « VALIDÉ S6-V3 ».

**Prochaine étape** : V3 (cnp show scenes/S2_peigne.yaml), micro-commit de clôture,
puis S7 — ancrage Li-Dantam 4-DOF (porte G3'). NB S7/S9 : le builtin
`spatial_revolute` du parser est prêt côté moteur ; la certification EXACTE des
scènes spatiales (kind `spatial_revolute` dans verify.py) reste S9.

