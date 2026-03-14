# 🚨 DÉPANNAGE PerformOS - MacBook Pro M5

## Problème: Application ne s'ouvre pas

### 🔍 DIAGNOSTIC RAPIDE

#### 1. Vérifier l'environnement
```bash
cd /Users/simonhingant/Documents/health_analyzer
python3 test_launch.py
```

#### 2. Vérifier les permissions
```bash
# Calendrier
Réglages Système > Confidentialité > Calendriers > Python
# Doit être coché

# Terminal (si nécessaire)
Réglages Système > Confidentialité > Automatisation > Terminal
```

#### 3. Vérifier les dépendances
```bash
cd /Users/simonhingant/Documents/health_analyzer
pip install -r requirements.txt
```

### 🛠️ SOLUTIONS

#### Solution 1: Version Simplifiée
```bash
cd /Users/simonhingant/Documents/health_analyzer
./create_simple_app.sh
# Crée PerformOS_Simple.app sur le bureau
```

#### Solution 2: Lancement Direct
```bash
cd /Users/simonhingant/Documents/health_analyzer
python3 main.py --serve --calendar-days 7
```

#### Solution 3: Reset Complet
```bash
cd /Users/simonhingant/Documents/health_analyzer

# Supprimer les anciennes apps
rm -rf ~/Desktop/PerformOS*.app

# Réinstaller les dépendances
pip install --upgrade -r requirements.txt

# Recréer l'app
./create_simple_app.sh

# Tester
python3 test_launch.py
```

### 📋 VÉRIFICATIONS

#### Fichiers requis:
- ✅ `main.py` (script principal)
- ✅ `athlete.db` (base de données)
- ✅ `requirements.txt` (dépendances)
- ✅ `quick_launch.py` (lanceur)

#### Dépendances Python:
- ✅ `sqlite3` (base de données)
- ✅ `defusedxml` (parsing sécurisé)
- ✅ `joblib` (cache)
- ⚠️ `pyobjc-framework-EventKit` (calendrier)

#### Permissions macOS:
- ✅ Calendrier: Python doit avoir accès
- ✅ Terminal: Si utilisé pour le lancement

### 🚀 LANCEMENT MANUEL

Si l'icône ne fonctionne pas, lancez manuellement:

```bash
# Terminal
cd /Users/simonhingant/Documents/health_analyzer
python3 main.py --serve --calendar-days 7 --serve-port 8765

# Puis ouvrir dans navigateur:
open http://127.0.0.1:8765
```

### 📞 SUPPORT

Si rien ne fonctionne:

1. **Vérifiez les logs** dans le terminal lors du lancement
2. **Testez** `python3 test_launch.py` pour diagnostiquer
3. **Réinstallez** les dépendances: `pip install -r requirements.txt`
4. **Vérifiez** les permissions dans Réglages Système

### 🎯 RACCourcis

- **Lancement rapide**: `python3 quick_launch.py`
- **Test diagnostic**: `python3 test_launch.py`
- **Serveur simple**: `./launch_simple.sh`
- **Créer icône**: `./create_simple_app.sh`
