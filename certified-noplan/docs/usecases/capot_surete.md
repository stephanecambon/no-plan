# Cas d'usage — Capot de sûreté · fenêtre opérateur : certificat EXACT recomptable

> **L'auditeur RECOMPTE, il ne fait pas confiance au pipeline.** Une pièce algébrique versable au
> dossier de sûreté, re-vérifiable en arithmétique exacte par un tiers — pas un « croyez notre
> collision-checker flottant ».

---

## 1. Secteur & persona (qui paie)

- **Secteur Cambon AI : sûreté / réglementaire** (sûreté fonctionnelle des cellules robotisées,
  ISO 10218 / ISO/TS 15066 / EN ISO 13849, analyses de risque, marquage CE).
- **Qui paie** : le **responsable sûreté** de l'intégrateur (et l'**organisme notifié** qui audite
  le dossier). Leur problème : justifier qu'une zone est **inatteignable par le bras** sans
  s'en remettre à la parole d'un pipeline de simulation non re-vérifiable.

## 2. Le récit (scène — apparence FAISABLE, A20)

Une cellule 7-DOF travaille derrière un **capot de sûreté** (guard panel) percé d'une **fenêtre
opérateur**. Question d'analyse de risque : *« le bras peut-il, depuis sa zone home, atteindre la
zone opérateur en traversant le plan du capot ? »* La **fenêtre est visible**, la zone opérateur
**proche** — l'intuition dit *« il y a un passage »*. Le certificat prouve que **non** : viser la
fenêtre ne sert à rien, le **segment proximal** reste pris dans le plein du capot, fenêtre ou pas.

## 3. Claim CALIBRÉ — ce que le certificat prouve, et ce qu'il ne prouve PAS

**PROUVE** : *dans les limites articulaires affichées* (actifs **±70°**, distaux **±143°** ⊂
limites usine), **aucun chemin continu sans collision** ne fait franchir le plan du capot au
segment proximal épaule-coude (link 2) — dalle `|φ|≤δ` entièrement en collision, **indépendamment
des 4 joints distaux**. Preuve **algébrique exacte**, **re-vérifiée en rationnels par un programme
indépendant** (`cnp verify`, <500 lignes, stdlib seule, sans importer le générateur).

**NE PROUVE PAS** :
- **pas** l'inatteignabilité *hors* des limites affichées ni hors géométrie modélisée (autre
  outil monté, déplacement de base, jeu mécanique) — **UNDECIDED ≠ inatteignable** (SPEC §6) ;
- **pas** une garantie de sûreté *système* (ce n'est PAS une certification ISO ; c'est une
  **pièce géométrique** versable, à intégrer dans une analyse de risque par l'humain compétent) ;
- **pas** un facteur de performance vs un autre outil (pas de ×N) ;
- **pas** une montée en dims actives gratuite (régime `(d+1)^k`, S9f ; ici k=3) ;
- **pas** la fidélité physique au-delà du modèle (bac technique 7-DOF, frames simplifiés, A21).

## 4. Proposition de valeur PROPRE à ce cas

**La NATURE du certificat, pas sa vitesse** (différenciateur A26/DECISION-G2 §4). Les pipelines de
vérification d'atteignabilité du marché s'appuient sur un **collision-checker flottant** : non
recomptable, l'auditeur doit **faire confiance** au pipeline. Notre certificat est **algébrique et
exactement re-vérifiable** : l'organisme notifié relance `cnp verify` (arithmétique rationnelle,
indépendant du générateur) et **recompte la preuve lui-même**. Pour un dossier de sûreté, c'est la
différence entre *« le fournisseur affirme »* et *« j'ai re-vérifié »*. C'est aussi le seul des
trois cas où la **recomptabilité** est la valeur centrale (vs un argument de portée ou d'élagage).

## 5. Scène & plausibilité (PAS une certification)

- **Spec chargeable** : [`scenes/usecase_capot_surete.yaml`](../../scenes/usecase_capot_surete.yaml)
  — 7-DOF (`spatial_revolute`), corps certifié = **link 2**, obstacle `GUARD_PANEL` (plein du
  capot) en H-rep exacte ; la **fenêtre opérateur** est l'espace libre au-dessus/sur les côtés du
  panneau (apparence faisable, A20). `python -m cnp show … --interactive` OK.
- **Piégeage proximal explicite** : link 2 dépend des seuls **{0,1,2}** (3 **dims actives**) ;
  j3,j4,j5,j6 **prouvés passifs** pour la paire (`GUARD_PANEL`).
- **Plausibilité** (`python scripts/usecase_sanity.py scenes/usecase_capot_surete.yaml`, seedé) :
  start/goal **libres** ; **0 libre dans la dalle** sur 30 000 uniformes ET **0 sur 30 000
  biaisés-coins** (S9f) ; **libre des deux côtés** (2706/4000 à gauche, 2679/4000 à droite — le
  capot plus large laisse de plus grandes poches libres hors-dalle, déconnexion nette). ⟹
  **déconnexion candidate plausible**. *La preuve est `cnp verify` en S11.*

## 6. Storyboard des artefacts (construits en S11, pack démo)

- **[A24] interactif HTML** : curseurs 7 joints (butées = limites, degrés, A25) ; collision
  visuelle ; **fantômes home/zone-opérateur** ; **boutons d'évasion** (viser la fenêtre, rouler le
  poignet) → verdict « bloqué ». **Bouton « recompter le certificat »** rejouant `cnp verify`
  (l'argument auditabilité, rendu tangible).
- **[A20, NON NÉGOCIABLE] vue sweep** : le bras *semblant viser la fenêtre*, poses en collision
  en rouge — l'œil croit au passage, la preuve dit non.
- **Figure C-space livrée ici** :
  [`benchmarks/figures/S9b_usecases/usecase_capot_surete_cspace.png`](../../benchmarks/figures/S9b_usecases/usecase_capot_surete_cspace.png).
- **[A25] limites partout** + **rappel des hypothèses du verdict** (statiques, polytopes convexes,
  géométrie exacte) — central ici, car c'est ce que l'auditeur lit.

## 7. Critères d'acceptation (ce que S11 doit livrer)

1. `cnp certify scenes/usecase_capot_surete.yaml` → **PROOF** ; `cnp verify` → **OK** (exact),
   **lancé par un tiers** sur la pièce versée (démonstration de recomptabilité).
2. Budget présenté avant run (~8 feuilles / secondes attendus, k=3).
3. **A32 = 0** ; vérité-terrain dense seedée ré-assertée (règle 9).
4. **Encadré « hypothèses du certificat »** explicite (limites degrés, pas de wrap-around,
   obstacles statiques, corps = polytopes, géométrie rationnelle exacte) — la pièce doit se lire
   **sans le pipeline qui l'a produite**.
5. Cadrage honnête : pièce géométrique re-vérifiable, **PAS** une certification ISO en soi.
