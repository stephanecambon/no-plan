# Cas d'usage — Bin-picking logistique : élagage PROUVÉ d'une branche TAMP infaisable

> **Un planificateur qui ÉLAGUE avec une preuve, pas un planificateur qui ABANDONNE sur un
> timeout.** « Ce colis est inatteignable sans retirer d'abord la paroi » — prouvé, pas supposé.

---

## 1. Secteur & persona (qui paie)

- **Secteur Cambon AI : logistique / intralogistique** (dépalettisation, préparation de
  commandes, vidage de bacs profonds).
- **Qui paie** : l'éditeur (ou l'intégrateur) d'un **planificateur TAMP** (task-and-motion) de
  bin-picking, dont le coût opérationnel est dominé par les **branches explorées en vain**. Un
  oracle d'infaisabilité **certain** sur une branche = du temps de planification (et du temps de
  cycle robot) économisé à chaque pièce.

## 2. Le récit (scène — apparence FAISABLE, A20)

Un cobot 6 axes (classe UR/ABB) vide un **bac profond**. Le planificateur TAMP ouvre une branche :
*« saisir le colis au FOND du bac par cette approche »*. Le colis est **visible et proche** ; la
**paroi frontale** du bac est pleine et haute. Sans preuve, le planificateur **essaie** : il
échantillonne des milliers de configurations IK + chemins, et finit en **timeout** — sans jamais
savoir si la branche était *infaisable* ou seulement *difficile à échantillonner*.

## 3. Claim CALIBRÉ — ce que le certificat prouve, et ce qu'il ne prouve PAS

**PROUVE** : *dans les limites articulaires affichées* (actifs **±70°**, distaux **±143°** ⊂
limites usine), **aucun chemin continu sans collision** ne fait passer le segment proximal
épaule-coude (link 2) **de l'avant à l'arrière de la paroi du bac** — la dalle `|φ|≤δ` est
entièrement en collision, **indépendamment des poignets distaux**. Preuve **algébrique exacte**,
recomptable (`cnp verify`, <500 l.).

**NE PROUVE PAS** :
- **pas** que le colis est infaisable *en soi* — seulement **par cette approche, dans ces
  limites** (retirer la paroi, ou une autre approche, change le problème) ; **UNDECIDED ≠
  infaisable** (SPEC §6) ;
- **pas** un gain de vitesse chiffré vs un planificateur du marché (pas de ×N) ;
- **pas** une portée illimitée en dims actives : régime `(d+1)^k` (S9f), ici k=3 ;
- **pas** la fidélité physique au-delà du modèle (bac technique, A21).

## 4. Proposition de valeur PROPRE à ce cas

**Transformer un timeout en élagage.** La valeur n'est pas « le robot ne peut pas » — c'est
**« le PLANIFICATEUR peut couper cette branche, avec une preuve, et passer à la suivante »**. Là
où l'échantillonnage ne produit *jamais* de « non » certain (absence de preuve ≠ preuve
d'absence), notre certificat fournit l'**infaisabilité certifiée** qui manque à la boucle TAMP :
un nœud `INFEASIBLE` prouvé, pas un nœud `UNKNOWN` abandonné sur budget. C'est l'argument-cœur du
démonstrateur (SPEC §6 : « élaguer une branche infaisable d'un arbre TAMP »), instancié sur la
scène la plus banale du secteur.

## 5. Scène & plausibilité (PAS une certification)

- **Spec chargeable** : [`scenes/usecase_binpicking.yaml`](../../scenes/usecase_binpicking.yaml)
  — 6-DOF (`spatial_revolute`), corps certifié = **link 2**, obstacle `CRATE_WALL` (paroi
  frontale) en H-rep exacte. `python -m cnp show … --interactive` OK.
- **Piégeage proximal explicite** : link 2 dépend des seuls **{0,1,2}** (3 **dims actives**) ;
  j3,j4,j5 (poignet) **prouvés passifs** pour la paire (`CRATE_WALL`).
- **Plausibilité** (`python scripts/usecase_sanity.py scenes/usecase_binpicking.yaml`, seedé) :
  start/goal **libres** ; **0 libre dans la dalle** sur 30 000 uniformes ET **0 sur 30 000
  biaisés-coins** (S9f) ; **libre des deux côtés** (3649/4000 à gauche, 3643/4000 à droite). ⟹
  **déconnexion candidate plausible**. *La preuve est `cnp verify` en S11.*

## 6. Storyboard des artefacts (construits en S11, pack démo)

- **[A24] interactif HTML** : curseurs 6 joints (butées = limites, degrés, A25) ; collision
  visuelle ; **fantômes home/colis** ; **boutons d'évasion** (plonger le coude, contourner) →
  verdict « bloqué ». Mise en scène TAMP : un bandeau « branche élaguée (preuve) » au lieu de
  « timeout ».
- **[A20, NON NÉGOCIABLE] vue sweep** : éventail de poses montrant le préhenseur *semblant
  atteindre* le colis au fond, poses en collision en rouge.
- **Figure C-space livrée ici** :
  [`benchmarks/figures/S9b_usecases/usecase_binpicking_cspace.png`](../../benchmarks/figures/S9b_usecases/usecase_binpicking_cspace.png).
- **[A25] limites partout** (encadré, cadre = boîte P, butées curseurs, verdict CLI).

## 7. Critères d'acceptation (ce que S11 doit livrer)

1. `cnp certify scenes/usecase_binpicking.yaml` → **PROOF** ; `cnp verify` → **OK** (exact).
2. Budget présenté avant run (~8 feuilles / secondes attendus, k=3).
3. **A32 = 0** ; vérité-terrain dense seedée ré-assertée (règle 9).
4. **Récit TAMP** explicite dans le one-pager final + interactif : la sortie `INFEASIBLE` prouvée
   est positionnée comme **nœud élagué** d'un arbre de planification (pas seulement « le robot ne
   peut pas »).
5. Pack démo cohérent avec le flagship (mêmes conventions de figures/limites/interactif).
