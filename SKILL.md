# SKILL — Bord : Dashboard personnel santé/sport/vie

## Description

Dashboard personnel avec backend FastAPI + frontend Next.js, analysant :
- **Apple Health** : workouts, HRV, FC repos, VO2Max, sommeil
- **Strava FIT** : activités + séances musculation avec exercices détaillés
- **Garmin Connect** : sync API directe
- **Groupes musculaires** : volume par muscle, déséquilibres, recommandations
- **Planner** : planning hebdomadaire pilotable, sync Apple Calendar

## Architecture

```
api/
  main.py                    ← serveur FastAPI (port 8765) — CANONICAL
  routes/                    ← activities, calendar, health, muscles, planner, training
analytics/
  training_load.py           ← ACWR, PMC, Wakeboard Score
  muscle_groups.py           ← Volume/sem, déséquilibres, radar
  planner.py                 ← Logique planning
  sports_agent.py            ← Agent d'analyse sportive
pipeline/
  schema.py                  ← SQLite DDL (athlete.db)
  parse_apple_health.py      ← Parse export.xml → DB
  parse_strava_fit.py        ← Parse FIT.gz + CSV → DB
  parse_garmin_connect.py    ← API Garmin → DB
integrations/
  apple_calendar.py          ← Sync bidirectionnelle Apple Calendar
frontend/                    ← Next.js 16, React 19, Tailwind 4
  app/                       ← App Router (sections: travail, sante, social, semaine, idees)
  components/                ← Composants React réutilisables
  lib/                       ← queries/, types.ts
```

## Commandes

```bash
# Backend
python3 -m uvicorn api.main:app --port 8765 --reload

# Frontend
cd frontend && npm run dev

# Lint + format
ruff check . && ruff format --check .

# Tests
pytest

# Typecheck
mypy analytics/

# Garmin sync
python3 garmin_sync_full.py --from 2025-01-01
```

## Données et Sources

### Apple Health (export.xml)
- Workouts avec durée, distance, FC, training load
- HRV SDNN, FC repos, VO2Max, Sommeil, Poids

### Strava FIT (export_strava/)
- Fichiers FIT.gz = activités complètes
- Séances musculation avec données détaillées

### Garmin Connect (garmin_sync.py / garmin_sync_full.py)
- Sync API directe : activités, HRV, Body Battery, Sleep

## Métriques calculées

### Wakeboard Readiness Score (0-100)
- HRV (40%) : comparaison à la baseline personnelle
- Sommeil (30%) : idéal 7.5-9h
- ACWR (30%) : zone optimale 0.8-1.3

### PMC (Performance Management Chart)
- CTL = Forme chronique (EWM 42j)
- ATL = Fatigue aiguë (EWM 7j)
- TSB = CTL - ATL (forme nette)

### Muscle Groups
Volume cibles (sets/semaine, hypertrophie) :
- Pecs : 12 | Dos : 14 | Épaules : 12
- Biceps : 10 | Triceps : 10
- Jambes : 16 | Core : 12

## Notes développeur

### Déduplication
Clé : `type[:8]|YYYY-MM-DD|dur_arrondi_5min`
Strava FIT est inséré en premier → priorité sur Apple Health.

### Mapping exercices FIT
Les fichiers récents (sept 2025+) n'ont pas de `exercise_title` messages.
Utiliser `set.category` (tuple d'indices) → `GARMIN_CAT_IDX` dans `parse_strava_fit.py`.
