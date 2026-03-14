# Workflow de développement

## Lancer le projet

```bash
# Terminal 1 — Backend
python3 -m uvicorn api.main:app --port 8765 --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

## Avant de commit

1. `ruff check .` — lint obligatoire
2. `ruff format --check .` — format vérifié
3. `pytest` — tests passent
4. Pas de `any` en TypeScript

## Ne PAS committer

- `.env` (secrets)
- `athlete.db` (données personnelles)
- `export.xml`, `export_cda.xml` (exports Apple Health)
- `_legacy/`, `_debug/` (exclus mais versionnés pour référence)
- `*.log`, `*.pkl`, `*.cache`

## Ajouter un endpoint

1. Créer/éditer le fichier dans `api/routes/`
2. Enregistrer le router dans `api/main.py`
3. Ajouter un test dans `tests/`

## Ajouter une métrique analytics

1. Fonction pure dans `analytics/`
2. Types annotés, retour typé
3. Test dans `tests/`
