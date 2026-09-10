# FACTCHECK v0.1 — brouillon de papier §§ 1-5 confronté au CODE

**Session P1 (Claude Code, autonome) — 9 septembre 2026.**
Cible : `docs/papers/PAPER-DRAFT.md` v0.1 (§§ Abstract, 1, 2, 3, 4, 5).
Base : HEAD `9f92ecc` (clôture S12), working tree propre hors `docs/papers/`.
État vert au moment du contrôle : `make test` = **240 passed, 1 deselected,
0 skipped, 0 warnings** (368 s).

**Cette session n'a modifié aucun code.** Tout ce qui suit est lecture, mesure et
proposition. Les points qui exigeraient une modification de `verify.py` (SACRÉ,
règle 4) sont isolés en fin de document et **non appliqués** (règle 1).

Le brouillon lui-même n'est pas modifié par Code (document de supervision,
esprit règle 14) — les phrases de remplacement sont prêtes à coller en § 2.

---

## 1. Table de contrôle

| # | Affirmation du brouillon | Verdict | Preuve (fichier:ligne) + correction |
|---|---|---|---|
| **A1** | §4 : « the shipped verifier uses the strict test » (Bern(φ−δ) **>** 0 sur au moins un coefficient) | **FAUX** | `src/cnp/verify.py:139-141` `_bern_all_nonneg` renvoie `all(v >= 0 ...)` — test **LARGE**, sur **TOUS** les points de contrôle. Appelé tel quel en `verify.py:390-391`. Le vérificateur livré n'a **aucune** forme stricte. Voir A4 : le test large est **sound**, c'est la phrase du brouillon qui est fausse. |
| **A2** | Dalle définie `|φ| ≤ δ` | **VRAI et cohérent** | `SPEC.md:82` « la dalle S = {s ∈ P : \|φ(s)\| ≤ δ} » ; `engine.py:145-149` « the slab `\|phi\| <= delta` » avec `bc.min() >= delta or bc.max() <= -delta` (large) ; `verify.py:16` idem. **Les trois sont cohérents** : dalle FERMÉE, test outside LARGE partout. |
| **A3** | §4 (i) : `φ(s_start) < −δ` et `φ(s_goal) > +δ` (strict) | **VRAI dans le code, INCOHÉRENT avec SPEC** | `verify.py:342-345` : `not (_t_eval(phi, s0) < -delta)` → rejet ; idem `> delta`. **Strict**, conforme au brouillon. **Mais `SPEC.md:80` pose (i) LARGE** : « φ(s_start) ≤ −δ et φ(s_goal) ≥ +δ ». verify est donc **plus strict que la SPEC** — sens sûr (faux rejet possible, jamais fausse acceptation), mais dérive à corriger (règle 12). |
| **A4** | §4 : le cas `φ(s*) = ±δ` exige un test outside strict | **FAUX — il n'y a pas de trou** | Le théorème est **sound avec le test large**, à condition que la preuve choisisse `s*` tel que **φ(s\*) = 0** et non `\|φ(s\*)\| ≤ δ`. Détail en §3 ci-dessous. **Aucune modification de code requise. `verify.py` reste intouché.** La correction est **purement rédactionnelle**. |
| **B** | §3.4 : `d = max(deg λ + deg N, 2·deg φ)`, `= 4` pour λ affine et φ quadratique | **VRAI (formule)** / **FAUX (le « 7 » attendu)** | `witness.py:434` `DPAD = d_X` puis `witness.py:438` `DPAD = max(d_X, 2 * d_phi)` avec `d_X = d_lam + d_N` (`witness.py:423`). `verify.py:435-436` calcule **le même** `max(d_X, 2*dphi)` — contrat générateur↔verify tenu. `d_N` est une **constante fixe = 2** (`verify.py:313`, degré par variable d'un numérateur de pose révolute). **DPAD mesuré = 4 sur les QUATRE certificats livrés**, S6 flagship inclus (λ affine ⇒ `d_lam=1`, `d_X=3` ; `degree_per_var=2` ⇒ `2·dphi=4`). **Le « S6 = 7 » du prompt est erroné** — 7 est la dimension `n`, pas le degré. Corroboration indépendante : mur scellé S9f, `cost_leaf_full_rows` 766→3 782→18 814→93 878→469 006 = **×4,99 par dimension = (d+1) avec d=4**. |
| **B-bis** | §3.6/S9f : φ linéaire déclarée à degré 2 ⇒ DPAD = 4 | **VRAI** | Les quatre certificats portent `phi.degree_per_var = 2` alors que φ est **linéaire** (`{'0,1,0,0,0,0,0': '1'}` = φ = s₁). `verify.py:466` lit `dphi` **du champ déclaré**, pas du degré effectif ⇒ `2·dphi = 4` domine `d_X = 3`. **Le papier doit décrire ce que le code FAIT** : le degré est celui **déclaré**, pas le degré effectif de φ. |
| **C** | §3.6 : division exacte par les `(1+s_i²)` communs **PUIS** détection des variables absentes | **VRAI** | `engine.pair_views` (`engine.py:296-305`) : ligne 301 `_simplify_geometry(...)` **d'abord**, ligne 302 `_geom_passive(problem.phi, verts, D, n)` **sur les tenseurs SIMPLIFIÉS**. Ordre exactement celui du brouillon. |
| **C-bis** | §3.7 : la condition d'applicabilité L6 lit les tenseurs **ORIGINAUX** | **VRAI** | `engine.py:387-390` : `blocking` teste `_tensor_depends(pr.D, i)` et `pr.verts_num` — les tenseurs **d'avant** simplification — plus `problem.phi`. Deux clauses `applicable = (not removed) and (not blocking)` (`engine.py:391`), documentées `engine.py:360-370`. Table de vérité journalisée : VRAI sur S1/S2/S2b/S4 et les trois iiwa7 ; **FAUX sur S3 shoulder-elbow** (A29 divise le roll coaxial) ⇒ repli plein-dim (`JOURNAL.md:3391-3395`). |
| **D1** | §1/§5 : `verify.py` fait **499 lignes** | **VRAI** | `wc -l src/cnp/verify.py` = **499**. Gardé par `tests/test_certificate.py:151-154` (`assert n < 500`, règle 4). |
| **D2** | §5 : « It imports `fractions`, `json`, and nothing else » | **IMPRÉCIS** | `verify.py:25-29` : `from __future__ import annotations`, `import json`, `from fractions import Fraction`, **`from math import comb`**. Il y a donc **un troisième module**, `math`. Le test d'audit AST autorise explicitement `{__future__, json, fractions, math}` (`tests/test_certificate.py:162`). L'affirmation de fond (stdlib seule, zéro import du générateur) **tient** ; l'énumération est fausse. |
| **D3** | §5 : « a 40-line exact implementation of the tensor-product Bernstein transform » | **VRAI (estimation juste)** | Bloc `verify.py:89-141` (`_shift_matrix`, `_bern_matrix`, `_matmul`, `_apply_axis`, `_bernstein_control_points`, `_bern_all_nonneg`) = **53 lignes au total, 43 non vides, 38 lignes de code**. `_matmul` n'est utilisé que par ce bloc (`verify.py:135`) — il est autonome. Remplacer l'estimation par le compte réel. |
| **D4** | Abstract/C2 : « **28** adversarial certificate mutations » ; §5 : « 26 mutations on planar certificates, plus a spatial suite and a locked-joint suite » | **§5 VRAI / C2 FAUX** | Décompte exact par suite : `tests/test_verify.py::test_mutation_is_rejected` = **26** mutations planaires paramétrées ; `tests/test_locked_joints.py::test_lock_mutation_is_rejected` = **6** mutations de verrou ; `tests/test_adversarial.py` = 6 tests dont **3** de mutation spatiale (`spatial_verifier_rejects_corrupted_multipliers`, `spatial_cross_check_catches_a_geometry_swap`, `spatial_verifier_consumes_the_joint_geometry`), les 3 autres étant des épisodes (fausse prémisse, micro-canal). **Le « 28 » est le nombre de tests du FICHIER `test_verify.py`** (26 mutations + `test_at_least_20_mutations` + `test_verifier_never_raises_on_garbage`), pas un nombre de mutations. Phrase unique cohérente proposée en §2. |
| **D5** | §5 : « On any failure it returns `(False, reason)`; **it never raises** on a corrupted certificate » | **FAUX** | `verify.py:489-491` n'attrape qu'une liste **énumérée** : `except (KeyError, ValueError, ZeroDivisionError, TypeError)`. **Contre-exemple reproduit** : remplacer `cert["obstacles"]` par une **liste** au lieu d'un dict fait remonter `AttributeError: 'list' object has no attribute 'items'` hors de `verify.verify()` (`verify.py:331`). Le test censé garantir la propriété (`tests/test_verify.py::test_verifier_never_raises_on_garbage`) n'essaie que **4 entrées superficielles** (`{}`, `{"theorem":…}`, `{"leaves":[]}`, `{"x":None}`) — ce n'est pas un fuzz. **Ce n'est PAS un défaut de soundness** (le vérificateur plante au lieu d'accepter ; il ne peut jamais transformer un faux certificat en PROOF), mais l'affirmation est réfutable en trente secondes par un relecteur. |
| **D6a** | §5 : verify flagship = **2,4 s** | **VRAI** | `benchmarks/results/20260909T092652Z/flagship_S10_iiwa_real.json` : `verify_s = 2.42`, `verdict = PROOF`, `leaves = 2`, commit `dbaaab8`. Confirmé aussi par `20260908T141015Z/L6_eval.json` : `verify_s = 2.4468`. |
| **D6b** | §5 : scène d'ancrage 4-DOF = **0,04 s** | **VRAI** | `benchmarks/results/20260612T233416Z/results.json`, scène `S3_shoulder_elbow`, `n_unlocked = 4` : `verify_exact_s = **0.0415**` (moteur 0,0426 s), commit `eb134e7`, `git_dirty = false`. |
| **D-bis** | §5 : le vérificateur tourne deux fois, « **about 4,9 s** on the flagship » | **VRAI** | `JOURNAL.md:3446-3448` : « **2,45 s** audit exact par feuille (la garde) + **2,41 s** `verify_loop` complet … deux fois … pour **~4,9 s** ». Mesuré, pas inféré. |
| **E1a** | §4 : parité chaîne iiwa7 = **1,99e-6** sur **1 500** configs | **VRAI** | `scripts/build_iiwa7_chain.py:159-181` : `for _ in range(1500)`, `rng = default_rng(7)`, **les 7 DOF** échantillonnés, référence = plant Drake **externe** à l'objet testé (conforme A46). **Re-mesuré en session : 1,985e-6.** Journalisé `JOURNAL.md:2704`. Garde CI : `tests/test_iiwa7_chain.py:65` `assert err < 5e-6`. |
| **E1b** | §4 : parité corps = **1,67e-6** sur **400 cfg × 40 sommets** | **VRAI, avec une nuance de provenance** | `JOURNAL.md:2817` journalise bien « 1,67e-6 … 400 cfg × 40 sommets ». **Mais le test livré appelle la valeur par défaut** `check_body_parity(n_cfg=**200**)` (`scripts/build_iiwa7_scene.py:186` ; `tests/test_iiwa7_body.py:63`). **Re-mesuré en session : 1,674e-6 à 200 cfg, 1,682e-6 à 400 cfg.** Le chiffre « 1,67 » correspond en fait plus exactement au run **200 cfg** ; à 400 cfg il arrondit à **1,68e-6**. |
| **E1c** | §4 : plancher SDF = **3,67e-6** | **VRAI** | `JOURNAL.md:2711-2712` : « le SDF iiwa7 lui-même n'est aligné aux axes qu'à ~3,67e-6 rad (arrondi quaternion ; axes joints 2/6 ≈ [−2,65e-6, 3,67e-6, 1]) ». Docstring `tests/test_iiwa7_chain.py:59`. |
| **E2** | §3.7 : « In every certificate reported here this loop accepted at the **first or second** denominator bound » | **VRAI mais trop faible — MESURÉ : toujours le premier** | L'échelle est `DEFAULT_MAX_DEN = 10**6` (`certificate.py:54`), escaladée **×100 par palier** jusqu'à `max_den * 10**6` (`certificate.py:487-494`). **Aucun compteur n'existe** ⇒ l'information n'était pas journalisée. **Mesurée cette session** (instrumentation en scratchpad, hors dépôt) sur les **7 scènes livrées** : `S1_relais`, `S2_peigne`, `S3_shoulder_elbow`, `S5_iiwa_shelf`, `S6_iiwa_real_shelf`, `usecase_binpicking_iiwa7`, `usecase_capot_surete_iiwa7` — **rungs = 1 partout**, échelle `[1000000]`, jamais escaladée. Le papier peut affirmer le **premier palier**. (Le maximum des dénominateurs d'un certificat n'est **pas** un indicateur du palier : le dernier λ est fixé par soustraction pour rendre `Σλ ≡ 1` exact, ce qui produit un dénominateur = ppcm des autres — d'où les 10¹⁸ et plus observés à `max_den = 10⁶`.) |
| **E3a** | §1/§3.4 : « no semidefinite program appears in the trust chain » | **VRAI** | Le SOS-SDP vit dans `tests/regref.py:110` (« Lives here, never imported by cnp »), seul fichier à importer `cvxpy` (`tests/regref.py:18`). Aucun `src/cnp/*.py` du chemin critique n'importe cvxpy. |
| **E3b** | §3.4 : « solved with **HiGHS** » | **VRAI** | `engine.py:61` `ENGINE_BACKEND = HighspyBackend()` — API C++ `highspy` directe (`witness.py:230-246`). Un back-end scipy-HiGHS reste disponible (`witness.py:189-218`), et un back-end cvxpy/CLARABEL historique (`witness.py:151-159`) **hors défaut**. Garde Mosek **verte** : `tests/test_mosek_guard.py` vérifie en **sous-processus frais** que ni `import cnp.engine` ni un solve réel par le back-end par défaut ne réveillent `mosek` **ni `cvxpy`** (importer cvxpy réveille le mosek transitif de Drake). |
| **E4** | §3.7 : « the count is **zero** on every certificate we ship » (embed rejeté) | **VRAI** | Compteurs `stats` des certificats livrés : `S6_iiwa_real_shelf` `n_embed_rejected: 0`, `usecase_binpicking_iiwa7` `0`, `usecase_capot_surete_iiwa7` `0`. Décompte complet par scène `JOURNAL.md:3410-3412` : flagship 2/0/0 · bin-picking 2/0/0 · capot 2/0/0 · S4 4/0/0 · S2 46/0/0 · S1 38/0/0 · S2b 4/0/0 · **S3 shoulder-elbow 0/4/0 (repli plein-dim exercé)** · E3 planaire 38/0/0. **Nuance** : `S5_iiwa_shelf.cert.json` est **antérieur à S12** et ne porte pas les compteurs L6 (`stats` = `n_collision/n_leaves/n_outside/n_reresolve_failed` seulement) — ne pas l'inclure dans l'affirmation. |
| **E5** | §3.5 : « an axis whose split pushes a child out of the slab if one exists, **else the axis with the best one-step look-ahead margin** » | **IMPRÉCIS** | `engine._choose_axis` (`engine.py:513-523`) : `_slab_boundary_axis` **d'abord** (`engine.py:480-488`) ✓ ; puis, **seulement si `axis_mode == "margin"`**, `_margin_axis` (look-ahead à un pas, `engine.py:491-510`). **Le défaut de la bibliothèque est `axis="oracle"`** = **axe actif le plus large** (`engine.py:841`, `scenes.py:144,152`). Le mode `margin` est **posé explicitement dans le YAML** de toutes les scènes rapportées (S2, S3, S5, S6, les trois use-cases : `budget: {… axis: margin}`) ; **S1_relais et S2b_spatial3 tournent en `oracle`**. Noter aussi que « oracle » désigne ici **l'axe le plus large**, pas une vérité-terrain — le mot risque d'induire le relecteur en erreur s'il apparaît dans le papier. Le choix d'axe **ne touche jamais la soundness**, seulement le coût (`scenes.py:136`). |
| **F1** | §3.4 : « A cell is a collision leaf if (2) has **t ≥ 0** after exact rounding (§3.7) » | **IMPRÉCIS** | `engine.py:472` : `status = "collision" if best_t > problem.tol` avec `tol = 1e-6` (`engine.py:94`). Le seuil est un **t strictement positif**, pas `t ≥ 0` — marge délibérée qui laisse la place à l'arrondi exact. Et la décision est prise par le **LP flottant**, *avant* l'arrondi exact : l'arrondi et `verify` interviennent à l'export (`certificate.py:466-495`). La formule « after exact rounding » inverse l'ordre réel. |
| **F2** | Abstract : flagship « with a **90 mm** separation margin » | **IMPRÉCIS (quantité non nommée)** | Le JSON flagship porte **deux** marges : `slab_penetration_mm = **91.5**` et `startgoal_clearance_mm = **83.3**` (`20260909T092652Z/flagship_S10_iiwa_real.json`). « 90 mm » arrondit la première. Le papier doit **dire laquelle**. |
| **F3** | Abstract/C4 : flagship certifié « **in under a minute** » | **VRAI (post-S12)** | `certify_s = **46.73**` s au bench S12 (`20260909T092652Z`), contre **726,34 s** avant L6 (`20260908T121907Z`). Forme débloquée par S12 (`JOURNAL.md`, prochaine étape) : « ~47 s bout-en-bout, dont ~39 s de construction FK symbolique » (`phases_s: build_fk_sympy 39.09, branch_and_bound 1.3, export_certificate 6.34`). **Mentionner la décomposition** : le coût dominant n'est pas la preuve, c'est la construction FK. |
| **F4** | Abstract/C3 : « a measured **443×** reduction of the per-leaf LP on the 7-DOF flagship » | **VRAI** | `reduction_x = **442.9**` sur le flagship `S6_iiwa_real_shelf` (`cost_leaf_reduced_rows = 1070` vs `cost_leaf_full_rows = 473870`). |
| **F5** | C3 : « the affine witness certifies **every k ≤ 7** » sur les disconnexions synthétiques scellées | **VRAI pour k = 3..7** | `benchmarks/results/20260613T014131Z/wall_resonde_S9f.json` : PROOF à k = 3, 4, 5, 6, 7 avec `lam_degree = affine`, `verify_ok = true` partout. **k = 1 et 2 ne sont pas dans ce banc** — écrire « every k from 3 to 7 » ou citer S1/S2 (planaires, n = 2 et 3) pour le bas de gamme. |
| **F6** | Abstract : « in **seconds for 5–6-DOF** scenes » | **IMPRÉCIS** | Scènes livrées : `S4_iiwa_bin` **n = 5** → moteur 0,15 s + verify 0,157 s ✓. **Aucune scène 6-DOF livrée** ; le seul point 6-D est le **mur scellé synthétique** k = 6 (moteur 10,8 s, verify 1,16 s). Dire « 5-DOF » pour les scènes robot et renvoyer la famille synthétique k = 6 à son statut de banc. |
| **F7** | C2/§5 : « < 500 lines, standard library only, **zero imports from the generator** », vérifié par un audit AST | **VRAI** | `tests/test_certificate.py:151-154` (< 500 lignes) et `:157-172` (audit AST : `allowed = {__future__, json, fractions, math}`, `assert "numpy" not in mods and "cnp" not in mods`). |

---

## 2. Corrections à porter au brouillon (phrases prêtes à coller)

### 2.1 §4, preuve du théorème — LE point critique (A1/A4)

Le brouillon invente une exigence de stricture qui **n'existe pas dans le code**, pour
fermer un cas frontière que la preuve **n'a en réalité jamais besoin d'ouvrir**. Il suffit
de choisir `s*` au niveau **zéro** de φ plutôt que dans la dalle fermée : par le TVI, un
chemin qui va de `φ < −δ` à `φ > +δ` **atteint la valeur 0**, strictement à l'intérieur de
la dalle, où aucune feuille *outside* ne peut se trouver (elle exigerait `|φ| ≥ δ > 0`).

**Supprimer**, dans la preuve du Théorème 1, tout le passage « If C were an outside leaf,
(iii) would give … the shipped verifier uses the strict test. » et le **remplacer** par :

> *Proof.* Let γ be such a path. By (i), φ(γ(0)) < −δ < 0 < δ < φ(γ(1)), so by the
> intermediate value theorem applied to the continuous map φ∘γ there is τ with
> **φ(s\*) = 0**, where s\* = γ(τ). By (ii) s\* lies in exactly one leaf C. C cannot be an
> outside leaf: (iii) would give φ(s\*) ≥ δ or φ(s\*) ≤ −δ, both impossible since δ > 0.
> Hence C is a collision leaf with pair (B, O). Since T(s\*) = δ² − φ(s\*)² = δ² > 0, (iv)
> gives, for every face j, g_j(s\*) ≥ μ_j T(s\*) ≥ 0, which after division by D_ℓ(s\*) > 0
> reads a_jᵀ x(s\*) ≤ b_j; and Σ_k λ_k(s\*) = 1 with λ_k(s\*) ≥ 0 puts x(s\*) in B(s\*). So
> x(s\*) ∈ B(s\*) ∩ O and γ(τ) is a collision configuration, contradicting the hypothesis. □

**Conséquence à propager** — ce que le certificat prouve est la dalle **OUVERTE** :

> Every s ∈ P with |φ(s)| < δ lies in a leaf; it cannot be an outside leaf, hence it is a
> collision leaf, hence it is in C_obs. The certificate therefore establishes
> **{s ∈ P : |φ(s)| < δ} ⊆ C_obs**, and Lemma 1 needs no more than that. Nothing is
> claimed about the boundary {|φ| = δ}, and nothing needs to be.

**Amender aussi le Lemme 1 (§3.3)** — remplacer la dalle fermée par l'ouverte dans
l'énoncé *du lemme* (la définition §3.3 de Σ peut rester fermée si elle est utilisée
ailleurs, mais alors le lemme doit citer Σ° = {|φ| < δ}) :

> **Lemma 1 (slab separation).** If **{s ∈ P : |φ(s)| < δ} ⊆ C_obs**, φ(s_start) < −δ and
> φ(s_goal) > δ, then no continuous path in P ∩ C_free joins s_start to s_goal.
> *Proof.* φ∘γ is continuous and passes from below −δ to above δ, hence takes the value 0
> at some γ(τ), which therefore lies in the open slab ⊆ C_obs. □

**Et remplacer la condition (iii) du Théorème 1** — la garder **large**, telle que le code
la teste, sans mention d'une forme stricte :

> (iii) every outside leaf C satisfies Bern_C(φ − δ) ≥ 0 or Bern_C(−φ − δ) ≥ 0
> (coefficient-wise; this is exactly the shipped test, `verify.py:390`).

> **Remark.** The outside test is non-strict, and deliberately so: the proof selects a
> point at which φ vanishes, so the slab boundary never has to be adjudicated. A strict
> test would reject certificates the large one accepts, and prove nothing more.

### 2.2 §5, imports (D2)

> It imports `json`, `fractions` and `math.comb` — three standard-library names, and
> nothing else; in particular it imports nothing from the generator, a property checked
> in the test suite by walking the module's abstract syntax tree.

### 2.3 §5, taille de l'implémentation Bernstein (D3)

> … no notion of Bernstein bounds beyond a self-contained 53-line block (38 lines of
> code) implementing the exact tensor-product Bernstein transform.

### 2.4 Abstract / C2 / §5, décompte des mutations (D4)

Phrase **unique et cohérente**, à reprendre à l'identique aux trois endroits :

> hardened against **32 adversarial certificate mutations** — 26 on a planar certificate,
> 6 on a locked-joint certificate — together with a spatial mutation suite and two
> recorded episodes in which the certifier refused a disconnection claim that dense
> sampling had validated.

(Et supprimer le « 28 » de l'Abstract et de (C2) : c'est le nombre de fonctions de test du
fichier `test_verify.py`, pas un nombre de mutations.)

### 2.5 §5, robustesse (D5)

> On any failure it returns `(False, reason)` rather than raising: malformed inputs are
> caught as `KeyError`, `ValueError`, `ZeroDivisionError` or `TypeError` and reported as a
> rejection. This is a convenience for callers, not a hardening claim — the verifier is
> not a fuzz target, and a sufficiently ill-formed input can still abort it. Soundness
> does not depend on it: an aborted verification is not an accepted certificate.

*(Si la supervision préfère conserver l'affirmation absolue, voir §4 — elle demande une
modification de `verify.py`.)*

### 2.6 §3.4, seuil d'acceptation d'une feuille (F1)

> A cell is a *collision leaf* when (2) returns a strictly positive margin (the shipped
> tolerance is t\* > 10⁻⁶). That decision is taken on the floating-point LP; the
> multipliers are only then made exact (§3.7) and submitted to the exact verifier, which
> is the sole arbiter of the final verdict.

### 2.7 §3.5, heuristique d'axe (E5)

> … and otherwise bisects it at the midpoint of one axis: an axis whose split pushes a
> whole child out of the slab if one exists, else — in the `margin` mode used by every
> scene reported here — the axis with the best one-step look-ahead margin (the library's
> own default fallback is simply the widest active axis). The axis rule affects cost only,
> never soundness: any midpoint partition is re-proved by the verifier from the leaf list
> alone.

### 2.8 §3.4/§3.6, degré de padding (B, B-bis)

> All polynomials in (1) and in λ_k ≥ 0 are expanded at a common per-variable degree
> d = max(deg λ + deg N, 2·deg φ), where deg N = 2 is fixed by the half-angle substitution
> and deg φ is the degree **declared** with the barrier (not its effective degree — a
> linear φ declared at degree 2 still yields d = 4). Every certificate reported here has
> d = 4 (affine λ, barrier declared quadratic), and the verifier recomputes the same d
> from the certificate's own fields.

Ajouter, comme corroboration mesurée du modèle de coût de (C3) :

> The (d+1)^k law is visible directly in the sealed-wall family: the full-dimension row
> count per leaf runs 766, 3 782, 18 814, 93 878, 469 006 for k = 3…7 — a factor 4,99 per
> added active dimension, i.e. d + 1 with d = 4.

### 2.9 §4, fidélité du corps (E1b)

> … agreeing with Drake's link to 1.67·10⁻⁶ over 200 random configurations and all 40
> support vertices (1.68·10⁻⁶ over 400).

### 2.10 Abstract, marge du flagship (F2)

> … proven unable to reach a target behind an overhead shelf, the trapping band reaching
> 91.5 mm inside the shelf and start and goal clearing the obstacle by 83.3 mm …

### 2.11 Abstract / C4, temps et périmètre DOF (F3, F6)

> … in well under a second for the 2- to 5-DOF scenes, and in 47 s end to end for a KUKA
> iiwa7 — of which 39 s is symbolic forward-kinematics construction and 1.3 s the
> branch-and-bound proof itself …

et, pour la famille synthétique (F5) :

> … on a family of sealed synthetic disconnections the affine witness certifies every
> k from 3 to 7 …

### 2.12 §3.7, compteur de repli (E4) et palier d'arrondi (E2)

> In every certificate reported here this loop accepted at the **first** denominator bound
> (10⁶); the escalation path has never been taken on a shipped scene.

> … it would fall back to the full re-solve and be counted. The count of *rejected*
> embeddings is zero on every certificate we ship; the fallback itself is not dead code —
> it carries all four leaves of the 4-DOF anchor scene, whose coaxial roll makes the
> embedding condition genuinely false.

---

## 3. Le cas frontière, en détail (justification de A4 = NON)

**Ce que fait le code.** Une feuille est acceptée *outside* si **tous** les coefficients de
Bernstein de `φ − δ` sont `≥ 0`, **ou** tous ceux de `−φ − δ` sont `≥ 0`
(`verify.py:388-393` via `_bern_all_nonneg`, `verify.py:139-141`). Cela garantit `φ ≥ δ`
sur toute la feuille, ou `φ ≤ −δ` sur toute la feuille.

**Le cas que le brouillon redoute est réel… mais inatteignable par la preuve.** Il existe
bel et bien des feuilles *outside* légitimes contenant un point où `φ = δ` exactement — par
exemple φ = s₁, δ = 1/2, cellule `s₁ ∈ [1/2, 1]` : les coefficients de Bernstein de `φ − δ`
y valent 0 et 1/2, tous `≥ 0`, feuille acceptée, et le point `s₁ = 1/2` appartient à la fois
à la feuille et à la dalle **fermée**. Si la preuve part de « il existe s\* avec
`|φ(s*)| ≤ δ` », elle bute effectivement sur ce point.

**Pourquoi il n'y a pas de trou.** La preuve n'a aucune raison de partir de là. Le théorème
des valeurs intermédiaires, appliqué à `φ∘γ` qui va d'une valeur `< −δ` à une valeur `> +δ`,
donne **toutes** les valeurs intermédiaires — en particulier **0**. En prenant `s*` tel que
`φ(s*) = 0` :

- `s*` ne peut pas être dans une feuille *outside* : cela imposerait `φ(s*) ≥ δ > 0` ou
  `φ(s*) ≤ −δ < 0`, contradiction immédiate. **Aucune stricture n'est requise** — la marge
  est `δ`, pas `ε`.
- `s*` est donc dans une feuille *collision* (`verify.py:487` rejette tout autre statut),
  où `T(s*) = δ² − 0 = δ² > 0`, donc `g_j(s*) ≥ μ_j T(s*) ≥ 0` pour chaque face, donc
  collision.

**Conclusion.** Le trou est dans la **rédaction** du brouillon, pas dans le théorème ni dans
le code. Le test large est sound. `verify.py` **n'a pas à être touché** — ce qui est la
bonne nouvelle, puisqu'il est sacré (règle 4) et sorti de S12 à **zéro diff**.

**Bénéfice secondaire pour le papier** : formuler la garantie sur la dalle **ouverte**
`{|φ| < δ} ⊆ C_obs` est à la fois plus faible à prouver et suffisant pour le lemme — c'est
la formulation honnête de ce que le certificat établit réellement.

---

## 4. Décisions de supervision requises

A4 étant **NON**, aucune décision n'est requise sur le cas frontière : la correction est
rédactionnelle et n'engage que le brouillon (document de supervision). Restent **trois**
points qui dépassent le mandat de cette session.

### D-P1 — Incohérence SPEC §2 (i) large vs `verify.py` strict [A3]

`SPEC.md:80` pose `φ(s_start) ≤ −δ` et `φ(s_goal) ≥ +δ` ; `verify.py:342-345` exige
`< −δ` et `> +δ`. Le sens de l'écart est **sûr** (verify plus strict ⇒ au pire un faux rejet,
jamais une fausse acceptation), et la version stricte est celle que le papier annonce.
**Proposition** : amender **SPEC §2 (i) en strict** pour aligner la spec sur le code et sur
le papier (règle 12, « une spec fausse est pire que pas de spec »). Aucun changement de code.
Une session ultérieure applique ; **non appliqué ici**.

### D-P2 — `verify.verify` peut lever sur entrée malformée [D5]

Contre-exemple reproduit : `obstacles` fourni comme liste ⇒ `AttributeError` non attrapée
(`verify.py:331`, liste d'exceptions `verify.py:490`). Deux issues :

- **(a) Rédactionnelle, coût nul** — affaiblir la phrase du papier (texte prêt en §2.5).
  **Recommandée** : elle ne touche pas au module sacré et dit le vrai.
- **(b) Correction du code** — une ligne : `except (KeyError, ValueError, ZeroDivisionError,
  TypeError)` → `except Exception` à `verify.py:490`, plus un élargissement de
  `test_verifier_never_raises_on_garbage`. **Impact** : `verify.py` est SACRÉ (règle 4) ;
  tout diff impose la suite adversariale complète (règle 1) et casserait le « zéro diff »
  acquis en S12. Le budget de lignes le permet (499 < 500, mais **une seule ligne de marge**
  — élargir le test de garbage pousserait le fichier au-dessus si on y ajoutait du code, ce
  qui n'est pas le cas ici puisque le test vit dans `tests/`).

**Arbitrage demandé à la supervision.** Recommandation de cette session : **(a) pour le
papier maintenant**, et **(b) plus tard**, groupé avec un autre chantier `verify.py`, s'il y
en a un — jamais pour lui seul.

### D-P3 — Le mot « oracle » dans le code désigne l'axe le plus LARGE [E5]

`axis="oracle"` (défaut de `engine.solve`, `engine.py:841`) ne désigne aucune vérité-terrain :
c'est l'heuristique « axe actif le plus large ». Le brouillon ne l'emploie pas — **bien** —
mais §6/§7 risquent de le faire en citant les configurations de scènes. **Proposition** :
soit le papier ne nomme jamais ce mode, soit il le nomme « widest-axis ». Aucun changement de
code (renommer toucherait les YAML livrés et les empreintes de reproductibilité).

---

## 5. Récapitulatif

**Vérifié : 31 affirmations.**

- **FAUX : 3** — A1 (test outside « strict » : il est large), D4/C2 (« 28 mutations » :
  c'est 26 + 6, le 28 est un nombre de tests de fichier), D5 (« never raises » :
  contre-exemple reproduit).
- **IMPRÉCIS : 5** — D2 (imports : `math` oublié), E5 (le look-ahead n'est pas le défaut de
  la bibliothèque), F1 (`t ≥ 0` → `t > 10⁻⁶`, et avant l'arrondi, pas après), F2 (« 90 mm » :
  quantité non nommée), F6 (« 5-6 DOF » : aucune scène robot 6-DOF).
- **VRAI mais à préciser ou renforcer : 3** — E2 (mesuré : **premier** palier partout, pas
  « premier ou deuxième »), F5 (k = 3..7, pas « k ≤ 7 »), E1b (chiffre journalisé exact,
  mais le test livré tourne à 200 cfg, pas 400).
- **VRAI, rien à changer : 19** — A2, A3 (vs code), B, B-bis, C, C-bis, D1, D3, D6a, D6b,
  D-bis, E1a, E1c, E3a, E3b, E4, F3, F4, F7.
- **Cas frontière A4 : PAS de trou.** Correction purement rédactionnelle, `verify.py` intact.

**Deux écarts hors brouillon**, relevés au passage : SPEC §2 (i) est large là où `verify.py`
est strict (D-P1), et `verify.py` peut lever sur une entrée malformée (D-P2). Aucun des deux
n'affecte la soundness ; les deux sont proposés en §4, aucun n'est appliqué.

**Le point le plus important pour la supervision** : le brouillon §4 affirme que le
vérificateur livré utilise un test strict. Il ne le fait pas, et **il n'a pas à le faire** —
mais un relecteur qui ouvre `verify.py:139` verra immédiatement le `>= 0` et conclura que la
preuve du papier ne tient pas. La réécriture de §2.1 supprime la contradiction sans toucher
au code.
