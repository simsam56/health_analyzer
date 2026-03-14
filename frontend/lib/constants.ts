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
