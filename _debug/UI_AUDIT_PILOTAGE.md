# Audit UI/UX — Page Pilotage (PerformOS v3)

> Date : 2026-03-05 | Auteur : Claude Code | Score UX : 5.5/10

---

## 1. Problemes critiques (P0)

### 1.1 Header confus — metriques brutes non actionnables
- **Composant** : `.top-new > .hero-metrics` (L.1268-1303)
- **Probleme** : 4 cartes RHR/HRV/Sommeil/Battery affichent des valeurs medicales brutes (ex: "52 bpm", "38 ms") sans contexte ni action
- **Impact** : L'utilisateur ne sait pas quoi faire de "HRV 38ms" — c'est bien ? mauvais ?
- **Inspiration** : Oura montre un score Readiness/100, WHOOP affiche Recovery % avec couleur
- **Recommandation** : Remplacer par 4 KPIs domaine (Sante/Sport/Travail/Social) avec score actionnable + tendance

### 1.2 Anneaux redondants avec le header
- **Composant** : `.hero-rings` (L.1305-1352)
- **Probleme** : Recuperation/Activite/Sommeil re-affichent des donnees deja dans le header (Readiness = Battery, Activite = sport, Sommeil = sleep_h)
- **Impact** : Double affichage = confusion, espace gaspille
- **Recommandation** : Remplacer par 3 barres de progression horizontales (Readiness, Charge sport, Travail) — plus lisibles, moins d'espace

### 1.3 Inbox trop petite et comprimee
- **Composant** : `.planning-secondary > .card:first-child` (L.1374-1405)
- **Probleme** : L'inbox est dans la sidebar droite (40% largeur), les cartes kanban sont minuscules
- **Impact** : Impossible de lire les titres longs, pas d'espace pour le drag-drop
- **Recommandation** : Passer l'Inbox en pleine largeur SOUS le planning (layout vertical)

---

## 2. Problemes importants (P1)

### 2.1 Layout sidebar inutilement compact
- **Composant** : `.grid-planning` (L.1362)
- **Probleme** : Le layout est en `grid-template-columns: 1fr` mais le design melange planning + sidebar en colonne unique
- **Impact** : Pas d'utilisation optimale de l'espace horizontal disponible (1540px max)
- **Recommandation** : Grid 2 colonnes `[Planning 60%] [KPIs/Donut/Goal 40%]` + Inbox pleine largeur dessous

### 2.2 Labels de colonnes kanban flous
- **Composant** : Decision grid lanes (urgent/planifier/non_urgent/done)
- **Probleme** : Les labels sont en majuscules generiques, pas de compteur d'items
- **Recommandation** : Ajouter badge compteur + descriptions courtes

### 2.3 Couleurs des events peu differenciees
- **Composant** : `.event` (L.656-670)
- **Probleme** : border-left generique `#9ca3af`, la couleur de categorie n'est pas assez visible
- **Recommandation** : border-left prend la couleur categorie + pill badge visible

### 2.4 Planning trop court
- **Composant** : `.day-col` (L.626-633)
- **Probleme** : `min-height: 300px` — insuffisant pour voir plus de 3-4 events
- **Recommandation** : Passer a `min-height: 400px`, ajouter indicateur "Aujourd'hui" (bordure accent)

---

## 3. Ameliorations souhaitables (P2)

### 3.1 Pas d'indicateur jour actuel
- Le planning n'a aucune distinction visuelle pour "aujourd'hui"
- **Recommandation** : Border accent bleue + badge "Aujourd'hui" dans le day-head

### 3.2 Section Travail/Social trop basiques
- Les onglets Travail et Social sont fonctionnels mais minimalistes
- **Recommandation** : Ajouter raccourcis vers ces sections depuis Pilotage

### 3.3 Typographie heterogene
- Tailles de texte variables sans echelle coherente
- **Recommandation** : Definir une echelle typographique (11/12/13/14/16/20/24/32px)

### 3.4 Aucune animation d'entree
- Le contenu apparait d'un bloc sans transition
- **Recommandation** : Ajouter des fade-in staggers sur les cards

---

## 4. Points forts a conserver

| Element | Qualite |
|---------|---------|
| Dark glassmorphism | Excellent — backdrop-filter, radial gradients, rgba layers |
| Totem mascot (renard) | Charme et personnalite — garder l'animation wiggle |
| Drag-and-drop inbox→planning | Fonctionnel et intuitif (SortableJS) |
| 4 onglets navigation | Structure claire Pilotage/Sante/Travail/Social |
| Debug panel | Utile pour le dev — garder accessible |
| Donut categories | Bonne vue d'ensemble — canvas DPR-aware |
| Goal bar sport | Motivation visuelle — garder le design |
| Trend charts (Chart.js) | Bon feedback sur 4 semaines |

---

## 5. Plan de refonte cible

```
AVANT (v3)                          APRES (v4)
========================            ========================
[RHR|HRV|Sleep|Battery]             [Sante 75↑|Sport 33%|Travail 0.5h|Social --]
[O Recup][O Activ][O Sommeil]       [━━━ Readiness][━━━ Charge][━━━ Travail]
[Planning ][Sidebar ]               [Planning 60%  ][KPIs 40%  ]
            [Inbox  ]               [━━━━━━ Inbox pleine largeur ━━━━━━]
```

---

## 6. Inspirations design

| Produit | Ce qu'on prend |
|---------|---------------|
| **Linear** | Dark UI, sidebar compacte, animations subtiles, typographie Inter |
| **Vercel Dashboard** | Cards epurees, spacing genereux, badges statut |
| **Oura Ring** | Score /100 avec couleur, tendance fleche, cercle de progression |
| **WHOOP** | Recovery %, strain %, couleurs vert/jaune/rouge |
| **shadcn/ui** | Tokens CSS, radii consistants, glassmorphism dark |
| **Notion** | Kanban board ergonomique, drag-drop fluide |
