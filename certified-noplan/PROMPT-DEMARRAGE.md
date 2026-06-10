# PROMPT-DEMARRAGE.md — Première session Claude Code (S0)

## Avant de lancer Claude Code (à faire toi-même, ~10 min)

```bash
# 1. Python Homebrew (PAS le Python système, PAS Anaconda)
brew install python@3.12

# 2. Claude Code (si pas déjà fait)
brew install --cask claude-code

# 3. Dézipper ce dossier où tu veux, puis :
cd certified-noplan
git init && git add -A && git commit -m "S0 input: SPEC, CLAUDE.md, reference sandbox scripts"

# 4. Lancer
claude
```

Note : ne crée PAS le venv toi-même, c'est la première tâche de la session
(elle doit être reproductible par le script).

---

## Prompt à coller dans Claude Code (session S0)

```
Lis dans cet ordre : CLAUDE.md (règles binding + plan de sessions), SPEC.md
(spécification complète), JOURNAL.md (état), docs/CAMPAGNE-E1-E4-RESULTATS.md
(résultats de référence et pièges connus).

Nous démarrons la session S0 telle que définie dans CLAUDE.md. Objectif :
environnement reproductible + squelette du repo + portage des scripts de
référence (sandbox_reference/) en suite de tests de régression.

Contraintes de cette session :
1. venv Python 3.12 Homebrew + pyproject.toml avec les dépendances de SPEC §3 ;
   tout doit s'installer via `make setup` (script idempotent).
2. Arborescence src/cnp/ exactement comme SPEC §3 ; porter
   sandbox_reference/polylin.py dans src/cnp/polylin.py en CONSERVANT ses
   self-tests, convertis en tests pytest.
3. Convertir E1-E4 (exp12_ladder.py, exp34_multipair.py) en tests pytest dans
   tests/ : les scènes planaires deviennent des fixtures réutilisables. Les
   valeurs de référence à reproduire à 1e-6 près sont dans
   sandbox_reference/exp12_results.json et dans docs/CAMPAGNE-E1-E4-RESULTATS.md
   (E3 : certified=True, 46 feuilles, 0 échec ; contrôle négatif : refus).
4. Écrire tests/test_putinar_sign.py qui FIGE le signe g − μT (un certificat
   construit avec g + μT doit être rejeté par le test). Règle 2 de CLAUDE.md.
5. Makefile : setup / test / clean. CI locale = `make test` vert.
6. Critère de sortie G0' (CLAUDE.md S0) : pytest vert, t* identiques au bac à
   sable, JOURNAL.md mis à jour (Fait / Décisions / Pièges / Prochaine étape),
   commit final.

Discipline : si tu rencontres une friction d'installation (Drake n'est PAS
nécessaire en S0 — ne l'installe que si trivial, sinon note-le pour S1), ne
contourne jamais un test en l'affaiblissant ; journalise et demande-moi.
Vérifie chaque étape en l'exécutant réellement. À la fin, montre-moi la sortie
complète de `make test` et le diff de JOURNAL.md.
```

---

## Sessions suivantes (gabarit de prompt)

Pour S1, S2, … réutiliser le même gabarit court :

```
Lis CLAUDE.md, SPEC.md, JOURNAL.md. Vérifie que les critères de sortie de la
session précédente sont verts (relance `make test`). Nous démarrons la session
S<N> telle que définie dans CLAUDE.md : [coller le bloc de la session].
Mêmes règles : soundness avant tout, suite adversariale après tout changement
de witness/engine/verify, JOURNAL.md + commit en fin de session.
```

## Rappels d'exploitation

- Une session Claude Code = une session du plan. Ne pas enchaîner deux sessions
  du plan dans le même contexte, même si ça semble rapide.
- Les runs longs (S9-S10) : lancer via les scripts à checkpoints (engine.py),
  pas en interactif, pour pouvoir reprendre.
- Si une porte (G1'-G4') est rouge : la décision de re-scope se prend avec moi
  (Claude sur claude.ai) ou un collaborateur humain, pas dans Claude Code.
