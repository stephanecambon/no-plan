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
