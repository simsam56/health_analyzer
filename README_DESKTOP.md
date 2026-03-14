# 🚀 PerformOS - Guide d'utilisation

## Icône Bureau Créée ✅

Une application **PerformOS.app** a été créée sur votre bureau avec :

### 🎯 Lancement Rapide
- **Double-cliquez** sur l'icône PerformOS.app
- Interface web s'ouvre automatiquement
- Calendrier Apple synchronisé

### 🗓️ Fonctionnalités Calendrier

#### Synchronisation Automatique
- 30 jours d'événements synchronisés
- Mise à jour en temps réel
- Intégration avec les tâches planner

#### Modification Rapide
- Créer des événements directement
- Modifier les événements existants
- Synchronisation bidirectionnelle

### 🌐 Interface Web
- **URL** : http://127.0.0.1:8765
- **Planning** : Vue hebdomadaire avec drag & drop
- **Santé** : Métriques et progression
- **Calendrier** : Gestion directe des événements

### 🔧 API Endpoints Disponibles

#### Calendrier
- `GET /api/calendar/status` - État de la connexion
- `GET /api/calendar/events?days=30` - Événements synchronisés
- `POST /api/calendar/sync?days=30` - Synchronisation manuelle
- `POST /api/calendar/create` - Créer un événement

#### Planner
- `POST /api/planner/tasks` - Créer une tâche
- `PATCH /api/planner/tasks/{id}` - Modifier une tâche
- `DELETE /api/planner/tasks/{id}` - Supprimer une tâche

### 📋 Dépannage

#### Calendrier non accessible
```bash
# Vérifier les permissions
Réglages Système > Confidentialité > Calendriers
# Cochez Python/EventKit
```

#### Application ne démarre pas
```bash
# Relancer le setup
cd /Users/simonhingant/Documents/health_analyzer
./setup_desktop.sh
```

#### Reset complet
```bash
# Supprimer et recréer
rm -rf ~/Desktop/PerformOS.app
cd /Users/simonhingant/Documents/health_analyzer
./setup_desktop.sh
```

### 🎉 Prêt à utiliser !

Double-cliquez sur **PerformOS.app** pour commencer !
