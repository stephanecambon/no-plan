# DECISION-G2.md — Go/no-go technique G2′ (5-6 DOF)

Session S9d (Claude Code) · 12 juin 2026 · commit de référence `eb134e7` (arbre propre).
Sortie formelle du pilotage D22 : la supervision la revoit, **Stéphane la SIGNE avant toute
ouverture de S10**. Ce document est une RECOMMANDATION ; la décision de re-scope, si rouge,
se prend avec Stéphane (pas dans Claude Code).

---

## 1. Verdict G2′ (chiffré) — **GO (vert)**

Critère de sortie G2′ (SPEC §8) : *S4 (5-6 DOF) certifiée PROOF, vérifiée en arithmétique
exacte, en < 1 h sur la machine cible, < 10⁴ feuilles, compteur A32 à zéro.*

| Exigence G2′                         | Mesuré (scène S4 iiwa-like bac profond)             | Verdict |
|--------------------------------------|------------------------------------------------------|---------|
| Verdict                              | **PROOF** (moteur + `verify.py` exact indépendant)   | ✅      |
| Vérification exacte indépendante     | **OK** (`cnp verify` re-dérive la FK, joints verrouillés cos/sin) | ✅ |
| Temps total (machine cible = laptop CPU) | **5-DOF ≈ 1,0 s · 6-DOF ≈ 3,9 s** (certif + verify) — marge ×1000 sous 1 h | ✅ |
| Nombre de feuilles                   | **8** (5-DOF *et* 6-DOF) — marge ×1250 sous 10⁴      | ✅      |
| `n_reresolve_failed` (A32)           | **0** (dissonance décision↔certificat nulle)         | ✅      |

Machine cible : MacBook (Apple Silicon arm64), Python 3.12, **CPU pur, sans GPU**.
Les cinq exigences sont tenues avec une marge de 3 ordres de grandeur. **G2′ est VERT.**

---

## 2. Ce qui est certifié — et la lecture honnête

**Scène S4** (`scenes/S4_iiwa_bin.yaml`) : bras iiwa-like 7 joints (chaîne S-R-S, longueurs
de liens ~ iiwa, axes lacet/tangage alternés), **2 joints poignet VERROUILLÉS à 0** (cos=1,
sin=0) ⟹ 5 DOF actifs ; bac profond à mur frontal scellé. La **déconnexion est PROXIMALE** :
le segment certifié (link 2) a son extrémité proximale piégée dans le mur sur toute la bande
de lacet de base et tout tangage du box ; **aucun jeu des joints distaux ne l'en sort** (ils
ne déplacent que des points au-delà du link 2).

**Vérité-terrain dense AVANT certification** (règle 9, leçon micro-canal) : start/goal libres ;
**0 point libre dans la dalle sur 40 000 échantillons seedés** ; libre des deux côtés (deux
composantes) ; contrôle négatif (mur descellé) ⟹ **UNDECIDED, jamais de faux certificat**.

**Gate visuel [V5, D38] : VALIDÉ.** « VALIDÉ S9-V5 » donné par Stéphane (S9d) sur l'artefact
interactif A24 (`cnp show scenes/S4_iiwa_bin.yaml --interactive`, joints verrouillés annoncés,
butées = limites A25, fantômes start/goal, boutons d'évasion à verdict) + coupes C-space — l'œil
humain a validé l'INTENTION de la scène (le certificat, lui, fait foi sur la vérité mathématique).

**Lecture honnête (le point central, non un angle mort) [amendé A35].** La scène n'a que **3
dimensions actives** {lacet, tangage épaule, coude} alors qu'elle a 5-6 DOF : les joints distaux
sont *prouvés passifs* pour la paire de collision. Ce n'est **pas** un cas favorable trié sur le
volet, mais ce n'est PAS non plus une « propriété intrinsèque des déconnexions » (formulation
trop forte, corrigée) : des déconnexions à dims actives ÉLEVÉES existent (ex. un bras entier
franchissant une fenêtre étroite — la collision dépend alors de tous les joints). C'est un
**effet de SÉLECTION de NOTRE schéma** (barrière scalaire bas-degré φ + dalle) : les
déconnexions que ce schéma certifie **à bas coût** sont celles où un corps **proximal** est
piégé (un bras ne peut pas le déplacer ⟹ peu de joints actifs) ; un piégeage distal serait
défait par la redondance (leçon S5/S6/S7). **Conséquence stratégique** : sur la classe que
notre schéma certifie à bas coût, le coût suit les **dims actives**, pas le **DOF total** — la
montée en DOF y est quasi gratuite (table §3). Le régime à dims actives élevées est MESURÉ au
§3d (bench du mur) ; la portée de coût (d+1)^actif est énoncée comme limite assumée au §5.3.
*[supersédé par §3d-bis : pas de mur k≤7 ; frontière = taille du LP]*

---

## 3. Calibration du modèle de coût (A31 / D20 / D31)

Même famille de scènes (le bac S4 avec un nombre croissant de joints verrouillés : les 3
joints actifs {0,1,2} restent fixes, seul le nombre de joints PASSIFS croît). `axis=margin`,
réductions A29/A30 actives. Coût/feuille = lignes Bernstein de la paire WALL (faces + λ≥0).

### 3a. feuilles(n) et coût/feuille — globaux

| n (DOF actifs+passifs) | actifs | passifs | feuilles | coût/feuille RÉDUIT (A30) | coût/feuille PLEIN (sans réduction) | facteur | certif s | verify s | A32 |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 0 | **8** | 766  | 766    | ×1,0   | 0,34 | ~0,04 | 0 |
| 4 | 3 | 1 | **8** | 766  | 3 782  | ×4,9   | 0,36 | ~0,05 | 0 |
| 5 | 3 | 2 | **8** | 766  | 18 814 | ×24,6  | 0,84 | 0,16  | 0 |
| 6 | 3 | 3 | **8** | 766  | 93 878 | ×122,6 | 3,26 | 0,68  | 0 |

**Lecture** : feuilles(n) = **8, constant** (les dims passives n'ajoutent aucune feuille —
le moteur ne branche jamais dessus, A18). Coût/feuille réduit = **766 lignes, constant** (les
3 dims actives fixent (d+1)³). Le coût PLEIN (ce que coûterait l'absence de réduction) explose
en (d+1)ⁿ : le **facteur de réduction A30 atteint ×122 à 6-DOF** et croît ≈×5 par dim passive.
Le temps de certification croît modestement (la re-résolution pleine-dim du certificat à
l'export, soundness S8, est le seul terme qui voit le n complet) : **3,3 s à 6-DOF**, loin de 1 h.

### 3b. Réduction PAR-PAIRE proximale vs distale (A30) — première validation réelle

La scène S4 livrée n'a **qu'UN corps certifié** (link 2) ⟹ sur elle, la réduction par-paire ≡
la réduction globale (dit honnêtement). Le levier par-paire se mesure sur une **variante
deux-corps** de la même chaîne (n=7, sans lock), paire proximale sur link 2 et paire distale
sur link 4 :

| Paire | corps | dims actives | lignes LP par-paire (A30) | lignes LP si global {0,1,2,3,4} |
|---|---|---|---|---|
| PROX (link 2) | proximal | {0,1,2}       | **766**    | 18 814 |
| DIST (link 4) | distal   | {0,1,2,3,4}   | 18 814     | 18 814 |

**Lecture** : la paire proximale ne paie que ses 3 dims actives (**766 lignes**) là où la
réduction globale (union des actifs de toutes les paires = {0,1,2,3,4}) lui imposerait 18 814 —
**×24,6 par-paire** sur la paire proximale. C'est la première mesure réelle (hors synthétique
S9a) du levier A30 : *chaque paire paie SES dims actives, pas l'union*.

### 3c. Ancrage S3 (4-DOF, Li-Dantam, benchmark canonique régénéré)

Benchmark canonique régénéré sur arbre **propre** (commit `eb134e7`, `git_dirty=false`),
`benchmarks/results/20260612T233416Z/` : **S3 (4-DOF) = moteur 0,043 s + verify exact 0,041 s**.
(S1 46 feuilles 0,48 s ; S2-peigne 54 feuilles 1,36 s ; S4 iiwa 8 feuilles 0,15 s.)

### 3d. Le MUR de scaling en dimensions ACTIVES (pilotage Stéphane — mesurer la limite)

Là où §3a-c font varier les dims PASSIVES (gratuites), ce bench fait varier les dims
**ACTIVES** k — le régime cher du §5.3, mesuré au lieu d'être supposé. Famille synthétique
(`scripts/wall_bench.py`) : chaîne k-joints dont le corps certifié est le **dernier link** (sa
géométrie dépend de TOUS les joints ⟹ k dims actives DÉTECTÉES par `pair_views`, asserté, aucun
padding passif) ; barrière φ=lacet de base ; obstacle dimensionné à la portée du dernier link
sur la bande ⟹ dalle entièrement en collision. **Chaque k est une VRAIE déconnexion** (vérité-
terrain dense seedée AVANT certif : start/goal libres, **0 libre dans la dalle / 8 000**, libre
des deux côtés). Budget plafonné 10⁴ feuilles / 30 min. Mesuré le 13 juin 2026, commit `81aeefe`
+ working tree (`git_dirty=true` — bench exploratoire ; reproductible : `python scripts/wall_bench.py`,
seedé). `lam_degree=affine` (le schéma livré).

| k actif | verdict | feuilles | coût/feuille (lignes Bernstein) | moteur s | certif s | verify s | A32 |
|---|---|---|---|---|---|---|---|
| **3** | **PROOF** | 2  | 766    | 0,12 | 0,03 | 0,01 | 0 |
| **4** | **PROOF** | 2  | 3 782  | 0,21 | 0,10 | 0,05 | 0 |
| **5** | **UNDECIDED** (pratique — *re-sondé S9f, cf. §3d-bis*) | 48 | 18 814 | 45,1 | — | — | — |

**Lecture honnête (confronter, pas confirmer l'hypothèse)** :
- **Coût/feuille ×(d+1)≈5 par dim active CONFIRMÉ** : 766 → 3 782 → 18 814 (×4,94 puis ×4,97).
  Ici **coût réduit ≡ coût plein** (toutes les dims sont actives — rien à réduire pour A30 ; c'est
  le sens du bench : isoler le coût des dims ACTIVES, là où A18/A30 n'aident pas).
- **k=4 est le plus haut point CERTIFIÉ** (PROOF + verify exact, ~0,36 s, A32=0) : une dimension
  active **au-dessus** du voisin algébrique le plus proche (Henrion et al. 2024, ensembles
  abstraits n≤3) — claim mesurable pour le papier. **Ceinture [A37] : dans des cadres DIFFÉRENTS**
  (eux = schéma *nécessaire-et-suffisant* sur ensembles abstraits ; nous = schéma *suffisant* sur
  bras articulés) ; la comparaison est légitime mais à formuler pour survivre à un reviewer
  (possiblement Henrion lui-même). *(S9f re-mesure ce point : cf. §3d-bis.)*
- **Le mur est à k=5** (mesure S9e), et c'est un **UNDECIDED PRATIQUE, pas de budget** : 48 feuilles
  (≪ 10⁴), 45 s (≪ 30 min) — le moteur termine sans certifier au témoin affine. **Cause de
  terminaison [A37] : à documenter exactement** — la subdivision Bernstein converge en théorie (à
  raffinement infini l'affine pourrait certifier si la barrière existe), donc ce qui est mesuré est
  un mur **pratique** (« non certifié à coût raisonnable »), pas structurel. Sonde unique (pilotage) :
  `lam_degree=quadratic` à k=5 ⟹ **un SEUL LP de feuille dépasse 150 s**. Honnêteté : UNDECIDED ≠
  « faisable » (SPEC §6) ; la vérité-terrain dense SUGGÈRE que la déconnexion k=5 est réelle, mais
  l'échantillon ne fait pas foi (leçon micro-canal) — on dit « notre schéma affine ne la prouve pas
  au budget », pas « elle est infaisable ».
  **⚠ Re-sondé en S9f (cause de terminaison EXACTE + budget réel + profondeur relevée) : voir
  l'ADDENDUM §3d-bis daté, qui SUPERSÈDE ce point k=5.** Le corps signé n'est pas réécrit au-delà de
  cette retouche (D42) ; les chiffres S9e ci-dessus restent l'historique, l'addendum porte le résultat.

**Conclusion pour le dossier** : le régime à dims actives élevées N'est PLUS « non mesuré,
probablement cher » (§5.3) — il est mesuré : **bas coût et certifié jusqu'à k=4, mur du schéma
affine à k=5**. Figure log `benchmarks/figures/S9e_wall/cost_vs_active_dims.png`. C'est la portée
honnête à énoncer dans le papier (régime (d+1)^actif), et la frontière au-delà de laquelle un cas
d'usage exigeant ≥5 dims actives est un point de pivot (re-scope avec Stéphane).

---

## 3d-bis. Re-sonde du mur (S9f, AUTONOME — 13 juin 2026) — **SUPERSÈDE le point k=5 du §3d**

Session S9f (Claude Code, autonome ; le verdict GO signé est inchangé — S9f *précise* la
frontière). Reproductible : `python scripts/run_resonde_S9f.py` (sealed scenes, seedé) ;
figure `benchmarks/figures/S9f_wall/cost_vs_active_dims.png` ; résultats datés +
commit + `git_dirty` dans `benchmarks/results/` (règle 7). **Quatre constats : L0a (diagnostic +
scène non étanche), re-mesure étanche, L0b (quadratic), L1 (anisotrope).**

**(1) L0a — le « mur k=5 » de S9e était un ARTEFACT, pas un mur du témoin affine.** Deux causes
cumulées, diagnostiquées :
- **Plafond de profondeur silencieux.** Le run k=5 de S9e s'est arrêté à 48 feuilles / 45 s non
  pas par budget (10⁴ feuilles / 30 min jamais atteints) mais par un **TROISIÈME plafond,
  `Problem.max_depth=16`** — désormais exposé dans `EngineResult.stats["termination"]`
  (= `depth_exhausted`, `max_depth_reached=16/16` ; instrumentation S9f). 10 cellules straddling
  la dalle ont touché la profondeur 16 ⟹ feuilles FAIL ⟹ UNDECIDED. Le budget réel n'a jamais
  été dépensé.
- **Scène non étanche.** À profondeur relevée et budget réel, le certificateur **REFUSE
  SAINEMENT** la scène k=5 de S9e : son obstacle WALL est la **boîte englobante de 4 000
  échantillons ALÉATOIRES** de la portée du dernier link + marge 0,02, qui **sous-couvre la
  portée aux COINS** de l'espace de config (autres joints ≈ ±0,25). Des configs libres survivent
  dans la dalle (extrémité du link hors boîte de ~0,008 à 0,04) ; la vérité-terrain uniforme à
  8 000 échantillons les manque (les coins sont de mesure infime), **le certificateur les trouve**
  (règle 9 : la grille ne fait pas foi). ⟹ la scène k=5 de S9e **n'est PAS une déconnexion
  étanche** ; UNDECIDED y était le verdict SAIN, pas une insuffisance du témoin affine.

**(2) Re-mesure sur des déconnexions PROUVÉES ÉTANCHES.** Famille reconstruite avec un obstacle
**scellé par bornes de Bernstein** (chaque face `h = max_cp bcN_cp/bcD_cp` ⟹ `X_i ≤ h` sur TOUTE
la bande, *prouvé* par linéarité de Bernstein), vérité-terrain dense + **biaisée-coins**
ré-assertée (0 libre / dalle), start/goal libres. **Le témoin affine certifie CHAQUE k mesuré** :

| k actif | verdict | feuilles | **cause de terminaison** | coût/feuille (lignes, schéma livré DPAD=4) | moteur s | verify exact | A32 |
|---|---|---|---|---|---|---|---|
| **3** | **PROOF** | 2 | certified | 766     | 0,1  | **OK** | 0 |
| **4** | **PROOF** | 2 | certified | 3 782   | 0,2  | **OK** | 0 |
| **5** | **PROOF** | 4 | certified | 18 814  | 1,6  | **OK** | 0 |
| **6** | **PROOF** | 4 | certified | 93 878  | 11,2 | **OK** | 0 |
| **7** | **PROOF** | 2 | certified | 469 006 | 72,3 | **OK** | 0 |
| **8** | **UNDECIDED** (budget_time) | 2 | budget_time | ~2,3 M | 455 (≫ deadline 300 s) | — | — |

**Il n'y a PAS de mur du schéma affine en dims actives dans la plage mesurée (k≤7 : PROOF +
verify EXACT + A32=0).** Le coût n'est **pas** une explosion de feuilles : feuilles **2-4
quasi-constantes** ; c'est la taille d'**UN LP**, **(d+1)^k** (×4,99/dim mesuré : 766→3 782→
18 814→93 878→469 006). La vraie **frontière PRATIQUE** est la taille du LP unique : ~470k lignes
à k=7 (PROOF, ~95 s total) ; à **k=8 (~2,3 M lignes) la résolution d'UN SEUL LP dépasse le budget
temps** (UNDECIDED `budget_time` : 455 s pour 2 feuilles ; **deadline explicite [A38-2] = 300 s**
`run_resonde_S9f.py:engine_only(max_time_s=300)`, dépassée *pendant* une résolution LP unique — un
solve LP est **atomique (non-préemptible)**, la garde budget ne se déclenche qu'au retour du LP à
455 s — la scène reste prouvée étanche, vérité-terrain 0 libre). C'est une **frontière de
COÛT-LP, pas de certifiabilité** (point à paralléliser / réduire la taille du LP — A30 n'aide pas
ici, toutes dims actives), et k=8 = UNDECIDED-sur-budget reste ≠ infaisable (SPEC §6).

**(3) L0b — pas d'anomalie quadratic.** Le LP quadratic à k=5 mesuré : **19 479 lignes / 49
colonnes**, **construit en 0,04 s, résolu en 0,32 s** ; le LP le plus lent sur un run ENTIER =
**1,32 s**. Le « >150 s » de S9e était le **run quadratic complet** (331 résolutions LP via le
lookahead `axis=margin`) sur la scène **LEAKY** (qui ne certifie à AUCUN degré — même cause qu'en
(1)). Sur la scène scellée, quadratic certifie aussi (PROOF, 4 feuilles, 7,9 s). *(DPAD effectif=4
piloté par `2·d_φ` ; cf. (4).)*

**(4) L1 — Bernstein anisotrope : NE PAIE PAS (mesuré, laissé en option non-défaut).** Degrés
PAR AXE des polynômes de face mesurés sur le bench (k=5,6,7) **ET sur la scène réelle S4** :
**UNIFORMES = 3 sur tous les axes actifs** (chaque joint rotoïde contribue degré 2 à N et D, +1
pour λ affine). ⟹ `∏(dᵢ+1) = 4^k = (3+1)^k` : **aucun gain anisotrope (ratio 1,00×)**. Le seul
levier de lignes est le **degré de φ** : le bench stocke φ (lacet, *linéaire*) à `phi_degree=2`
⟹ `2·d_φ=4` ⟹ DPAD effectif=4 ⟹ **5^k** ; φ tendu à son degré réel 1 ⟹ DPAD=3 ⟹ **4^k**, mesuré
**(5/4)^k de gain** (×3,0 à k=5 → ×4,8 à k=7, scènes toujours PROOF). C'est un **choix de
PARAMÈTRE de scène** (et il s'évanouit pour une barrière réellement quadratique), **pas**
l'anisotropie. L'anisotrope reste donc **non-défaut**.

**Position re-mesurée du mur** : *aucun mur du schéma affine en dims actives mesuré (k≤7 PROOF +
verify exact)*. La montée en dims actives coûte **(d+1)^k par LP** à feuilles quasi-constantes
(pour cette famille à barrière simple — *descripteur exact [A38-1] : barrière φ scalaire bas-degré +
dalle ; ce bench certifie le DERNIER link, toutes dims actives, donc PAS proximal*). La frontière est la **taille du LP
unique** (~470k lignes à k=7 ; ~2,3 M à k=8). **Verdict GO inchangé — re-sonde RENFORÇANTE** :
(a) la machinerie est SOUND (elle a refusé une non-déconnexion que l'échantillonnage déclarait
déconnectée — exactement règles 1/9) ; (b) le régime (d+1)^actif est confirmé, et le point
« une dim active au-dessus d'Henrion et al. » passe de k=4 à **k≥7** (avec la ceinture A37
« cadres différents ») ; (c) **S10 reste à piégeage PROXIMAL** (peu de dims actives) pour rester
sous la frontière LP. Les chiffres S9e du §3d restent l'historique (jamais réécrit) ; ce §3d-bis
porte le résultat.

---

## 4. Comparaison à Li-Dantam — positionnement, PAS une course

Chiffres **vérifiés à la source** (rule 9/A28) dans **Li & Dantam, « Scaling Motion Planning
Infeasibility Proofs », arXiv:2406.04795, 2024** (PDF lu cette session ; le journal antérieur
est **IJRR 2023**, SAGE 10.1177/02783649231154674 — *[à vérifier, A36] les deux références
existent et NE sont PAS le même papier : IJRR 42(10) 2023 (sampling-and-learning proofs, journal)
ET RA-L 8(12):8303-8310 2023 (triangulation de Coxeter, le prédécesseur DIRECT du GPU 2406.04795) ;
cf. docs/BIBLIO-ANTERIORITE.md. Ne pas « corriger » l'une en l'autre — A28 vaut dans les deux sens*) :

| | **Li-Dantam 2024 (arXiv:2406.04795)** | **certified-noplan (nous, S9d)** |
|---|---|---|
| DOF | 5-DoF & 6-DoF (Packbot, Universal robot, Schunk ; 4 scènes) | 5-6 DOF (bac iiwa-like, piège proximal) |
| Temps | **« les deux scènes 6-DoF prennent moins d'1 minute en moyenne »** (triangulation : secondes→dizaines de s ; collision : dizaines de s) | **5-DOF ≈ 1 s · 6-DOF ≈ 3,9 s** |
| Matériel | **NVIDIA GeForce RTX 4070 (12 Go) + Intel i9-13900K** | **laptop Apple Silicon, CPU pur, sans GPU** |
| Nature du certificat | manifold triangulé (Coxeter) sur GPU, **validé par collision-checker FLOTTANT** | **certificat algébrique Bernstein-LP, exactement re-vérifiable** par un programme indépendant en arithmétique rationnelle (verify.py, <500 l. stdlib) |
| Re-vérification a posteriori | aucune (confiance dans le pipeline flottant) | **oui, exacte** (la clé de crédibilité) |

**Caveats honnêtes (lignée « pas de ×400 »)** :
- **Pas de course apples-to-apples.** Scènes différentes (leurs Packbot/UR/Schunk vs notre
  bac proximal), objets prouvés différents (ils trianglent le manifold séparateur ; nous
  certifions une dalle-barrière), matériel différent (GPU vs CPU). On **NE revendique PAS**
  un facteur de vitesse (« 60 s / 3,9 s ≈ ×15 » serait malhonnête : notre scène exploite la
  passivité, la leur est possiblement plus dense en dims actives).
- **Ce qu'on revendique, prudemment** : on atteint **la même frontière DOF (5-6) que la
  méthode GPU de Li-Dantam, sur un laptop CPU sans GPU**, avec un certificat **d'une autre
  nature** — algébrique et **exactement re-vérifiable** (différenciation A26/D27, pas le DOF).
- Leur méthode scale par **parallélisme massif** (coût intrinsèque élevé absorbé par le GPU) ;
  la nôtre scale par **structure** (réduction aux dims actives). Les deux sont légitimes ; ce
  sont des leviers orthogonaux sur des problèmes différents.

---

## 5. Recommandation — **GO**

**GO vers S9b (portefeuille de cas d'usage) puis S10 (flagship 7-DOF).** Justification :

1. **G2′ vert avec 3 ordres de grandeur de marge** : 5-6 DOF certifiés PROOF, vérifiés exact,
   en secondes sur CPU, 8 feuilles, A32=0.
2. **Le levier qui porte la montée en DOF est mesuré et réel** : ×122 (global) et ×24,6
   (par-paire proximal) — la machinerie A18/A29/A30 transforme un coût (d+1)ⁿ en (d+1)^actif.
3. **L'insight de scope est solide ET borné [amendé A35]** : les déconnexions que NOTRE schéma
   certifie à BAS COÛT sont proximales (effet de sélection, §2) ⟹ peu de dims actives ⟹ le DOF
   total n'y est pas le driver de coût. **S10 doit choisir un flagship 7-DOF à piégeage PROXIMAL**
   (case haute d'étagère inatteignable, capot de sûreté) pour rester dans ce régime — c'est une
   **consigne de conception ET une limite de portée ASSUMÉE**, à énoncer telle quelle dans le
   papier : *le régime de coût est (d+1)^{dims actives} ; la classe proximale est notre portée
   à bas coût ; le régime à dims actives élevées est cher* (mesuré au §3d, bench du mur).
   *[supersédé par §3d-bis : pas de mur k≤7 ; frontière = taille du LP]*

**Caveats portés au dossier (pas des bloquants)** :
- La scène S4 est un **bac technique iiwa-LIKE documenté** (table A21 dans le YAML :
  FIDÈLE = chaîne/axes/limites usine ⊂(−π,π) ; CHOISI = offsets rationnels arrondis, frames
  inter-joints simplifiés, mur, locks). Le `spatial_revolute` ne porte pas les rotations
  constantes inter-joints de l'URDF iiwa exact — une reproduction URDF-fidèle exigerait soit
  une formulation POE, soit une extension de `verify.py` (sacré) : **à décider en S10/S11 si
  un reviewer l'exige** ; hors-scope d'un go/no-go technique.
  *[résolu (D47, 18/06) : iiwa réel faisable — spike FK rationnelle q\*=0 (rotations inter-liens =
  permutations signées ±90° ⟹ cos/sin rationnels ⟹ forme `verify.py` S9c, INTACT, ni POE ni
  extension) ; livré S10-bis comme flagship d'en-tête (A39)]*
- Box des joints actifs limité à ±70° (limite douce de cellule ⊂ limites usine ±120/±170°) :
  le théorème prouve la déconnexion **dans ce box**, affiché en degrés (A25). Honnête.
- Le régime à **dims actives élevées** (le risque d'explosion §9.1) est désormais **MESURÉ**
  (§3d, bench du mur, pilotage Stéphane) et non plus « non mesuré, probablement cher » :
  **certifié à bas coût jusqu'à k=4 dims actives (~0,36 s), mur du schéma affine à k=5**
  (UNDECIDED structurel ; coût/feuille ×≈5 par dim active). Un cas d'usage S9b exigeant une
  déconnexion à **≥5 dims actives** est donc le vrai point de pivot (re-scope avec Stéphane).

**SI la supervision juge ROUGE** : mitigations SPEC §9.1 (heuristique d'axe, sparsité, degré
témoin adaptatif) ; point de pivot journalisé ; re-scope décidé **avec Stéphane**.

---

## 6. Signatures

- [x] **Supervision (claude.ai)** — revue : revue S9e du 13/06/2026 (cf. JOURNAL)  date : 2026-06-13
- [x] **Stéphane Cambon** — SIGNATURE : Stéphane Cambon  date : 2026-06-13

Reproductibilité : `python scripts/calibrate_g2.py` (table §3) ;
`benchmarks/results/20260612T233416Z/` (timings canoniques, `calibration.json`) ;
`cnp certify scenes/S4_iiwa_bin.yaml` → PROOF ; `cnp verify <cert> scenes/S4_iiwa_bin.yaml` → OK.
