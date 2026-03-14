# Bord — Guide Claude in Chrome

Ce document décrit la structure du dashboard Bord pour permettre à Claude in Chrome de naviguer et interagir efficacement.

## Navigation principale

La barre de navigation est identifiable via `[data-section="navigation"]`.

| Onglet   | URL        | `data-nav`  | Description                     |
|----------|------------|-------------|---------------------------------|
| Semaine  | `/semaine` | `semaine`   | Vue hebdomadaire (page par défaut) |
| Santé    | `/sante`   | `sante`     | Métriques santé et readiness    |
| Travail  | `/travail` | `travail`   | Suivi temps de travail          |
| Social   | `/social`  | `social`    | Événements sociaux              |
| Idées    | `/idees`   | `idees`     | Capture et gestion d'idées      |

**Naviguer** : cliquer sur `[data-nav="sante"]` pour aller à la page Santé.
L'onglet actif porte `aria-current="page"`.

---

## Pages et sections

### /semaine (Page Semaine)

| Section               | `data-section`        | Description                              |
|-----------------------|-----------------------|------------------------------------------|
| Readiness santé       | `readiness-sante`     | Score readiness avec jauge radiale       |
| Heures par domaine    | `heures-domaine`      | Répartition heures par catégorie         |
| Graphiques            | `graphiques`          | Charts volume hebdo et PMC              |
| Événements et tâches  | `evenements-taches`   | Timeline semaine + backlog kanban        |

Sous-sections imbriquées :
- `[data-section="timeline-semaine"]` — Timeline des événements par jour
- `[data-section="board-backlog"]` — Kanban des tâches par priorité

Attributs utiles :
- `[data-metric]` sur les pills de domaine (ex: `data-metric="sport"`)
- `[data-day="lun"]` sur chaque jour de la timeline
- `[data-event-id]` sur chaque événement
- `[data-task-id]` sur chaque tâche du backlog

### /sante (Page Santé)

| Section               | `data-section`         | Description                         |
|-----------------------|------------------------|-------------------------------------|
| Readiness et anneaux  | `readiness-anneaux`    | Score readiness + 3 anneaux        |
| Métriques santé       | `metriques-sante`      | HRV, FC repos, sommeil, VO2max...  |
| Running stats         | `running-stats`        | Allure, km/sem, prédictions        |
| Activités récentes    | `activites-recentes`   | Liste des dernières activités      |

Attributs utiles :
- `[data-metric="allure"]`, `[data-metric="km-semaine"]`, `[data-metric="prediction-*"]`
- `[data-activity-id]`, `[data-activity-type]` sur chaque activité

### /travail (Page Travail)

| Section               | `data-section`          | Description                        |
|-----------------------|-------------------------|------------------------------------|
| Métriques travail     | `metriques-travail`     | Heures travaillées, focus, réunions|
| Barre de progression  | `progression-objectif`  | Progression vers objectif hebdo    |
| Événements travail    | `evenements-travail`    | Liste des événements de travail    |

Attributs utiles :
- `[data-metric]` sur chaque métrique (ex: `data-metric="heures-travail"`)
- `role="progressbar"` avec `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- `[data-event-id]`, `[data-event-category]` sur chaque événement

### /social (Page Social)

| Section               | `data-section`           | Description                      |
|-----------------------|--------------------------|----------------------------------|
| KPI social            | `kpi-social`             | Heures sociales de la semaine    |
| Événements sociaux    | `evenements-sociaux`     | Liste des événements sociaux     |

Attributs utiles :
- `[data-metric="heures-sociales"]`
- `[data-event-id]`, `[data-event-category="social"]` sur chaque événement

### /idees (Page Idées)

| Section               | `data-section`       | Description                        |
|-----------------------|----------------------|------------------------------------|
| Capture idée          | `capture-idee`       | Formulaire de saisie d'idée       |
| Liste des idées       | `liste-idees`        | Toutes les idées existantes        |

---

## Formulaires

### Formulaire de capture d'idée (`/idees`)

Identifié par `[data-form="capture-idee"]`.

| Champ     | `htmlFor` / `id`  | Type     | Description              |
|-----------|--------------------|----------|--------------------------|
| Titre     | `idea-title`       | text     | Titre de l'idée          |
| Catégorie | `idea-category`    | select   | Catégorie (domaine)      |

**Action** : bouton `[data-action="creer-idee"]` avec `aria-label="Ajouter l'idée"`.

---

## Actions disponibles par page

| Page     | Action              | `data-action`    | Description                         |
|----------|---------------------|------------------|-------------------------------------|
| /idees   | Créer une idée      | `creer-idee`     | Soumet le formulaire de capture     |

---

## Composants réutilisables

### ReadinessGauge
- `[data-section="readiness-gauge"]` — conteneur principal
- `[data-value="readiness-label"]` — label du score (ex: "Bon")
- `[data-value="readiness-confidence"]` — pourcentage de confiance
- `[data-component="sleep"]` etc. — composantes du score

### EventTimeline
- `[data-section="timeline-semaine"]`
- `[data-day="lun"]` ... `[data-day="dim"]` — jours de la semaine
- `[data-event-id]`, `[data-event-category]` sur chaque événement

### BoardKanban
- `[data-section="board-backlog"]`
- `[data-triage-group="urgent"]` etc. — groupes par priorité
- `[data-task-id]`, `[data-task-title]`, `[data-task-category]`, `[data-task-status]`

### EventList
- `[data-section="evenements-semaine"]`
- `[data-event-id]`, `[data-event-category]` sur chaque événement

---

## Exemples de prompts pour Claude in Chrome

### Navigation
> "Clique sur l'onglet Santé pour voir mes métriques de santé."

### Lecture de données
> "Lis le score de readiness dans la section [data-section='readiness-anneaux'] et dis-moi si je suis en forme."

### Créer une idée
> "Va sur la page Idées, remplis le formulaire avec le titre 'Préparer marathon' et la catégorie 'sport', puis clique sur le bouton Ajouter."

### Analyser la semaine
> "Sur la page Semaine, regarde la timeline et dis-moi combien d'événements j'ai mardi."

### Vérifier les tâches urgentes
> "Regarde le backlog dans [data-triage-group='urgent'] et liste-moi les tâches urgentes."

### Suivi travail
> "Va sur la page Travail et lis la barre de progression pour savoir où j'en suis par rapport à mon objectif hebdo."
