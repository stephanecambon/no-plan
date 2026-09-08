# Cas d'usage — Bin-picking logistique : élagage PROUVÉ d'une branche TAMP infaisable

> **Un planificateur qui ÉLAGUE avec une preuve, pas un planificateur qui ABANDONNE sur un
> timeout.** « Ce colis est inatteignable sans retirer d'abord la caisse du dessus » — prouvé,
> pas supposé.

> **✅ CERTIFIÉ (S11, 8 septembre 2026) sur le VRAI KUKA iiwa7.** `PROOF` + `cnp verify` **OK en
> arithmétique exacte** + cross-check de scène, **A32 = 0**. Scène
> [`scenes/usecase_binpicking_iiwa7.yaml`](../../scenes/usecase_binpicking_iiwa7.yaml),
> certificat [`scenes/usecase_binpicking_iiwa7.cert.json`](../../scenes/usecase_binpicking_iiwa7.cert.json).
> **Montée en gamme assumée par rapport à la spec S9b** : le cas était spécifié sur un cobot
> 6 axes générique à corps-SEGMENT ; il est livré sur le **vrai iiwa7 7 axes**, cinématique
> fidèle à l'URDF à ~2e-6 et **silhouette convexe fidèle du lien 3** (40 sommets, ~1,7e-6). Le
> récit TAMP ne dépend pas du nombre d'axes ; la spec générique 6 axes reste au repo
> ([`scenes/usecase_binpicking.yaml`](../../scenes/usecase_binpicking.yaml)).

---

## 1. Secteur & persona (qui paie)

- **Secteur Cambon AI : logistique / intralogistique** (dépalettisation, préparation de
  commandes, vidage de bacs profonds).
- **Qui paie** : l'éditeur (ou l'intégrateur) d'un **planificateur TAMP** (task-and-motion) de
  bin-picking, dont le coût opérationnel est dominé par les **branches explorées en vain**. Un
  oracle d'infaisabilité **certain** sur une branche = du temps de planification (et du temps de
  cycle robot) économisé à chaque pièce.

## 2. Le récit (scène — apparence FAISABLE, A20)

Poste de prélèvement à **rack deux niveaux**. Le colis cible est au **FOND d'un bac du niveau
BAS**, dans la baie de droite ; le bras (KUKA iiwa7, 7 axes) est au repos au-dessus de la baie de
gauche. Un **bac plein est rangé au niveau HAUT**, juste au-dessus de l'épaule du robot. Le
planificateur TAMP ouvre la branche : *« saisir le colis dans le bac du bas SANS dépiler »*. Le
colis est **visible et proche** ; l'espace a l'air dégagé de tous côtés (apparence faisable, A20).
Sans preuve, le planificateur **essaie** : il échantillonne des milliers de configurations IK +
chemins, et finit en **timeout** — sans jamais savoir si la branche était *infaisable* ou seulement
*difficile à échantillonner*.

**Le mécanisme, mesuré et non supposé.** Pour passer de la baie gauche à la baie droite, le tangage
d'épaule `q2` doit **changer de signe**, donc passer par `q2 ≈ 0` : le bras se **redresse**. C'est là
que le **segment proximal** (lien 3) percute le bac du niveau haut. Et **aucun** des 4 joints
distaux ne l'en sort : ils sont géométriquement en aval du lien 3, donc **prouvés passifs** pour
cette paire. La redondance ne sert à rien — c'est le cœur du résultat.

## 3. Claim CALIBRÉ — ce que le certificat prouve, et ce qu'il ne prouve PAS

**PROUVE** : *dans les limites articulaires affichées* (actifs **±62°**, distaux **±143°** ⊂
limites usine iiwa7), **aucun chemin continu sans collision** ne fait changer de signe au tangage
d'épaule `q2` — la dalle `|φ| ≤ 3/20` est **entièrement en collision** entre le corps proximal
certifié (lien 3, silhouette convexe fidèle à 40 sommets) et le bac du niveau haut,
**indépendamment des 4 joints distaux**. Start et goal sont donc dans **deux composantes libres
distinctes**. Preuve **algébrique exacte**, recomptable (`cnp verify`, <500 l., stdlib seule,
sans importer le générateur).

**NE PROUVE PAS** :
- **pas** que le colis est infaisable *en soi* — seulement **par cette approche, dans ces
  limites** (retirer la caisse du dessus, ou dépiler, change le problème — c'est exactement
  l'action que le certificat justifie) ; **UNDECIDED ≠ infaisable** (SPEC §6) ;
- **pas** un gain de vitesse chiffré vs un planificateur du marché (pas de ×N) ;
- **pas** une portée illimitée en dims actives : régime `(d+1)^k` (S9f), ici k=3 ;
- **pas** « le iiwa exact » : la fidélité physique est plafonnée par la précision de l'URDF
  publié (~2e-6 mesuré, A41). Le **modèle interne**, lui, est exact — `verify` recompte en
  `Fraction`.

## 4. Proposition de valeur PROPRE à ce cas

**Transformer un timeout en élagage.** La valeur n'est pas « le robot ne peut pas » — c'est
**« le PLANIFICATEUR peut couper cette branche, avec une preuve, et passer à la suivante »**. Là
où l'échantillonnage ne produit *jamais* de « non » certain (absence de preuve ≠ preuve
d'absence), notre certificat fournit l'**infaisabilité certifiée** qui manque à la boucle TAMP :
un nœud `INFEASIBLE` prouvé, pas un nœud `UNKNOWN` abandonné sur budget. C'est l'argument-cœur du
démonstrateur (SPEC §6 : « élaguer une branche infaisable d'un arbre TAMP »), instancié sur la
scène la plus banale du secteur.

## 5. Scène, mesures et certificat (RÉSULTATS, plus une plausibilité)

- **Scène** : [`scenes/usecase_binpicking_iiwa7.yaml`](../../scenes/usecase_binpicking_iiwa7.yaml)
  — vrai iiwa7 7 axes (`spatial_revolute`, chaîne gelée), corps certifié = **lien 3**, coque
  convexe fidèle **40 sommets**, obstacle `CRATE_ABOVE` (bac du niveau haut, empreinte euro
  600×400, hauteur 220 mm) en **H-rep exacte** (étanche par construction).
- **Piégeage proximal RE-MESURÉ** (jamais présumé, `engine.pair_views`) : dims actives
  **{0,1,2}** ; **j4…j7 prouvés passifs** pour la paire.
- **Pourquoi ce séparateur** : `scripts/measure_iiwa7_lever.py` a mesuré le levier **avant**
  d'écrire la scène — 3 axes actifs × 6 directions × 2 motifs d'obstacle. Sur le vrai lien 3
  (blob compact ~0,13 m), **seul** « tangage `q2` + obstacle en surplomb » est franc
  (**+174,8 mm**) ; le lacet de base est **négatif dans les 6 directions**, le roulis `q3` aussi,
  et le motif « traverser une paroi verticale » est négatif partout (le corps reste **ancré à
  l'épaule**, il ne peut jamais être entièrement d'un côté d'une paroi). C'est le finding A43,
  quantifié.
- **Marge FRANCHE mesurée** : l'obstacle est posé **au milieu** de la fenêtre franche ⟹
  **+66,9 mm** de pénétration dans la dalle / **+71,7 mm** de dégagement aux poses. (On refuse le
  marginal : les ~6 mm du lacet de base ont été rejetés en S10-ter.)
- **Vérité-terrain dense** (oracle **corps-convexe**, seedée) : start/goal **libres** ; **0 libre
  dans la dalle** sur 40 000 uniformes ET **0 sur 448 coins** (extrêmes distaux balayés
  explicitement) ; **invariance de redondance** (les 2⁴ extrêmes distaux donnent tous
  « collision ») ; **libre des deux côtés**.
- **Certificat** : **PROOF**, **2 feuilles** (2 collision), **A32 = 0** ; `cnp verify` **OK
  exact** en **2,45 s** ; `certify` **567 s** (budget prédit A44 avant le run : ~620 s ⟹ écart
  **−9 %**). LP de feuille **1 070 lignes** (réduit aux 3 dims actives) contre **473 870** en
  pleine dimension : **×442,9**. Bench daté : `benchmarks/results/20260908T150151Z/`.

## 6. Artefacts livrés (pack démo S11)

- **[A24] interactif HTML auto-suffisant** :
  [`usecase_binpicking_iiwa7_interactive.html`](../../benchmarks/figures/S11_usecases/usecase_binpicking_iiwa7_interactive.html)
  — 7 curseurs (butées = limites, en degrés, A25), corps = **coque 40 sommets** avec collision
  **GJK** reproduisant l'oracle, fantômes start/goal, boutons d'évasion → tous « bloqué ».
- **3D partageable** (un fichier, sans Python) :
  [`usecase_binpicking_iiwa7_3d.html`](../../benchmarks/figures/share/usecase_binpicking_iiwa7_3d.html)
  — le vrai iiwa7, le bac, le balayage start→goal en curseur, **corps certifié surligné** +
  légende A40. Invariant testé (`tests/test_share_3d_html.py`).
- **[A20, NON NÉGOCIABLE] sweep** + **C-space** + **partition slab-aware** :
  `benchmarks/figures/S11_usecases/usecase_binpicking_iiwa7_{sweep,cspace,partition}.png`.
- **[A25] limites partout** (encadré de chaque figure, cadre = boîte P, butées des curseurs,
  verdict CLI).

## 7. Critères d'acceptation — état

| # | Critère | État |
|---|---|---|
| 1 | `cnp certify` → PROOF ; `cnp verify` → OK exact | ✅ (+ cross-check de scène) |
| 2 | Budget présenté AVANT le run | ✅ prédit ~620 s (A44 : lignes × colonnes), mesuré 567 s |
| 3 | A32 = 0 ; vérité-terrain dense seedée ré-assertée | ✅ |
| 4 | Récit TAMP explicite (nœud élagué, pas « le robot ne peut pas ») | ✅ §2 et §4 |
| 5 | Pack cohérent avec le flagship (figures / limites / interactif) | ✅ mêmes composants `cnp viz` |
| 6 | Marge FRANCHE (≥ ~40 mm) | ✅ +66,9 / +71,7 mm |
