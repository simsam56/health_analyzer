# Architecture — Canonical vs Legacy

## Canonical (code actif)

| Composant | Chemin | Rôle |
|-----------|--------|------|
| API server | `api/main.py` | FastAPI, port 8765 |
| API routes | `api/routes/` | Un fichier par domaine |
| Analytics | `analytics/` | Logique métier (training_load, muscle_groups, planner) |
| Pipeline | `pipeline/` | Ingestion données (Apple Health, Strava, Garmin) |
| Intégrations | `integrations/` | Apple Calendar sync |
| Frontend | `frontend/` | Next.js 16, React 19, Tailwind 4 |
| Garmin sync | `garmin_sync.py`, `garmin_sync_full.py` | Scripts de sync Garmin actifs |

## Legacy (dans `_legacy/`, NE PAS TOUCHER)

| Fichier | Remplacé par |
|---------|-------------|
| `cockpit_server.py` | `api/main.py` |
| `build_dashboard.py` | `frontend/` |
| `main.py` | `api/main.py` |
| `health_analyzer.py` | `analytics/` + `pipeline/` |
| `dashboard/generator.py` | `frontend/` |
| `server_simple.py` | `api/main.py` |

## Debug (dans `_debug/`, fichiers temporaires)

Diagnostics, audits, logs de debug — ne pas importer.
