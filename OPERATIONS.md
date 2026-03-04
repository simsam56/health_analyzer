# PerformOS v3 - Runbook

Ce document sert de guide d'exploitation rapide (local Mac).

## 1) Installation minimale

```bash
cd ~/Documents/health_analyzer
python3 -m pip install fitparse garminconnect python-dotenv pyobjc-framework-EventKit --break-system-packages
```

## 2) Commandes principales

- Run complet (parse + dédup + dashboard + agenda):
```bash
python3 main.py --garmin --days 90
```

- Run rapide (sans reparse):
```bash
python3 main.py --skip-parse
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

## 3) Sorties attendues

- Dashboard: `reports/dashboard_YYYY-MM-DD.html`
- DB SQLite: `athlete.db`
- Logs sync Garmin auto: `garmin_sync.log`

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
