# Bord v3 - Runbook

Ce document sert de guide d'exploitation rapide (local Mac).

## 1) Installation minimale

```bash
cd ~/Documents/health_analyzer
python3 -m pip install fitparse garminconnect python-dotenv pyobjc-framework-EventKit --break-system-packages
```

## 2) Commandes principales

- Lancement simple Bord (recommandé, 1 commande):
```bash
bash start_bord.sh
```
Ouvre automatiquement le navigateur sur la page **Pilotage** (board tâches + calendrier + sync Apple Calendar).
Utiliser le bouton **⟳ Synchroniser** dans l'UI pour déclencher une sync Apple Calendar bidirectionnelle.

- Run complet (parse + dédup + dashboard + agenda):
```bash
python3 main.py --garmin --days 90
```
Note: le parse local Apple/Strava est désormais en **smart skip** (si les exports n'ont pas changé, il est ignoré automatiquement).

- Run rapide quotidien (Garmin + agenda, sans reparse Apple/Strava):
```bash
python3 main.py --garmin --days 90 --skip-parse
```
Astuce: la sync Garmin est aussi en smart skip (par défaut 45 min).

- Forcer un reparse local même si smart skip actif:
```bash
python3 main.py --garmin --days 90 --force-parse
```

- Forcer Garmin même si sync récente:
```bash
python3 main.py --garmin --days 90 --force-garmin
```
Astuce perf: limiter le refresh complet aux derniers jours (incrémental):
```bash
python3 main.py --garmin --days 90 --force-garmin --garmin-refresh-tail-days 3
```

- Run rapide (sans reparse, sans Garmin):
```bash
python3 main.py --skip-parse
```

- Mode dashboard interactif (UI persistante DB + API locale):
```bash
python3 main.py --skip-parse --garmin --days 90 --serve
```
Puis ouvrir: `http://127.0.0.1:8765`
Note: si un dashboard existe déjà, Bord démarre immédiatement puis les données se rafraîchissent en arrière-plan.

- Mode dashboard interactif avec token API fixe (recommandé):
```bash
BORD_API_TOKEN="change-me-local-token" python3 main.py --skip-parse --garmin --days 90 --serve
```
Le token protège les actions d'écriture (`POST/PATCH/DELETE`) côté planning.

- Ajouter une tâche dans le planning (et Apple Calendar si activé):
```bash
python3 main.py --add-task "10km tempo" --task-category sante --task-date 2026-12-11 --task-time 14:00 --task-duration-min 70 --task-sync-apple
```

- Audit data console:
```bash
python3 main.py --skip-parse --audit
```

- Désactiver agenda Apple Calendar:
```bash
python3 main.py --skip-parse --no-calendar
```

- Désactiver déduplication inter-sources:
```bash
python3 main.py --skip-parse --no-dedup
```

- Arrêter tous les serveurs Bord locaux:
```bash
bash stop_bord.sh
```

## 3) Sorties attendues

- Dashboard: `reports/dashboard_YYYY-MM-DD.html`
- DB SQLite: `athlete.db`
- Logs sync Garmin auto: `garmin_sync.log`
- API planner (mode serveur): `/api/planner/...`

## 4) Apple Calendar (permission macOS)

Si le script affiche `calendar_permission_denied`:

1. Ouvrir `Réglages Système`
2. Aller à `Confidentialité et sécurité > Calendriers`
3. Autoriser le terminal utilisé (Terminal, iTerm ou app Python)
4. Relancer:
```bash
python3 main.py --skip-parse
```

## 5) Exécution automatique Garmin

Installation complète (sync historique + LaunchAgent quotidien):

```bash
bash setup_autorun.sh
```

## 6) Contrôle santé rapide (checklist)

```bash
python3 main.py --skip-parse --audit --weeks-muscle 8
```

Vérifier:

- `health_metrics` continue d'augmenter dans l'audit
- `calendar_events` > 0 si permission accordée
- `ACWR` pas constamment à 0 sauf vraie phase repos
- `Muscle Score` cohérent avec les séances récentes

## 7) Dépannage

- `fitparse manquant`:
```bash
python3 -m pip install fitparse --break-system-packages
```

- `eventkit_unavailable`:
```bash
python3 -m pip install pyobjc-framework-EventKit --break-system-packages
```

- `Garmin non connecté`:
  - Vérifier `.env` (`GARMIN_EMAIL`, `GARMIN_PASSWORD`)
  - Tester `python3 garmin_sync_full.py --from 2025-01-01`

## 8) Sauvegarde locale (recommandé)

Pour avoir une sauvegarde locale robuste (code + DB + dashboard), lance:

```bash
bash backup_local.sh
```

Le script crée un snapshot horodaté dans `backups/YYYYMMDD_HHMMSS/` avec:

- `source_head.tar.gz` (code du dernier commit)
- `git_diff.patch` (modifs locales non commit)
- `athlete.db` (backup SQLite cohérent)
- dernier dashboard `reports/dashboard_*.html`
- `metadata.txt`

Bonne pratique:

- exécuter `backup_local.sh` avant toute grosse refonte
- exécuter `backup_local.sh` avant `--reset`
- garder les secrets dans `.env` (déjà gitignoré)
