# 🚀 Bord - Guide d'utilisation rapide

## 🎯 Démarrage rapide

1. **Double-cliquez** sur `Bord_Simple.app` sur votre bureau
2. L'application s'ouvre automatiquement dans votre navigateur
3. Le calendrier Apple est synchronisé automatiquement

## 📱 Interface Web

- **URL**: http://127.0.0.1:8765
- **Dashboard**: Vue d'ensemble de vos performances
- **Rapports**: Analyses détaillées de santé
- **Calendrier**: Intégration Apple Calendar

## 🔧 Dépannage

Si l'application ne démarre pas :

```bash
# Vérification complète
./final_check.sh
```

### Jeton API
Le serveur utilise un jeton pour sécuriser les points de terminaison écriture
(POST `/api/planner`). Le jeton est automatiquement extrait du fichier
`reports/dashboard.html` et affiché dans la console au démarrage du
serveur. Vous pouvez aussi définir votre propre jeton en exportant
`BORD_API_TOKEN` avant d'exécuter le lancement simple.


## 📋 Permissions requises

- **Calendrier**: Système Préférences > Sécurité > Calendrier
- **Fichiers**: Accès aux dossiers Documents et Desktop

## 📊 Fonctionnalités

- ✅ Synchronisation Garmin Connect
- ✅ Analyse des entraînements
- ✅ Dashboard interactif
- ✅ Export Strava
- ✅ Intégration calendrier Apple
- ✅ Rapports de santé automatiques

## 🆘 Support

En cas de problème, consultez `TROUBLESHOOTING.md` ou relancez `./final_check.sh`

---

**Bord v3.0** - Application desktop fonctionnelle ✅
