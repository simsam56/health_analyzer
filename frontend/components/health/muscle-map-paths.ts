/**
 * SVG paths simplifié/stylisé type Garmin Connect pour le body map.
 * Chaque path représente un groupe musculaire sur une silhouette minimaliste.
 * viewBox: 0 0 120 300
 */

export interface MusclePath {
  id: string;
  d: string;
  muscle: string;
}

// Vue de face
export const BODY_FRONT_PATHS: MusclePath[] = [
  // Tête (non-interactive, juste silhouette)
  { id: "head-front", d: "M52,8 Q60,0 68,8 Q76,16 68,30 L52,30 Q44,16 52,8 Z", muscle: "" },
  // Cou
  { id: "neck-front", d: "M54,30 L66,30 L64,40 L56,40 Z", muscle: "" },
  // Épaules gauche
  { id: "shoulder-l", d: "M36,42 L56,40 L54,56 L38,54 Q32,48 36,42 Z", muscle: "Épaules" },
  // Épaules droite
  { id: "shoulder-r", d: "M64,40 L84,42 Q88,48 82,54 L66,56 L64,40 Z", muscle: "Épaules" },
  // Pectoraux gauche
  { id: "pec-l", d: "M42,56 L58,54 L58,78 L44,76 Q40,66 42,56 Z", muscle: "Pecs" },
  // Pectoraux droit
  { id: "pec-r", d: "M62,54 L78,56 Q80,66 76,76 L62,78 L62,54 Z", muscle: "Pecs" },
  // Biceps gauche
  { id: "bicep-l", d: "M30,56 L40,54 L38,88 L28,86 Q26,70 30,56 Z", muscle: "Biceps" },
  // Biceps droit
  { id: "bicep-r", d: "M80,54 L90,56 Q94,70 92,86 L82,88 L80,54 Z", muscle: "Biceps" },
  // Abdos
  { id: "abs", d: "M46,78 L74,78 L72,120 L48,120 Z", muscle: "Core" },
  // Avant-bras gauche
  { id: "forearm-l", d: "M26,88 L36,90 L34,126 L24,124 Z", muscle: "" },
  // Avant-bras droit
  { id: "forearm-r", d: "M84,90 L94,88 L96,124 L86,126 Z", muscle: "" },
  // Quadriceps gauche
  { id: "quad-l", d: "M42,122 L56,120 L54,190 L38,188 Q36,155 42,122 Z", muscle: "Jambes" },
  // Quadriceps droit
  { id: "quad-r", d: "M64,120 L78,122 Q84,155 82,188 L66,190 L64,120 Z", muscle: "Jambes" },
  // Tibia/Mollet gauche (vue de face)
  { id: "shin-l", d: "M40,192 L56,192 L52,260 L38,258 Q36,225 40,192 Z", muscle: "Mollets" },
  // Tibia/Mollet droit (vue de face)
  { id: "shin-r", d: "M64,192 L80,192 Q84,225 82,258 L68,260 L64,192 Z", muscle: "Mollets" },
];

// Vue de dos
export const BODY_BACK_PATHS: MusclePath[] = [
  // Tête
  { id: "head-back", d: "M52,8 Q60,0 68,8 Q76,16 68,30 L52,30 Q44,16 52,8 Z", muscle: "" },
  // Cou
  { id: "neck-back", d: "M54,30 L66,30 L64,40 L56,40 Z", muscle: "" },
  // Trapèzes gauche
  { id: "trap-l", d: "M40,40 L58,38 L56,56 L42,54 Q38,46 40,40 Z", muscle: "Dos" },
  // Trapèzes droit
  { id: "trap-r", d: "M62,38 L80,40 Q82,46 78,54 L64,56 L62,38 Z", muscle: "Dos" },
  // Dorsaux gauche
  { id: "lat-l", d: "M38,56 L56,54 L54,90 L40,88 Q36,72 38,56 Z", muscle: "Dos" },
  // Dorsaux droit
  { id: "lat-r", d: "M64,54 L82,56 Q84,72 80,88 L66,90 L64,54 Z", muscle: "Dos" },
  // Triceps gauche
  { id: "tricep-l", d: "M28,56 L38,54 L36,88 L26,86 Q24,70 28,56 Z", muscle: "Triceps" },
  // Triceps droit
  { id: "tricep-r", d: "M82,54 L92,56 Q96,70 94,86 L84,88 L82,54 Z", muscle: "Triceps" },
  // Bas du dos / lombaires
  { id: "lower-back", d: "M44,90 L76,90 L74,120 L46,120 Z", muscle: "Core" },
  // Avant-bras gauche
  { id: "forearm-bl", d: "M24,88 L34,90 L32,126 L22,124 Z", muscle: "" },
  // Avant-bras droit
  { id: "forearm-br", d: "M86,90 L96,88 L98,124 L88,126 Z", muscle: "" },
  // Fessiers gauche
  { id: "glute-l", d: "M42,120 L58,118 L56,148 L40,146 Q38,132 42,120 Z", muscle: "Jambes" },
  // Fessiers droit
  { id: "glute-r", d: "M62,118 L78,120 Q82,132 80,146 L64,148 L62,118 Z", muscle: "Jambes" },
  // Ischio-jambiers gauche
  { id: "ham-l", d: "M38,148 L56,148 L54,210 L36,208 Q34,178 38,148 Z", muscle: "Jambes" },
  // Ischio-jambiers droit
  { id: "ham-r", d: "M64,148 L82,148 Q86,178 84,208 L66,210 L64,148 Z", muscle: "Jambes" },
  // Mollets gauche
  { id: "calf-l", d: "M38,212 L56,212 L52,268 L36,266 Q34,238 38,212 Z", muscle: "Mollets" },
  // Mollets droit
  { id: "calf-r", d: "M64,212 L82,212 Q86,238 84,266 L68,268 L64,212 Z", muscle: "Mollets" },
];

/** All unique muscle names that are interactive */
export const MUSCLE_NAMES = [
  "Pecs", "Épaules", "Biceps", "Triceps", "Core", "Dos", "Jambes", "Mollets",
];
