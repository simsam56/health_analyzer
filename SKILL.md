# SKILL — PerformOS v2 : Sport Performance Dashboard

## Description
Génère un dashboard HTML de performance sportive (Apple Dark, iPhone-first) en analysant :
- **Apple Health** : workouts, HRV, FC repos, VO2Max, sommeil
- **Strava FIT** : activités + séances musculation avec exercices détaillés
- **Groupes musculaires** : volume par muscle, déséquilibres, recommandations

## Architecture
```
health_analyzer/
├── sport_dashboard.py          ← Point d'entrée principal
├── pipeline/
│   ├── schema.py               ← SQLite DDL (athlete.db)
│   ├── parse_apple_health.py   ← Parse export.xml → DB
│   └── parse_strava_fit.py     ← Parse FIT.gz + CSV → DB
├── analytics/
│   ├── muscle_groups.py        ← Volume/sem, déséquilibres, radar
│   └── training_load.py        ← ACWR, PMC, Wakeboard Score
├── dashboard/
│   └── generator.py            ← HTML iPhone-first (Plotly)
├── athlete.db                  ← SQLite (source unique de vérité)
├── export.xml                  ← Apple Health export (non versionné)
├── export_strava/              ← Export Strava (non versionné)
├── sync_and_generate.sh        ← Pipeline automatique
└── run.command                 ← Lanceur double-clic macOS
```

## Usage Claude
### Régénérer le dashboard
```
Génère le dashboard PerformOS avec mes données actuelles
```

### Analyser un muscle spécifique
```
Analyse mon entraînement des jambes sur les 4 dernières semaines
```

### Détecter les déséquilibres
```
Quels muscles je néglige le plus ? Compare mes volumes actuels aux recommandations
```

### Ajouter une source de données
```
Intègre mes données Garmin Connect dans le pipeline
```

## Commandes rapides
```bash
# Dashboard complet
python3 sport_dashboard.py

# Sauter le parsing (DB déjà à jour)
python3 sport_dashboard.py --skip-parse

# Analyser 8 semaines au lieu de 4
python3 sport_dashboard.py --weeks-muscle 8

# Pipeline automatique (double-clic sur le Bureau)
./run.command
```

## Données et Sources

### Apple Health (export.xml)
- Workouts avec durée, distance, FC, training load
- HRV SDNN (dernière mesure : jan 2025)
- FC repos (dernière mesure : sept 2025)
- VO2Max, Sommeil, Poids

### Strava FIT (export_strava/)
- 108 fichiers FIT.gz = activités complètes
- 25 séances musculation avec données détaillées :
  - Jan-Mai 2025 : noms d'exercices en français + catégories Garmin
  - Sept 2025+ : catégories par indices uniquement
- 468 séries enregistrées, 7 groupes musculaires identifiés

### Données manquantes / à améliorer
- Garmin Connect API (HRV live, Body Battery, Sleep score)
- Poids corporel (seulement 4 mesures dans AH)
- Reps non enregistrés pour les séances récentes (Sept-Fév)

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

### SQLite ne fonctionne pas sur FUSE (virtiofs)
Développer dans `/sessions/magical-beautiful-feynman/` et copier les fichiers Python vers `mnt/`.
La DB `athlete.db` se crée automatiquement dans le dossier du projet sur macOS.

### Mapping exercices FIT
Les fichiers récents (sept 2025+) n'ont pas de `exercise_title` messages.
Utiliser `set.category` (tuple d'indices) → `GARMIN_CAT_IDX` dans `parse_strava_fit.py`.

### Déduplication
Clé : `type[:8]|YYYY-MM-DD|dur_arrondi_5min`
Strava FIT est inséré en premier → priorité sur Apple Health.
