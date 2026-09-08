# Portefeuille de cas d'usage — trois propositions de valeur du MÊME certificat

> **✅ ÉTAT AU 8 SEPTEMBRE 2026 (S11) — LES TROIS CAS SONT CERTIFIÉS SUR LE VRAI KUKA iiwa7.**
> `PROOF` + `cnp verify` **OK en arithmétique exacte** + cross-check de scène + **A32 = 0** pour
> les trois. Ce document n'est plus un portefeuille de *specs* : c'est un pack de *preuves*.
> (Le corps du document ci-dessous garde le cadrage S9b — conception produit — pour la trace ;
> les chiffres réels sont dans le tableau « État certifié » et dans les trois one-pagers.)

## État certifié (S11)

| Cas | Scène (vrai iiwa7) | Verdict | Feuilles | `verify` exact | `certify` (prédit A44) | Marges franches | Bench daté |
|---|---|---|---|---|---|---|---|
| **Étagère pharma** ⭐ *(flagship d'en-tête)* | `scenes/S6_iiwa_real_shelf.yaml` | **PROOF** | 2 | ✅ 3,79 s | 726 s | +91,5 / +83,3 mm | `20260908T121907Z` |
| **Bin-picking logistique** | `scenes/usecase_binpicking_iiwa7.yaml` | **PROOF** | 2 | ✅ 2,45 s | 567 s (~620 s, −9 %) | +66,9 / +71,7 mm | `20260908T150151Z` |
| **Capot de sûreté** | `scenes/usecase_capot_surete_iiwa7.yaml` | **PROOF** | 4 (2 coll. + 2 hors-dalle) | ✅ 2,54 s | 498 s (~620 s, −20 %) | +83,1 / +85,3 mm | `20260908T151019Z` |

Communs aux trois : **7 axes réels** (chaîne gelée fidèle à l'URDF iiwa7 à ~2e-6), **corps certifié
= lien 3** avec sa **silhouette convexe fidèle à 40 sommets** (~1,7e-6), **dims actives {0,1,2}
RE-MESURÉES** (les 4 joints distaux sont *prouvés* passifs — la redondance ne dégage pas le corps),
LP de feuille **1 070 lignes** réduit contre **473 870** en pleine dimension (**×442,9**),
vérité-terrain dense par l'**oracle corps-convexe** (0 libre / 40 000 dans la dalle, 0 / 448 coins,
invariance de redondance, libre des deux côtés).

### Le mécanisme est commun — et c'est un RÉSULTAT mesuré, pas un raccourci

Avant d'écrire la moindre scène, `scripts/measure_iiwa7_lever.py` a mesuré le **levier par joint
actif** sur le vrai lien 3 : **3 axes actifs × 6 directions × 2 motifs d'obstacle** (demi-espace
« plafond » et plaque « paroi à traverser »).

| séparateur | meilleure marge franche | verdict |
|---|---|---|
| **`s1` = q2, tangage d'épaule + obstacle en SURPLOMB** | **+174,8 mm** | **le seul franc** |
| `s0` = lacet de base | **négatif dans les 6 directions** (−73 à −299 mm) | mort |
| `s2` = q3, roulis du bras | négatif partout | mort |
| motif « traverser une paroi verticale » | négatif partout | mort |

Le corps proximal réel est un **blob compact** ancré à l'épaule : il tourne sur lui-même sans se
déplacer (d'où la mort du lacet de base — le finding A43 de S10-ter, ici quantifié), et il ne peut
**jamais** se retrouver entièrement d'un côté d'une paroi verticale. Sur ce robot et ce lien, le
piège proximal franc **est unique**. Les trois cas partagent donc la mécanique et se différencient
par la **géométrie de l'obstacle** (étagère en surplomb / bac empilé / capot mince et large), les
**limites**, la **dalle**, les **poses**, le **récit** et le **claim**. C'est exactement la thèse
« **une seule machinerie, trois marchés** » énoncée plus bas — et on le dit plutôt que de le
maquiller.

---

Session **S9b** (trace d'origine) : conception produit (spécification + storyboard), **pas de
preuve** (aucun run de certification long, aucun `make_certificate` là). Chaque cas était livré au
niveau (a) one-pager calibré · (b) spec YAML chargeable · (c) sanity-check de **plausibilité** (pas
une certification) · (d) storyboard + ≥1 figure · (e) critères d'acceptation S10/S11.

**Cadre S9f (frontière re-mesurée) — ce qui calibre le choix.** Il n'y a **pas de mur affine
k≤7** : la montée en dims actives coûte `(d+1)^k` **par LP unique** à feuilles quasi-constantes, et
la frontière pratique est la **taille du LP** (~470k lignes à k=7, PROOF en ~95 s ; k=8 ~2,3 M
lignes au-delà d'une deadline laptop). **Conséquence** : un piège **proximal** (~3 dims actives,
LP minuscule, ~8 feuilles, secondes) est **trivialement sous la frontière**. Le flagship n'a donc
plus à être proximal *par contrainte de faisabilité* — il l'est *par pertinence* (les vrais cas le
sont). **Le critère de choix devient le RÉCIT et la VALEUR, pas la faisabilité technique.**

---

## Tableau comparatif

| Cas | DOF total | Dims actives (est.) | Corps certifié | Proposition de valeur | Secteur Cambon AI | Force du certificat (attendue) | Difficulté de conception de scène |
|---|---|---|---|---|---|---|---|
| **Bin-picking logistique** | **6** | **3** `{0,1,2}` | link 2 (épaule-coude) | **Élagage PROUVÉ d'une branche TAMP** : timeout → nœud `INFEASIBLE` certain | Logistique / intralogistique | PROOF + `verify` exact, k=3 ⟹ ~8 feuilles, **secondes** | **Faible** (piège proximal type S4) |
| **Étagère pharma** ⭐ | **7** | **3** `{0,1,2}` | link 2 (épaule-coude) | **Portée 7-DOF certifiée**, *robuste à la redondance* (la redondance n'aide pas) | Santé / pharma-logistique | PROOF + `verify` exact, k=3 ⟹ **secondes** | **Faible-moyenne** (7-DOF, redondance = le point ; 4 joints distaux passifs) |
| **Capot de sûreté · fenêtre opérateur** | **7** | **3** `{0,1,2}` | link 2 (épaule-coude) | **Certificat exact RECOMPTABLE** : l'auditeur re-vérifie (vs « croyez le pipeline ») | Sûreté / réglementaire | PROOF + `verify` exact, k=3 ; **recomptabilité = la valeur** | **Faible-moyenne** (capot large, déconnexion nette) |

Plausibilité vérifiée pour les trois (seedé, `scripts/usecase_sanity.py`) : start/goal libres ·
**0 libre dans la dalle** (30 000 uniformes **ET** 30 000 biaisés-coins, leçon S9f) · **libre des
deux côtés**. Les trois **parsent** et `cnp show … --interactive` fonctionne. Figures C-space
livrées dans `benchmarks/figures/S9b_usecases/`.

### Lecture du tableau (honnête)

- **Cœur kinématique commun = une FORCE, pas une redite.** Les trois instancient le **même piège
  proximal** (corps proximal link 2, ~3 dims actives, 4-3 joints distaux prouvés passifs) : *une
  seule machinerie, trois marchés*. C'est exactement « **trois propositions de valeur du même
  certificat** » (CLAUDE.md S9b). La différenciation est le **récit / la valeur / le secteur**, pas
  la kinématique.
- **Pourquoi tous à 3 dims actives ?** C'est la **classe à bas coût** de notre schéma (effet de
  sélection A35 : un corps proximal piégé ⟹ peu de joints actifs). Des déconnexions à dims actives
  élevées (k=4..7) sont **mesurées PROOF en S9f**, mais coûtent davantage par LP — on les garde en
  **future work** plutôt que de les forcer dans une vitrine.
- **Note de conception (résultat, pas échec)** : une variante **4 dims actives** (piège sur
  l'avant-bras, link 3) a été tentée pour le capot ; le scellement à la main est **fiddly** (les
  joints de tangage balaient large, la séparation gauche/dalle/droite n'est pas franche). Conforme
  à S9f : le régime k≥4 est faisable mais demande un scellement soigné (bornes de Bernstein,
  `build_scene_sealed`) — réservé à S10/S11, pas à un storyboard. La version livrée reste à k=3.

---

## Recommandation ARGUMENTÉE du flagship S10 — **Code recommande : Étagère pharma (7-DOF)**

> **Stéphane TRANCHE le flagship ; Code recommande.** Critère = **récit + valeur** (la faisabilité
> d'un piège proximal est acquise pour les trois d'après S9f).

**Recommandation : `étagère pharma` (7-DOF, piégeage proximal, 3 dims actives).** Quatre raisons :

1. **Le récit le plus contre-intuitif, donc le plus démonstratif.** « Un bras **redondant** à 7
   axes ne peut PAS atteindre ce casier — et la redondance, qui *devrait* aider, n'y change rien. »
   C'est la mise en scène directe de notre insight technique (A35 : la barrière **proximale** n'est
   pas défaite par la redondance, contrairement à une barrière distale). Un certificat n'a de
   valeur que s'il **réfute une intuition forte** ; ici l'intuition (« 7 axes trouveront un
   chemin ») est maximale.

2. **Il vise la porte G4' / la Definition of Done telles qu'écrites.** La DoD et S10/V6
   pointent déjà un **flagship 7-DOF d'étagère** (`scenes/S5_iiwa_shelf.yaml`, « case haute
   inatteignable »). Recommander l'étagère pharma **aligne** le portefeuille sur le jalon déjà
   anticipé *(fait en S10 : `usecase_etagere_pharma.yaml` → `scenes/S5_iiwa_shelf.yaml`)*.

3. **La valeur la plus directement monétisable et explicable à un non-spécialiste.** « Enveloppe
   de portée **certifiée** (pas échantillonnée) pour dimensionner une cellule » se vend en une
   phrase à un intégrateur ; c'est la matière commerciale Cambon AI la plus immédiate.

4. **Le meilleur showcase de « la montée en DOF est quasi gratuite sur la classe proximale ».**
   7-DOF *réels* (tous joints libres) mais **3 dims actives** ⟹ secondes, sous la frontière LP
   S9f. C'est précisément le message de portée à porter au papier (`(d+1)^{dims actives}`).

**Les deux autres → S11 (pack démo, D24)**, comme les deux autres propositions de valeur du même
certificat :
- **Bin-picking logistique** : la plus « produit » (élagage TAMP, cœur de SPEC §6) — fort candidat
  si la priorité commerciale est la **logistique** ; réserve : **6-DOF**, il ne couvre pas la porte
  **7-DOF** (G4'/DoD) — d'où le rôle de complément, pas de flagship.
- **Capot de sûreté** : la plus « confiance » (recomptabilité, dossier de sûreté) — fort candidat
  si la priorité est la **différenciation par la NATURE du certificat** (A26) ; 7-DOF également.

**Si Stéphane préfère un autre flagship** : `capot de sûreté` est le second choix naturel (même
7-DOF, argument auditabilité fort) ; `bin-picking` exigerait d'assumer un flagship **6-DOF** (sous
la cible G4' 7-DOF) ou de le porter à 7-DOF.

---

## Gate (validation VUE — fin de S9b) — *acquise*

Validée par Stéphane en S9b ; flagship désigné = **étagère pharma**. Les deux autres cas ont été
certifiés en **S11** (tableau « État certifié » en tête).

## Artefacts du pack démo (S11)

| Artefact | Où |
|---|---|
| **3D partageable** (un fichier `.html`, ouvrable sans Python ni serveur, orbite souris, balayage start→goal, corps certifié surligné + légende A40) | `benchmarks/figures/share/*_3d.html` |
| **Interactif A24** (7 curseurs, corps = coque 40 sommets, collision GJK ≡ oracle, fantômes, boutons d'évasion) | `benchmarks/figures/S11_usecases/*_interactive.html`, `benchmarks/figures/S10_real_flagship/S6_real_shelf_interactive.html` |
| **Figures** C-space · sweep fidèle · **partition slab-aware** (plein = prouvé, hachuré = hors-dalle où le théorème ne dit rien, A11) | `benchmarks/figures/S11_usecases/`, `benchmarks/figures/S10_real_flagship/` |
| **Composite Figure 1** du papier (rendu 3D + coupe C-space + encadré de chiffres lus dans les JSON de bench) | `benchmarks/figures/paper/fig1.png` |

Tous les artefacts qui portent un ARGUMENT sont adossés à un **invariant testé** (règle 11 / A40) :
`tests/test_viz_partition.py` (le plein ne peut pas sortir de la dalle et ne peut pas contredire
l'oracle), `tests/test_share_3d_html.py` (le corps dessiné est celui du certificat ; le verdict de
collision affiché est celui de l'oracle), `tests/test_flagship_real_interactive.py` (la collision
JS reproduit l'oracle, 0 écart / 694 configurations).

Détail des cas : [`binpicking.md`](binpicking.md) · [`etagere_pharma.md`](etagere_pharma.md) ·
[`capot_surete.md`](capot_surete.md).
