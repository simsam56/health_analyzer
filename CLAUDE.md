# Bord — Tableau de bord personnel

## Architecture

```
health_analyzer/
├── api/                    # Backend FastAPI (port 8765)
│   ├── main.py            # App FastAPI + endpoint agrégat /api/dashboard
│   ├── deps.py            # Connexion DB, auth, cache
│   └── routes/            # Routers modulaires
│       ├── health.py      # GET /api/health/{metrics,rings,readiness}
│       ├── training.py    # GET /api/training/{pmc,acwr,running}
│       ├── activities.py  # GET /api/activities/{recent,weekly-hours}
│       ├── muscles.py     # GET /api/muscles/{volume,heatmap,imbalances,sessions}
│       ├── planner.py     # CRUD /api/planner/{events,board,tasks}
│       └── calendar.py    # GET/POST /api/calendar/{status,events,sync,create}
├── frontend/              # Frontend Next.js 16 (port 3000)
│   ├── app/               # Pages (App Router)
│   │   ├── page.tsx       # Redirige vers /semaine
│   │   ├── semaine/       # Vue semaine (events + board)
│   │   ├── sante/         # Santé (rings, métriques, running, activités)
│   │   ├── travail/       # Travail (heures, tâches, backlog)
│   │   ├── social/        # Social (événements, contacts)
│   │   └── idees/         # Capture d'idées (board triage)
│   ├── components/        # Composants UI réutilisables
│   ├── lib/               # API client, types, React Query hooks
│   └── next.config.ts     # Proxy /api/python → backend:8765
├── analytics/             # Logique métier
│   ├── training_load.py   # PMC, ACWR, readiness score, métriques santé
│   ├── muscle_groups.py   # Volume musculaire, imbalances
│   ├── planner.py         # Gestion tâches/événements
│   └── sports_agent.py    # Agent IA sport
├── pipeline/              # ETL / ingestion données
│   ├── schema.py          # DDL SQLite + migrations
│   ├── parse_apple_health.py
│   ├── parse_strava_fit.py
│   └── parse_garmin_connect.py
├── dashboard/             # Ancien générateur HTML (legacy v2)
├── integrations/          # Apple Calendar sync
├── reports/               # Dashboards HTML générés (legacy)
├── tests/                 # Tests pytest
├── seed_demo.py           # Données de démo pour développement
└── athlete.db             # Base SQLite (gitignored)
```

## Stack technique

- **Backend** : Python 3.11+, FastAPI, SQLite (WAL mode), uvicorn
- **Frontend** : Next.js 16, React 19, TypeScript, Tailwind CSS 4, React Query 5
- **Charts** : Recharts 3
- **Animations** : Framer Motion 12
- **Data sources** : Apple Health XML, Strava FIT, Garmin Connect API

## Commandes

```bash
# Backend
python -m api.main                    # Démarre sur http://127.0.0.1:8765

# Frontend
cd frontend && npm run dev            # Démarre sur http://localhost:3000

# Données de démo
python seed_demo.py                   # Peuple athlete.db avec des données réalistes

# Tests
pytest tests/                         # Tests unitaires
ruff check .                          # Linting Python

# Build frontend
cd frontend && npx next build         # Build production
```

## Base de données

SQLite `athlete.db` (créée automatiquement au démarrage).

Tables principales :
- `activities` — Activités sportives (toutes sources)
- `health_metrics` — Métriques santé journalières (HRV, RHR, sleep, VO2max, weight, body_battery)
- `strength_sessions` / `exercise_sets` — Sessions muscu détaillées
- `planner_tasks` — Tâches planifiées avec triage (kanban)
- `calendar_events` — Événements Apple Calendar
- `daily_load` / `weekly_muscle_volume` — Agrégats calculés

Noms de métriques dans `health_metrics.metric` :
`hrv_sdnn`, `rhr`, `sleep_h`, `vo2max`, `weight_kg`, `body_battery`

## API principale

`GET /api/dashboard` — Agrégat complet en 1 requête (santé, readiness, PMC, ACWR, running, muscles, événements, board, activités).

Le frontend utilise un proxy Next.js : `/api/python/:path*` → `http://127.0.0.1:8765/api/:path*`

## Conventions

- Python : formatage ruff, type hints, docstrings françaises
- TypeScript : strict mode, composants fonctionnels, React Query pour le data fetching
- Commits : préfixes conventionnels (feat, fix, chore, refactor, docs)
- Pas de fichiers `.env` committés — utiliser `.env.example` comme référence
- Variables d'env : `BORD_DB`, `BORD_PORT`, `BORD_API_TOKEN`, `BORD_DASHBOARD`

## Fichiers legacy (v1/v2)

Ces fichiers sont des vestiges des versions précédentes et ne sont plus utilisés par l'app v3 :
- `*.sh` scripts (start_cockpit, sync, launch_*, setup_*, etc.)
- `cockpit_server.py`, `server_simple.py` — anciens serveurs
- `build_dashboard.py`, `sport_dashboard.py`, `health_analyzer.py` — générateurs HTML
- `main.py` (racine), `launch.py`, `quick_launch.py`, `test_launch.py` — lanceurs legacy
- `dashboard/` — générateur HTML premium
- `reports/*.html` — dashboards HTML générés
- `diagnose*.py`, `setup_calendar.py` — scripts de diagnostic
- `garmin_sync*.py` — sync Garmin (remplacé par pipeline/)
- `*.command` — lanceurs macOS
- `AUDIT_*.md`, `ROADMAP_*.md`, `UI_AUDIT_*.md` — anciens audits
