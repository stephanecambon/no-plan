# Infaisabilité certifiée haute-dimension par barrières SOS — note de reprise

*Résumé de ce qu'on a établi (avec démonstrations qui tournent) + plan de travail vers un papier. Écrit pour reprendre une session sans tout relire. Ton volontairement calibré : on distingue ce qui est **acquis** de ce qui est **pari de recherche**.*

---

## 1. Le problème et l'objectif

Planification de mouvement : pour un robot à N degrés de liberté (N-DOF), on veut **certifier rigoureusement qu'AUCUN chemin sans collision n'existe** entre une configuration de départ `q_start` et une configuration d'arrivée `q_goal`. C'est le problème de **l'infaisabilité prouvée** (infeasibility / disconnection proofs), le dual du planificateur classique : au lieu de trouver un chemin, prouver qu'il n'y en a pas.

**Le blanc sur la carte** qu'on vise : l'infaisabilité **rigoureuse ET haute-dimension**. Les méthodes rapides existantes sont *probabilistes* (pas de preuve dure) ; les méthodes *rigoureuses* existantes **plafonnent vers 4-DOF**. Personne n'a de preuve dure au-delà. C'est là qu'on attaque.

---

## 2. État de l'art (positionnement, vérifié sur le web cette session)

- **GCS** — Marcucci, Tedrake et al., *Shortest Paths in Graphs of Convex Sets*, Science Robotics 2023. Planification optimale multi-requêtes côté **libre**. Pas notre sujet direct mais même écosystème (Drake).
- **C-IRIS** — Dai, Amice, Werner, Zhang, Tedrake (IJRR). Certifie qu'une **cellule convexe est LIBRE** via SOS sur la **paramétrisation rationnelle** de la cinématique (demi-angle tangent `s = tan(θ/2)`). **Passe à l'échelle : 7-DOF (KUKA iiwa), 12-DOF (bi-bras).** Deux programmes : (23) hyperplan séparateur, (29) vacuité de l'intersection. **Les deux certifient le LIBRE.** Open-source dans Drake.
- **Preuves d'infaisabilité / déconnexion** :
  - Basch et al. 2001 (fondateur).
  - **McCarthy, Bretl, Hutchinson**, *Proving path non-existence using sampling and alpha-shapes*, ICRA 2012 — alpha-shapes dans `C_obs`, ≤3-DOF.
  - Varava et al. 2020.
  - **Li & Dantam** (le concurrent direct le plus proche) : variété séparatrice **apprise** (SVM) dans `C_obs`, puis **triangulée** (Coxeter), facettes vérifiées ⊂ `C_obs`. « Plan ou preuve sous hypothèses d'hyper-paramètres. » **Plafond ~4-DOF** car la triangulation explose exponentiellement en dimension. Sihui Li a soutenu (Mines, avril 2024), désormais prof à **Washington State University Tri-Cities** (lab RoPAL).
- **Méthodes rapides mais probabilistes** (pas de preuve dure) : IRIS-NP, IRIS-ZO, VCC. Elles ont gagné en vitesse en **abandonnant** la rigueur.

**Synthèse :** rigoureux ⟹ ≤4-DOF ; haut-DOF ⟹ probabiliste. Le croisement « rigoureux + haut-DOF » est vide. C'est notre cible.

---

## 3. Notre idée — le **dual de C-IRIS**

C-IRIS certifie qu'une cellule est **libre**. **Notre contribution : certifier qu'une cellule convexe est EN COLLISION**, puis **assembler ces cellules en une barrière séparatrice** qui prouve la déconnexion.

- **Dualité exploitée :** le certificat de C-IRIS « cellule libre » repose sur un **hyperplan séparateur** entre les deux corps `A(s)` et `B(s)`. Le dual logique de « il existe un hyperplan qui sépare » est « il existe un **point témoin** dans l'intersection `A(s) ∩ B(s)` » → preuve de collision. **Témoin ↔ hyperplan.**
- **Le gain structurel :** Li-Dantam construit une variété **fine triangulée** (→ mur des 4-DOF). Nous remplaçons ça par des **dalles épaisses certifiées SOS** (pas de triangulation) → on **hérite du scaling de C-IRIS** au lieu d'hériter du mur de la triangulation.

**Phrase-résumé de la contribution :** *remplacer la variété séparatrice apprise-et-triangulée de Li-Dantam (plafond 4-DOF) par des dalles de collision épaisses certifiées SOS (dual de C-IRIS), pour pousser l'infaisabilité rigoureuse vers 7-DOF.*

---

## 4. Ce qu'on a validé — démonstrations qui **tournent** (cvxpy 1.9.1 / CLARABEL+SCS, sympy 1.14, numpy, matplotlib)

Tous les scripts ont un **cas positif + un contrôle négatif** (soundness : ils **refusent** de certifier quand ce n'est pas vrai). `t*` = marge optimale ; `t* ≥ 0` ⟹ certificat valide.

### 4.1 Le certificat-témoin « en-collision » — **ACQUIS**
Cellule certifiée `⊆ C_obs` via un point témoin `x(s) = Σ_k λ_k(s)·v_k^A(s) ∈ A(s) ∩ B(s)`, coefficients SOS.
- `dual_sos.py` : témoin 2-DOF synthétique (sommets affines). Cellule serrée **certifiée** (`t*=+0.47`), cellule large **refusée** (`t*=−0.83`), sous-cellule **certifiée** (principe *subdiviser-pour-certifier*).
- `dual_sos_arm.py` : **vraie cinématique rationnelle** (bras planaire 2 segments, segment-2 vs obstacle), degré 6. Cellule serrée **certifiée** (`t*=+0.26`), large **refusée** (`t*=−0.66`).
- ⟹ Le dual de C-IRIS fonctionne, y compris sur cinématique réelle.

### 4.2 Le scaling — **le mur était un artefact** (clarifié après lecture de C-IRIS)
- Au départ : base monomiale **pleine** → explosion `C(2n+1, n)` (10 → 35 → … → 6435 à 7-DOF). Conclusion hâtive « match nul avec Li-Dantam à 4-DOF ».
- **Lecture de C-IRIS** (web_fetch arXiv 2302.12219 + 2205.03690) → révélation : (a) la FK rationnelle est **multilinéaire** (chaque variable de degré ≤2) ; (b) C-IRIS exploite le **choix de repère** : le coût est la **longueur de la chaîne cinématique entre les deux corps**, *pas* le DOF total. Leurs matrices PSD : **16 lignes @ 7-DOF, 64 @ 12-DOF**.
- `dual_sos_structured.py` : base structurée `{0,1}^n` (témoin **constant**) au lieu de la base pleine. À `n=4` : **16×16 / 1,6 s** (structuré) vs **70×70 / 92,7 s** (naïf). **Échec à `n=5`** (`t*=−0.086`) : un témoin *constant* est trop restrictif (un point fixe ne tient pas dans l'obstacle sur 5 articulations).
- **Compromis identifié :** témoin constant = petit SDP mais + de subdivision ↔ témoin **mobile** = SDP plus gros mais moins de subdivision. Le mur de scaling **n'est pas fondamental**.

### 4.3 Le certificat de déconnexion end-to-end — **ACQUIS (en 2-DOF)**
**Théorème (déconnexion par barrière).** S'il existe un polynôme `φ(s)` et `δ>0` tels que
1. `φ(q_start) ≤ −δ` et `φ(q_goal) ≥ +δ`, et
2. la **dalle** `{ s ∈ P_lim : φ(s)² ≤ δ² } ⊆ C_obs`,

**alors aucun chemin sans collision ne relie `q_start` à `q_goal`.** *Preuve :* théorème des valeurs intermédiaires — tout chemin continu passe par `φ=0`, qui est inclus dans la dalle, elle-même `⊆ C_obs`. La condition (2) est exactement notre **certificat-témoin** appliqué à la région `{ δ² − φ² ≥ 0 }` (contrainte de Putinar).
- `disconnection.py` : bras 2-link, obstacle au **bout du segment 1** bloquant `θ₁ ∈ [−0.49, +0.49]`, `C_free` **réellement scindé en 2 composantes**. `φ = s₁` ; dalle **certifiée en collision** (`t*=+0.09`) → **déconnexion prouvée rigoureusement**.

---

## 5. Statut honnête — ce qui manque pour le cas général 3D / N-DOF

**Soundness : acquise.** Un certificat = une preuve (pas de probabiliste caché). **On ne bat pas PSPACE** : la méthode est *sound* mais *incomplète*.

Par ordre de difficulté croissante, il manque :
1. **Trouver `φ`** (recherche de barrière) — non convexe, **dur**, partagé avec tout le monde (Li-Dantam le fait par ML). Notre apport **déplace** le goulot : de la triangulation vers la recherche de `φ`. *Idée à tester : utiliser C-IRIS pour couvrir les 2 composantes libres, repérer le « col » entre elles, ajuster `φ` là.*
2. **Barrière MULTI-PAIRES** — quand des paires de corps **différentes** bloquent des **endroits différents** de la dalle : il faut **partitionner** la dalle et **prouver le recouvrement complet** par les morceaux en collision. **C'est LE morceau neuf décisif (make-or-break).**
3. **3D / cinématique spatiale** — connu-faisable (C-IRIS le fait), mais **non implémenté** chez nous.
4. **Théorème de complétude dual** — analogue des Thm 3/4 de C-IRIS (sous quelles conditions le certificat existe-t-il si la scène est vraiment déconnectée ?).
5. **Solveur intégré + numérique à l'échelle** — Drake, Mosek, conditionnement des SDP à 7-DOF.

**Est-ce déjà un papier ?** Non : c'est le **squelette + une proposition solide**. Il manque un **résultat haute-DOF qui batte Li-Dantam** (le témoin constant a *échoué* à 5-DOF), la recherche de `φ`, le multi-paires, la 3D, le théorème, et un benchmark.

---

## 6. Plan de travail (vers le papier)

**Cible :** « Preuves d'infaisabilité certifiées haute-DOF par barrières de collision SOS ». **Venue :** RA-L, ou WAFR / ICRA.
**Chaque phase a une porte go/no-go.** Veille continue en parallèle : *« quelqu'un publie-t-il déjà ça ? »* (surveiller Tedrake/Amice/Werner dans Drake, et Dantam/Li).

- **Phase 0 — Infra & reproduction.** Installer Drake. Reproduire C-IRIS (cellules libres 2-DOF puis 7-DOF). **Réimplémenter le certificat-témoin dans Drake.**
  - **Porte G0 :** le SDP du témoin fait ~quelques **dizaines** de lignes (pas des milliers) sur cinématique réelle. ← valide que le scaling tient hors du bac à sable jouet.
- **Phase 1 — Dalle MULTI-PAIRES (RISQUE n°1).** Certifier une dalle où plusieurs obstacles/paires bloquent des zones distinctes ; prouver le recouvrement complet.
  - **Porte G1 :** dalle multi-obstacles certifiée **entièrement** `⊆ C_obs` à 3-4 DOF. **Si ça casse, le projet casse.**
- **Phase 2 — Trouver `φ` (RISQUE n°2).** Via couverture C-IRIS des composantes libres + détection du col.
  - **Porte G2 :** `φ` fiable sur scènes déconnectées 3-5 DOF.
- **Phase 3 — 3D / spatial.** Cinématique spatiale, paires de corps 3D.
- **Phase 4 — RÉSULTAT-TITRE + benchmark.** Infaisabilité prouvée à **5-7 DOF**, **battant le plafond 4-DOF de Li-Dantam**.
  - **Porte G4 :** c'est **la thèse du papier**. Sans ça, pas de papier fort.
- **Phase 5 — Théorème de complétude dual** (bonus, en parallèle).
- **Phase 6 — Rédaction + soumission.**

---

## 7. Réalités à garder en tête (calibrage)

- **Le calendrier est gouverné par le risque de recherche, pas par l'effort.** Les phases 1 et 2 sont des **problèmes ouverts** : l'intuition tombe… ou jamais. Ma vitesse (Claude) **comprime l'ingénierie et la rédaction à des heures de session**, mais elle ne change **ni** la probabilité que l'idée marche, **ni** le besoin de **vrai calcul** (SDP 7-DOF / Drake / Mosek / GPU — au-delà du bac à sable de cette session), **ni** le besoin de **vérification humaine** (mon output peut être plausible *et faux*, surtout sur du neuf).
- **Je ne persiste pas seul.** Travail en sessions, piloté par Stéphane. Pas de « Claude mène le projet seul pendant des mois ».
- **Compétition réelle :** Tedrake/Amice (C-IRIS dans Drake) et Dantam/Li. Publier une demi-version est **risqué** (ils exécuteraient la version complète plus vite). → arbitrer entre vitesse et complétude au moment de G4.
- **Recommandation forte :** recruter **un collaborateur fluent en Drake**. Il n'est pas là pour taper (Claude le fait) mais pour le **calcul/labo** et surtout la **vérification**. La présente proposition peut servir d'**outil de recrutement**.

---

## 8. Références clés (à recroiser)

- **C-IRIS** : Dai, Amice, Werner, Zhang, Tedrake, *Certified Polyhedral Decompositions of Collision-Free Configuration Space*, IJRR — **arXiv 2302.12219**. Version conférence : Amice et al., WAFR 2022 — **arXiv 2205.03690**. Programmes (23) hyperplan, (29) vacuité. Code dans **Drake**.
- **Li & Dantam** : *A sampling and learning framework to prove motion planning infeasibility*, IJRR 2023. *Scaling Motion Planning Infeasibility Proofs* — **arXiv 2406.04795** (ICRA 2024). *Incremental Sampling and Segmentation-Based Approach…* — **arXiv 2501.11434** (2025). Thèse S. Li, Mines 2024 ; aujourd'hui **WSU Tri-Cities, lab RoPAL**.
- **McCarthy, Bretl, Hutchinson**, *Proving path non-existence using sampling and alpha-shapes*, ICRA 2012.
- **GCS** : Marcucci et al., *Shortest Paths in Graphs of Convex Sets*, Science Robotics 2023.
- **Fondations SOS** : Blekherman, Parrilo, Thomas, *Semidefinite Optimization and Convex Algebraic Geometry*. **Positivstellensatz de Putinar** ; Psatz de vacuité (Parrilo).

*(IDs arXiv issus des recherches de cette session — à revérifier au moment de citer.)*

---

## 9. Scripts produits — **à régénérer** (le filesystem ne persiste pas entre sessions)

Tous en Python (cvxpy + sympy + numpy + matplotlib), avec cas positif + contrôle négatif :
1. `dual_sos.py` — témoin 2-DOF synthétique (sommets affines). Démontre subdiviser-pour-certifier.
2. `dual_sos_arm.py` — **cinématique rationnelle** réelle (bras 2-link), degré 6.
3. `dual_sos_scaling.py` — probe scaling 2 vs 3-DOF (montre l'explosion de la base naïve).
4. `dual_sos_structured.py` — **base multilinéaire `{0,1}^n`** vs base pleine (16×16/1,6 s vs 70×70/92,7 s à n=4 ; échec témoin constant à n=5).
5. `disconnection.py` — **certificat de déconnexion end-to-end** (bras 2-link, `C_free` scindé, `φ=s₁`, dalle certifiée, `t*=+0.09`).

---

## 10. Les deux formulations à garder sous la main

**Certificat-témoin (cellule `Q ⊆ C_obs` pour la paire de corps `A,B`).**
Trouver des multiplicateurs SOS `λ_k(s) ≥ 0` sur `Q`, avec `Σ_k λ_k(s) = 1`, tels que le point
`x(s) = Σ_k λ_k(s)·v_k^A(s)` (combinaison convexe des sommets de `A(s)`)
appartienne à `B(s)` pour tout `s ∈ Q` (chaque inégalité de demi-espace de `B` certifiée SOS sur `Q`), en maximisant une marge `t`. **`t* ≥ 0` ⟹ `Q ⊆ C_obs`.** C'est le **dual** du certificat « cellule libre » de C-IRIS (témoin ↔ hyperplan séparateur).

**Théorème de déconnexion.** `∃ φ` polynôme, `∃ δ>0` :
(i) `φ(q_start) ≤ −δ`, `φ(q_goal) ≥ +δ` ; (ii) `{ s ∈ P_lim : δ² − φ(s)² ≥ 0 } ⊆ C_obs` (certifié par (le) certificat-témoin ci-dessus).
**⟹ aucun chemin sans collision.** Preuve par les valeurs intermédiaires.

---

*Prochaine session : commencer par la **Phase 0** (Drake + reproduire C-IRIS + réimplémenter le témoin) puis foncer sur **G1 (multi-paires)** — c'est le verrou qui décide si le papier existe.*

---
---

# ADDENDUM — Session 2 (10 juin 2026) : challenge, nouvelles expériences, plan révisé

## A. Révisions issues du challenge (toutes intégrées ci-dessous)

1. **Le témoin n'est pas la contribution** (trop naturel, « exercice dual de C-IRIS » pour un reviewer ; IRIS-NP trouve déjà des *points* de collision). La valeur = multi-paires + résultat haut-DOF + théorème. Vendre le papier sur l'assemblage, pas la dualité.
2. **Hypothèse wrap-around à rendre explicite** : s=tan(θ/2) ⟹ limites articulaires dans (−π,π) requises, sinon un chemin contourne la barrière. Même hypothèse que C-IRIS, mais elle doit figurer dans l'énoncé du théorème.
3. **G1 reformulé** : partition de la dalle **par découpes** (boîtes) ⟹ recouvrement **vrai par construction**, rien à prouver. Le risque devient le **nombre de cellules** (coût), plus l'existence d'une preuve de couverture. **Validé expérimentalement (E3).**
4. Empilement de conservatismes (degré du témoin, SOS⊊positif, dalle entière dans C_obs) : réel, à quantifier, pas disqualifiant.
5. Sans recherche de φ on a un **vérificateur**, pas un algorithme ⟹ piste hybride **Li-Dantam front-end (φ appris) + notre back-end certifié** promue plan A de la Phase 2.
6. Théorème de complétude asymptotique probablement **prouvable** (robustesse ⟹ fonction séparatrice continue ⟹ Stone-Weierstrass ⟹ Putinar) : promu composante du papier.
7. Veille session 2 : rien trouvé sur « certificat de collision paramétré » ni description **positive certifiée de C_obs** (Amice : positive = C_free ; négative = C_obs, non certifiée). Créneau ouvert. **À ajouter à la veille : analyse par intervalles / SIVIA (Jaulin) et littérature Bernstein-certificats** — proche parente de E2 ci-dessous, vérifier qu'elle n'a pas déjà été appliquée aux preuves d'infaisabilité C-space.

## B. Expériences session 2 (scripts : toolkit.py, e1_affine.py, e1b_setup.py, e2_bernstein.py, e3_multipair.py)

### E1 — Témoin affine vs constant (le « milieu » jamais testé)
- n=4 : constant certifie (t*=+0.0934, 16×16, 2.7 s) ; **affine n'apporte rien** (t*=+0.0935, 48×48, 36 s).
- n=5, cellule où le constant échoue (t*=−0.086) : affine **base complète tué (mémoire, base 112)** ; **1 bissection insuffisante** (t* = −0.008/+0.021 selon l'axe) ; **bissection croisée s₁×s₂ → 4 quadrants × témoin constant : TOUS certifiés** (t* ∈ [+0.058, +0.097], 4 SDP de 32×32, ~11 s chacun ; un solve `optimal_inaccurate`, à refaire avec Mosek/précision).
- **Conclusion : le compromis se résout par SUBDIVISION (témoin constant par morceau), pas par montée en degré.** Première cellule 5-DOF certifiée en collision (SOS).

### E2 — Bernstein + branch-and-bound : certification SANS SDP ★ résultat majeur
Pipeline : par feuille, LP au centre → témoin constant x₀ ; vérification rigoureuse `p_i·D − N_i·x_num ≥ 0` sur la feuille par **positivité des coefficients de Bernstein** (FK degré ≤2/variable → tenseurs 3^n, conversions exactes par axe) ; échec → bissection de l'axe le plus large. Soundness : refus du contrôle négatif (cellule 21% collision → refuted en 0.01 s par point libre).
- **n=5 : certifié en 0.07 s (4 feuilles)** — la même cellule coûtait 44 s en SOS (≈600×).
- n=6/7 première tentative : NON certifié **à raison** (vérité 99%/95% : mes cellules avaient des configs libres — la soundness a attrapé mon erreur de scène).
- Scène honnête (obstacle h=0.60/0.70, cellules ±0.05/±0.04, vérité 100%) : **n=6 certifié en 0.08 s (4 feuilles), n=7 certifié en 0.06 s (2 feuilles)**.
- **⟹ Cellules en collision certifiées à 7-DOF, au-delà du mur Li-Dantam, en millisecondes, zéro SDP.**
- Caveats honnêtes : bras planaire, une paire par certificat, cellules en collision *profonde* (le coût explosera près de ∂C_obs — c'est le nombre de feuilles qui devient la métrique) ; rigoureux **modulo flottant** (version publiable : arithmétique rationnelle/intervalle) ; la FK symbolique (sympy) devient le goulot (23 s à n=7, 3^n coefficients) → pipeline FK à industrialiser ; **nouveauté à vérifier en veille** (Bernstein/intervalles en C-space existent en basse dimension, p.ex. SIVIA).

### E3 — Barrière multi-paires par partition-construction (G1 reformulé) : VALIDÉ à 2-DOF
Scène 2-link, **deux obstacles** U (haut) et Dn (bas), centres mid_at(±0.8), demi-côté 0.30, limites |θᵢ|≤1.2, dalle |θ₁|≤0.10 (φ=s₁, δ_s=0.05).
- Vérité-terrain : chaque cellule 100% en collision **avec sa paire** ; la mauvaise paire ne couvre que **84%** ⟹ multi-paires réellement nécessaire (1ʳᵉ géométrie était dégénérée — corrigée ; toujours faire ce contrôle).
- Partition : coupe à s₂=0 → cell_up ∪ cell_dn = dalle (recouvrement **par construction**).
- Certification : **Bernstein 6 feuilles / 0.07 s par cellule** ; recoupement **SOS t*=+0.0155** les deux.
- Endpoints libres vérifiés (2 links × 2 obstacles), φ(q_start)=−0.483 ≤ −δ_s, φ(q_goal)=+0.483 ≥ +δ_s.
- **⟹ DÉCONNEXION PROUVÉE par barrière multi-paires.** Figure : multipair_disconnection.png.

## C. Plan révisé v2 (remplace le plan v1 §6 là où ça diffère)

- **Le moteur pratique devient Bernstein-B&B** (témoin constant par feuille) ; **SOS reste pour la théorie** (complétude via Putinar) et comme certificat de recoupement. Conséquence énorme : **la dépendance Mosek disparaît probablement** du chemin critique ; Drake reste utile pour la cinématique 3D/scènes réalistes, pas pour les SDP.
- **Prochain jalon (fusion E2+E3)** : barrière multi-paires Bernstein à **5-7 DOF** sur une scène réellement déconnectée — c'est devenu le candidat « résultat-titre » atteignable AVANT la 3D. Métriques : nombre de feuilles, profondeur, temps vs DOF, et comportement près de ∂C_obs.
- **Phase 2 (φ)** : plan A = hybride Li-Dantam (φ appris SVM → fit polynomial → dalle certifiée Bernstein) ; plan B = couverture C-IRIS + détection du col.
- **Phase 3 (3D/spatial)** : FK rationnelle spatiale (quaternions/Cayley 3D), pipeline FK numérique (remplacer sympy).
- **Théorème** (complétude asymptotique sous robustesse) : à rédiger, ingrédients standards.
- **Rigueur publiable** : passer la vérification Bernstein en arithmétique rationnelle exacte (les coefficients FK sont rationnels) — coût modeste, gain décisif.
- Portes : **G1' = barrière multi-paires Bernstein certifiée à 5-DOF sur scène déconnectée non triviale** (le jalon fusionné) ; G2 = φ automatique fiable ; G4 = benchmark 5-7 DOF vs Li-Dantam (leur scènes si reproductibles).

## D. État des risques (mise à jour)

| Risque | v1 | v2 |
|---|---|---|
| Formulabilité/soundness du témoin | retiré | retiré |
| Cinématique rationnelle réelle | retiré | retiré |
| Scaling SDP | artefact de base, retiré | **contourné** (Bernstein, 7-DOF en ms) |
| Multi-paires (G1) | make-or-break | **reformulé + validé 2-DOF** ; reste : coût en feuilles à haut DOF |
| Recherche de φ | ouvert | ouvert, dérisqué par l'hybride Li-Dantam (plan A) |
| 3D/spatial | connu-faisable | connu-faisable ; goulot = pipeline FK |
| Nouveauté | créneau ouvert (veille 2×) | idem + **vérifier Bernstein/intervalles C-space** (SIVIA, Jaulin) |
| Rigueur numérique | conditionnement SDP | flottant → **arithmétique rationnelle** (faisable) |

