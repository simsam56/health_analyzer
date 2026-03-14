# 🎯 PerformOS - Guide de lancement

## ✅ Méthodes de lancement (essayez dans l'ordre)

### 1️⃣ Lanceur Terminal (Recommandé)
**Double-cliquez** sur `PerformOS_Terminal` sur votre bureau.
- ✅ Ouvre automatiquement une fenêtre Terminal
- ✅ Affiche les messages de progression
- ✅ Plus fiable que l'app .app

### 2️⃣ Application Desktop
**Double-cliquez** sur `PerformOS_Simple.app` sur votre bureau.
- ✅ Interface native macOS
- ✅ Lancement silencieux (si elle fonctionne)

### 3️⃣ Script Direct (Solution de secours)
**Double-cliquez** sur `PerformOS_Lancer` sur votre bureau.
- ✅ Lanceur simple et direct
- ✅ Interface utilisateur basique

## 🌐 Accès Web

Une fois lancé, ouvrez : **http://127.0.0.1:8765**

**✅ L'URL racine fonctionne maintenant !** Le serveur crée automatiquement un lien vers le dernier dashboard généré et sert directement ce fichier (plus de 404).

## 📋 Fonctionnalités

- 📊 Dashboard interactif avec analyses sportives
- 🏃 Synchronisation Garmin Connect
- 📅 Intégration calendrier Apple
- 💾 Base de données avec 28K+ enregistrements
- 📈 Rapports de santé automatiques

## 🔑 Permissions (si demandé)

### 🗓️ Calendrier Apple
Au premier lancement, une boîte de dialogue apparaîtra pour autoriser l'accès au calendrier :

1. **Cliquez sur "Autoriser"** dans la boîte de dialogue système
2. Si vous avez refusé par erreur :
   - Allez dans **Préférences Système** > **Sécurité et confidentialité** > **Confidentialité**
   - Cliquez sur **Calendriers** dans la barre latérale
   - Cherchez **Python** ou **PerformOS** et activez l'accès

### 🔄 Configuration Automatique
PerformOS configure automatiquement les permissions au premier lancement.

## 🆘 Dépannage

### Erreur 404 sur la page d'accueil
Si vous obtenez une erreur 404, le lien vers le dashboard n'est pas créé :
```bash
# Régénérer le lien dashboard
./update_dashboard_link.sh
```

### Problème de calendrier
```bash
# Configuration manuelle du calendrier
python3 setup_calendar.py
```

### Vérification complète
```bash
# Test de tous les composants
./final_check.sh
```

### Jeton API
Au lancement avec `PerformOS_Terminal` ou `server_simple.py`, le jeton
utilisé pour authentifier les appels POST (`/api/planner/...`) est affiché
dans la console. Il correspond à la valeur stockée dans
`reports/dashboard.html` et peut être fixé via la variable
`PERFORMOS_API_TOKEN`.

---

**PerformOS v3.0** - Prêt à l'emploi ! 🚀
