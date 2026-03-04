# PerformOS Cockpit — Audit Complet (2026-03-04)

## 1) Audit Architecture

- Pipeline global cohérent: `pipeline/*` (ingestion) → `analytics/*` (calculs) → `dashboard/generator.py` (UI HTML) → `cockpit_server.py` (API locale).
- Point d'entrée unique clair: [`main.py`](/Users/simonhingant/Documents/health_analyzer/main.py).
- Forces:
  - ingestion multi-sources Apple/Strava/Garmin/Calendar opérationnelle,
  - base SQLite unifiée,
  - mode serveur interactif (`--serve`) avec persistance planner.
- Faiblesses:
  - couplage fort entre génération HTML et logique JS embarquée dans le template,
  - peu de tests automatisés end-to-end.

## 2) Audit UX / Produit

- Problème historique confirmé: surcharge métriques et faible hiérarchie visuelle.
- Refonte en place:
  - 3 pages Pilotage / Santé / Progression,
  - planning hebdo central (drag/drop + CRUD),
  - ajout rapide via bouton flottant,
  - vue progression simplifiée (4 courbes clés),
  - page santé clarifiée (KPI + recommandations + charge + module musculaire).
- Points restants:
  - manque de vue “jour détaillé” (timeline horaire),
  - pas de notifications intelligentes (surcharge/récup).

## 3) Audit Data

- Observé en base:
  - activités multi-sources agrégées et dédupliquées,
  - métriques santé Apple/Garmin présentes sur plusieurs années,
  - musculation disponible via `strength_sessions` + `exercise_sets`.
- Risques qualité:
  - variabilité de fraîcheur selon métrique (ex: HRV parfois ancienne),
  - dépendance aux noms d’exercices/métadonnées des montres pour la finesse musculaire.
- Correctifs déjà actifs:
  - dédup inter-sources,
  - score et alertes musculaires basés sur volumes hebdo.

## 4) Audit Sécurité

- Améliorations appliquées:
  - protection des endpoints d’écriture planner par token API (`X-PerformOS-Token`) en mode serveur,
  - validation stricte des dates début/fin,
  - plafonds de taille payload et longueur texte,
  - échappement HTML côté front pour éviter XSS sur titres d’événements,
  - headers `Cache-Control: no-store` et `X-Content-Type-Options: nosniff`.
- Risques restants:
  - secrets `.env` en local: rester strictement non versionnés,
  - API locale non chiffrée (acceptable en localhost, non exposer sur réseau public).

## 5) Audit Performance

- Point positif: SQLite + index déjà présents sur dimensions majeures.
- Front:
  - rendu planning performant sur fenêtre hebdo,
  - graphiques Chart.js légers.
- Backend:
  - opérations planner rapides, adaptées au local.
- Optimisation future:
  - déplacer certains calculs répétitifs en vues matérialisées SQLite (ou table cache journalière).

## 6) Conclusion

PerformOS est passé d’un dashboard “data brute” à un cockpit pilotable.  
La base produit est désormais solide pour la phase suivante: coaching adaptatif, meilleure précision musculation, et automatisations multi-domaines (travail/relationnel).
