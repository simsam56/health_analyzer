/**
 * Constantes partagées : couleurs, labels, icônes par catégorie.
 */

import type { Category } from "./types";

export const CATEGORY_COLORS: Record<Category, string> = {
  sport: "var(--color-sport)",
  yoga: "var(--color-yoga)",
  travail: "var(--color-travail)",
  formation: "var(--color-formation)",
  social: "var(--color-social)",
  lecon: "var(--color-lecon)",
  autre: "var(--color-autre)",
};

export const CATEGORY_LABELS: Record<Category, string> = {
  sport: "Sport",
  yoga: "Yoga",
  travail: "Travail",
  formation: "Formation",
  social: "Social",
  lecon: "Leçon",
  autre: "Autre",
};

export const CATEGORY_ICONS: Record<Category, string> = {
  sport: "🏃",
  yoga: "🧘",
  travail: "💼",
  formation: "📚",
  social: "🤝",
  lecon: "🎓",
  autre: "📌",
};

export const TRIAGE_LABELS: Record<string, string> = {
  a_determiner: "À déterminer",
  urgent: "Urgent",
  a_planifier: "À planifier",
  non_urgent: "Non urgent",
  termine: "Terminé",
};

export const TRIAGE_ORDER = [
  "a_determiner",
  "urgent",
  "a_planifier",
  "non_urgent",
  "termine",
] as const;

// ── Grille hebdomadaire ──────────────────────────────────────────

export const HOUR_HEIGHT = 60;
export const GRID_START_HOUR = 6;
export const GRID_END_HOUR = 22;

export const IDEA_CATEGORIES = ["Pro", "Perso", "Projet", "À creuser"] as const;

export const SOURCE_LABELS: Record<string, string> = {
  local: "Bord",
  apple_calendar: "Apple",
  google_calendar: "Google",
};

/** Resolve CSS variable category colors to hex (for non-CSS contexts). */
export const CATEGORY_HEX: Record<Category, string> = {
  sport: "#22c55e",
  yoga: "#a855f7",
  travail: "#3b82f6",
  formation: "#06b6d4",
  social: "#ec4899",
  lecon: "#f59e0b",
  autre: "#64748b",
};
