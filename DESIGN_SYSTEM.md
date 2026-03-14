# Design System — Bord v4

> Version : 1.0 | Date : 2026-03-05 | Stack : Python-generated Modern HTML

---

## 1. Palette de couleurs

### Couleurs de base (Dark Premium)

```css
:root {
  /* Surfaces */
  --bg:          #0a0e1a;
  --surface-0:   rgba(255,255,255,0.03);
  --surface-1:   rgba(255,255,255,0.06);
  --surface-2:   rgba(255,255,255,0.10);
  --surface-3:   rgba(255,255,255,0.14);

  /* Bordures */
  --border:      rgba(255,255,255,0.08);
  --border-hover:rgba(255,255,255,0.16);
  --border-focus:rgba(59,130,246,0.5);

  /* Texte */
  --text:        #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted:  #64748b;
  --text-inverse:#0f172a;

  /* Accent */
  --accent:      #3b82f6;
  --accent-hover:#2563eb;
  --accent-muted:rgba(59,130,246,0.15);
}
```

### Couleurs semantiques (Domaines)

```css
:root {
  /* Domaines Bord */
  --sante:         #22c55e;
  --sante-bg:      rgba(34,197,94,0.10);
  --travail:       #3b82f6;
  --travail-bg:    rgba(59,130,246,0.10);
  --social:        #ec4899;
  --social-bg:     rgba(236,72,153,0.10);
  --apprentissage: #f59e0b;
  --apprentissage-bg: rgba(245,158,11,0.10);
  --autre:         #64748b;

  /* Statuts */
  --success:     #22c55e;
  --warning:     #f59e0b;
  --danger:      #ef4444;
  --info:        #3b82f6;
}
```

---

## 2. Typographie

**Police** : Inter (Google Fonts)

| Usage | Taille | Poids | Letter-spacing |
|-------|--------|-------|---------------|
| H1 Brand | 28px | 800 | -0.03em |
| H2 Section | 16px | 700 | -0.01em |
| H3 Card | 14px | 700 | -0.01em |
| Body | 13px | 500 | 0 |
| Small / meta | 12px | 500 | 0 |
| Caption / label | 11px | 600 | 0.04em |
| Micro / badge | 10px | 700 | 0.06em |
| KPI value | 22px | 800 | -0.02em |
| KPI value (large) | 32px | 800 | -0.03em |

---

## 3. Spacing (base 4px)

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
}
```

| Usage | Token |
|-------|-------|
| Gap entre items | `--space-2` (8px) |
| Padding card | `--space-4` (16px) |
| Gap entre cards | `--space-3` (12px) |
| Margin section | `--space-4` (16px) |
| Padding bouton | `--space-2 --space-3` (8px 12px) |

---

## 4. Border Radius

```css
:root {
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 999px;
}
```

| Usage | Token |
|-------|-------|
| Bouton, badge | `--radius-sm` |
| Card secondaire, input | `--radius-md` |
| Card principale | `--radius-lg` |
| Hero section | `--radius-xl` |
| Pill, progress bar | `--radius-full` |

---

## 5. Ombres

```css
:root {
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.15);
  --shadow-md: 0 8px 24px rgba(0,0,0,0.25);
  --shadow-lg: 0 12px 32px rgba(0,0,0,0.45);
  --shadow-glow: 0 0 20px rgba(59,130,246,0.15);
}
```

---

## 6. Composants

### 6.1 TopBar (Header)

```
┌─────────────────────────────────────────────────────────────────┐
│ [Totem] [Simsam · date] | [Sante ▪] [Sport ▪] [Travail ▪] [Social ▪] | [Sync] [Debug] │
└─────────────────────────────────────────────────────────────────┘
```

- Classe : `.top-bar`
- Background : `var(--surface-1)` + `backdrop-filter: blur(20px)`
- Border : `1px solid var(--border)`
- Radius : `var(--radius-lg)`
- Layout : `display: flex; align-items: center; justify-content: space-between`

### 6.2 KpiCard (dans le header)

```
┌──────────┐
│ 🫀 Sante │
│ 75/100 ↑ │
└──────────┘
```

- Classe : `.kpi-pill`
- Padding : `8px 12px`
- Background : `var(--surface-1)`
- Border : `1px solid var(--border)`
- Radius : `var(--radius-sm)`
- Contenu : `icon + label + valeur + tendance`

### 6.3 IndicatorStrip (remplace les anneaux)

```
┌─────────────────────────────────────────────────────┐
│ 🫀 Readiness   75/100  ████████████░░░░             │
│ 🏃 Charge      2.0/6.0h ████████░░░░░░░            │
│ 💼 Travail     0.5/20h  █░░░░░░░░░░░░░             │
└─────────────────────────────────────────────────────┘
```

- Classe : `.indicator-strip`
- Layout : `display: flex; flex-direction: column; gap: 10px`
- Background : `var(--surface-0)`
- Padding : `16px`
- Radius : `var(--radius-lg)`

### 6.4 IndicatorCard (barre individuelle)

- Classe : `.indicator-card`
- Layout : `display: grid; grid-template-columns: 140px 1fr 60px; align-items: center`
- Barre : `.progress-track` (h:10px, radius:full, bg:surface-2) + `.progress-fill` (couleur domaine)

### 6.5 SectionCard

- Classe : `.card` (existante, conservee)
- Background : `var(--surface-1)` + `backdrop-filter: blur(20px)`
- Padding : `var(--space-4)`
- Radius : `var(--radius-lg)`
- Shadow : `var(--shadow-lg)`
- Hover : `translateY(-1px)` + shadow augmente

### 6.6 IdeaCard (dans l'Inbox)

```
┌───────────────────────────────────┐
│ Lancer offre IA PME              │
│ [💼 Travail] [→ Planifier] [✕]   │
└───────────────────────────────────┘
```

- Classe : `.idea-item` (existante, amelioree)
- Pill categorie avec couleur domaine
- Bouton "Planifier" visible
- Handle drag-drop

### 6.7 DayCol (Planning)

- Min-height : `400px` (vs 300px avant)
- Indicateur aujourd'hui : `border: 2px solid var(--accent)` + badge
- Events : `border-left-color` prend la couleur categorie

---

## 7. Patterns de layout

### Pilotage (page principale)

```
┌──────────────────────────────────────────────────────┐
│                    TopBar                              │
├──────────────────────────────────────────────────────┤
│                  IndicatorStrip                       │
├──────────────────────────────────────────────────────┤
│ [Pilotage] [Sante] [Travail] [Social]                │
├────────────────────────┬─────────────────────────────┤
│    Weekly Planner      │    Sidebar                   │
│    (60%)               │    (40%)                     │
│    7 DayCols           │    TSB/ACWR KPIs             │
│                        │    Donut categories           │
│                        │    Goal bar sport             │
├────────────────────────┴─────────────────────────────┤
│              Inbox — Kanban Board (100%)              │
│    [Urgent] [A planifier] [Non urgent] [Done]        │
├──────────────────────────────────────────────────────┤
│              Raccourcis rapides                       │
│    [Stats Travail] [Prospection] [Planning social]   │
└──────────────────────────────────────────────────────┘
```

---

## 8. Animations

| Animation | Propriete | Duree | Easing |
|-----------|-----------|-------|--------|
| Card hover | transform + shadow | 180ms | ease |
| Ring fill | stroke-dashoffset | 1.4s | cubic-bezier(0.4,0,0.2,1) |
| Progress bar fill | width | 800ms | cubic-bezier(0.4,0,0.2,1) |
| Totem float | translateY | 2.2s | ease-in-out |
| Toast appear | opacity + transform | 220ms | ease |
| Tab switch | background + color | 150ms | ease |

---

## 9. Responsive

| Breakpoint | Comportement |
|-----------|--------------|
| > 1200px | Layout complet 2 colonnes |
| 900-1200px | Planning pleine largeur, sidebar collapse |
| < 900px | Tout empile, planning scroll horizontal |

---

## 10. Accessibilite

- Contraste texte : `#f1f5f9` sur `#0a0e1a` = ratio 15.4:1 (AAA)
- Focus visible : `outline: 2px solid var(--accent)` + `outline-offset: 2px`
- Aria-labels sur boutons icon-only (Debug, Sync)
- Prefer-reduced-motion : desactiver animations ring/float
