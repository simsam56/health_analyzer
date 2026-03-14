/**
 * Utilitaires partagés — couleurs domaine, formatage dates.
 */

/** Couleur CSS par catégorie de domaine. */
export function getCategoryColor(cat: string): string {
  const colors: Record<string, string> = {
    sport: "#22c55e",
    yoga: "#a855f7",
    travail: "#3b82f6",
    formation: "#06b6d4",
    social: "#ec4899",
    lecon: "#f59e0b",
    autre: "#64748b",
  };
  return colors[cat] ?? "#64748b";
}

/** Formate un ISO datetime en "lun. 3, 14:30" (fr-FR). */
export function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", {
      weekday: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

/** Formate un ISO date en "3 mars" (fr-FR). */
export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
    });
  } catch {
    return "";
  }
}
