# Infaisabilité certifiée — Campagne expérimentale E1-E4 (10 juin 2026)

Session Claude (bac à sable claude.ai, Python 3.12, cvxpy 1.9.1 / Clarabel).
Code : `polylin.py` (bibliothèque), `exp12_ladder.py` (E1-E2), `exp34_multipair.py` (E3-E4), `make_figure.py`.
Figure : `certified_disconnection_results.png`. Données : `exp12_results.json`.

## Hypothèses testées

- **H1** — Le mur du témoin constant (échec observé à n=5 en session antérieure) est levé par un témoin *affine* x(s) = Σ λ_k(s)·v_k(s), λ_k affines.
- **H2** — Les bornes de Bernstein (tensorielle, degré ≤2-3/variable) remplacent le SDP-SOS par un **LP**, sans perte significative de marge, et scalent mieux.
- **H3** — Le multi-paires se résout par **partition par construction** (branch-and-bound par découpes axiales de la dalle), chaque feuille certifiée contre UNE paire ; le risque est le nombre de feuilles, pas l'existence d'une preuve de couverture.
- **H4** — Le pipeline hybride « échantillonner → ajuster φ → certifier » (piste A, à la Li-Dantam) fonctionne de bout en bout.

## Résultats

### E1 — Échelle de témoins (scène synthétique multilinéaire contrôlée, n = 3..6)
Carré mobile A(s) (drift multilinéaire avec termes croisés), boîte fixe B, cellule Q=[−1,1]^n.

| témoin | t* (n=3..6) | verdict |
|---|---|---|
| constant | −0.090 | échec partout (par construction) |
| **affine** | **+0.220** | **certifie partout testé** |
| multilinéaire | +0.220 | n'apporte rien de plus ici |

Contrôles négatifs (drift élargi ⇒ pas de collision aux coins) : refusés (t* = −0.190) par les deux back-ends. **H1 confirmée.**

### E2 — Bernstein-LP vs SOS-SDP (mêmes instances, témoin affine)
**Même t\* = 0.220 exactement** pour les deux back-ends (zéro conservatisme de Bernstein sur cette famille deg ≤2/var). Temps :

| n | SOS-SDP (Clarabel, naïf) | Bernstein-LP |
|---|---|---|
| 3 | 0.16 s | 0.01 s |
| 5 | 2.7 s | 0.03 s |
| 6 | 41.5 s | 0.10 s |
| 7 | — | 0.4 s |
| 8 | — | 1.9 s |
| **10** | — | **32.4 s** (≈236 k lignes LP) |

Mur 3^n du LP vers n≈10-12 sur cette machine — au-delà de la cible 7-DOF. **H2 confirmée fort.** Caveats : scène synthétique, marge généreuse, une seule paire, aucune subdivision nécessaire ; le SDP naïf cvxpy n'est pas C-IRIS+Mosek optimisé.

### E3 — Multi-paires, vraie cinématique (bras 2-link, FK rationnelle, 3 obstacles)
Scène : UP/DOWN/MID, aucun obstacle ne bloque seul ; θ ∈ [−π/2, π/2]² ; φ = s1, δ = 0.05.
Certificat de feuille **slab-aware** : Bernstein(g − μ·(δ²−φ²)) ≥ t, μ ≥ 0 (forme de Putinar côté Bernstein).

**certified = True** en 3.7 s : 46 feuilles (38 collision — DOWN 12, MID 14, UP 12 ; 8 hors-dalle ; 0 échec). Les trois paires se relaient le long de la dalle. **H3 confirmée** : le théorème de déconnexion est établi rigoureusement (sous limites articulaires données, sans wrap-around).

Contrôle de soundness : obstacles rétrécis de 30 % (prémisse « dalle ⊆ C_obs » fausse, 86/369 échantillons libres) ⇒ le certificateur **refuse** (904 feuilles en échec). ✔

### E4 — Barrière apprise (pipeline hybride)
φ ajusté par moindres carrés (1500 échantillons, cible sign(s1) sur les points libres, base deg ≤2/var), δ_fit = 0.350. **certified = True** en 6.7 s, 78 feuilles (76 collision). **H4 confirmée** à l'échelle jouet — la Phase 2 (trouver φ) est dérisquée dans son principe.

## Leçons de débogage (pièges à retenir)

1. **Cellules à cheval sur la frontière de dalle** : jamais résolues par bissections dyadiques (−0.05 n'est pas dyadique) ⇒ le multiplicateur de Putinar côté Bernstein est *nécessaire*, pas un raffinement.
2. **Signe de Putinar** : Bernstein(g + μT) ≥ t est UNSOUND ; la forme correcte est g − μT ≥ t ⟹ g ≥ t sur {T ≥ 0}.
3. **Micro-canal libre détecté par le certificateur** : la grille de validation à 41 points avait raté un canal libre (s1∈[−0.05,−0.04], s2∈[0.345,0.38]) ; le certificat refusait *à raison*. Démonstration en acte de la valeur du rigoureux contre l'échantillonnage. (Scène corrigée ensuite.)
4. Les dernières feuilles à marge −0.002 se certifient avec une bissection de plus (depth 14→16) : la profondeur est un paramètre de coût, pas de faisabilité.

## Limites honnêtes

- E3/E4 : **2-DOF seulement** ; n=10 atteint uniquement sur scène synthétique mono-paire sans subdivision.
- Solveurs bac à sable (Clarabel/cvxpy), pas de comparaison directe avec Li-Dantam ni avec C-IRIS+Mosek.
- Hypothèse wrap-around (limites articulaires dans (−π, π)) requise par l'argument IVT — à inscrire dans l'énoncé du théorème.
- L'identité t*(Bernstein) = t*(SOS) est observée sur cette famille, pas démontrée en général (Bernstein est conservatif en général ; convergence par subdivision/élévation de degré).
