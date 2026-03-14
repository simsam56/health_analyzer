# Bord — Dashboard personnel santé/sport/vie

## Stack

- **Backend**: Python 3.11+, FastAPI, SQLite (athlete.db), pandas, plotly
- **Frontend**: Next.js 16, React 19, Tailwind 4, TypeScript, TanStack Query, Recharts
- **Outils**: Ruff (lint+format), pytest+cov, mypy, bandit

## Commandes

- Backend : `python3 -m uvicorn api.main:app --port 8765 --reload`
- Frontend : `cd frontend && npm run dev`
- Lint : `ruff check . && ruff format --check .`
- Tests : `pytest`
- Typecheck : `mypy analytics/`

## Structure du projet

```
api/
  main.py            ← serveur FastAPI (port 8765) — CANONICAL
  routes/            ← un fichier par domaine (activities, calendar, health, muscles, planner, training)
  deps.py            ← dépendances partagées (db connection, etc.)
analytics/
  training_load.py   ← ACWR, PMC, Wakeboard Score, métriques santé
  muscle_groups.py   ← volume musculaire, déséquilibres
  planner.py         ← logique planning (semaines, tâches)
  sports_agent.py    ← agent d'analyse sportive intelligent
pipeline/
  schema.py          ← DDL SQLite, migrations
  parse_apple_health.py  ← XML Apple Health → SQLite
  parse_strava_fit.py    ← FIT.gz Strava → SQLite
  parse_garmin_connect.py ← API Garmin → SQLite
integrations/
  apple_calendar.py  ← sync bidirectionnelle Apple Calendar
frontend/
  app/               ← App Router (layout, pages par section)
  components/        ← composants React réutilisables
  lib/               ← queries/, types.ts, utils
tests/               ← pytest (test_training_load, test_muscle_groups, test_pipeline, etc.)
_legacy/             ← code mort, gardé pour référence
_debug/              ← fichiers de diagnostic temporaires
scripts/             ← scripts shell utilitaires
```

## Conventions

- API routes dans `api/routes/`, un fichier par domaine
- Analytics : fonctions pures, typées, testées
- Frontend : App Router, composants dans `components/`, queries dans `lib/queries/`
- Alias `@/*` pour imports frontend
- SQLite : `athlete.db`, schema dans `pipeline/schema.py`

## Checklist avant de valider une tâche

1. `ruff check .` passe sans erreur
2. `pytest` passe
3. Pas de `any` en TypeScript
4. Les nouveaux endpoints ont un test

## Do

- Utiliser `api/main.py` pour tout nouveau endpoint
- Utiliser le design system existant (voir `frontend/app/globals.css`)
- Écrire les types dans `lib/types.ts`
- Tester les fonctions analytics avec hypothesis quand pertinent

## Don't

- NE JAMAIS toucher aux fichiers dans `_legacy/` (code mort, gardé pour référence)
- NE PAS ajouter de routes dans `cockpit_server.py` (legacy, dans `_legacy/`)
- NE PAS créer de nouveaux scripts shell à la racine
- NE PAS modifier `athlete.db` directement (passer par `pipeline/schema.py`)
- NE PAS utiliser `build_dashboard.py` (legacy, remplacé par le frontend)

## Hypothèses à vérifier

- `garmin_sync.py` et `garmin_sync_full.py` sont encore actifs (à confirmer avec l'utilisateur)
- `dashboard/generator.py` pourrait être supprimé définitivement
