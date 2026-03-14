# PerformOS Cockpit — Roadmap Implémentation 2026

## Phase 1 (fait) — Fondation cockpit

- Refonte UI 3 pages:
  - Pilotage (planning central),
  - Santé,
  - Progression.
- CRUD planning complet:
  - ajout, modification, suppression, drag&drop.
- Sync Apple Calendar bidirectionnelle.
- API locale planner intégrée au serveur cockpit.
- Durcissement sécurité API locale (token + validation).

## Phase 2 (prochaine) — Fiabilité data & précision sportive

- Fiabiliser la classification musculation:
  - mapping exercices personnalisé utilisateur,
  - fallback NLP sur noms exotiques (ex: “Full body Dos”).
- Ajouter tests automatisés:
  - parsing,
  - règles de dédup,
  - API planner.
- Améliorer indicateurs:
  - freshness score par métrique (jours depuis dernière mesure),
  - qualité des sources par sport.

## Phase 3 — Coaching intelligent

- Recommandations hebdo actionnables:
  - surcharge,
  - déficit cardio,
  - manque récupération.
- Planification assistée:
  - proposition de microcycle 7 jours auto-généré.
- Alertes et notifications locales:
  - “objectif sport en retard”,
  - “charge trop élevée”.

## Phase 4 — Extension cockpit de vie

- Ajout interfaces Travail / Relationnel (planning partagé).
- Automatisations ciblées:
  - relances pros,
  - objectifs hebdo multi-domaines.
- Vue globale “équilibre de vie”:
  - santé vs travail vs relationnel vs apprentissage.
