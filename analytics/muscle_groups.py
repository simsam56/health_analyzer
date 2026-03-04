"""
muscle_groups.py — Analyse des groupes musculaires

Calcule :
  - Volume hebdomadaire par muscle (sets, reps)
  - Déséquilibres détectés (agoniste/antagoniste, sous-entraînement)
  - Recommandations hypertrophie (sets/semaine cible)
  - Score de balance musculaire

Références science de l'entraînement :
  - Schoenfeld (2017) : 10-20 sets/semaine pour hypertrophie optimale
  - Agoniste/Antagoniste : ratio Pecs/Dos idéal = 0.8-1.2
  - Volume mollets souvent négligé : minimum 6 sets/semaine
"""
import sqlite3
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "athlete.db"

# ─────────────────────────────────────────────────────────────────
# RECOMMANDATIONS VOLUME HEBDOMADAIRE (sets/semaine)
# ─────────────────────────────────────────────────────────────────
VOLUME_TARGETS = {
    "Pecs":     {"min": 8,  "hyper": 12, "max": 20, "icon": "💪"},
    "Dos":      {"min": 10, "hyper": 14, "max": 22, "icon": "🔙"},
    "Épaules":  {"min": 8,  "hyper": 12, "max": 20, "icon": "🦋"},
    "Biceps":   {"min": 6,  "hyper": 10, "max": 16, "icon": "💪"},
    "Triceps":  {"min": 6,  "hyper": 10, "max": 16, "icon": "🔱"},
    "Jambes":   {"min": 12, "hyper": 16, "max": 24, "icon": "🦵"},
    "Core":     {"min": 8,  "hyper": 12, "max": 20, "icon": "⭕"},
}

# Paires agoniste/antagoniste pour équilibre
AGONIST_PAIRS = [
    ("Pecs",  "Dos",     "Pecs/Dos",      (0.6, 0.9)),   # ratio Pecs:Dos idéal
    ("Biceps","Triceps", "Biceps/Triceps", (0.7, 1.3)),   # ratio proche de 1:1
]

# Seuils d'alerte
ALERT_THRESHOLDS = {
    "critique":   0.4,   # < 40% du minimum → alerte rouge
    "faible":     0.7,   # 40-70% du minimum → alerte orange
    "ok":         1.0,   # 70-100% du minimum → acceptable
    "optimal":    1.3,   # 100-130% → optimal
    "excessif":   1.5,   # > 150% → risque surentraînement
}


# ─────────────────────────────────────────────────────────────────
# FONCTIONS D'ANALYSE
# ─────────────────────────────────────────────────────────────────

def get_weekly_volume(
    conn: sqlite3.Connection,
    weeks: int = 8,
    end_date: date | None = None,
) -> dict[str, dict[str, dict]]:
    """
    Retourne le volume par semaine et groupe musculaire.

    Structure retournée :
    {
      "2025-W45": {
        "Pecs": {"sets": 12, "reps": 96, "sessions": 2},
        "Dos":  {"sets": 14, "reps": 112, "sessions": 2},
        ...
      },
      ...
    }
    """
    if end_date is None:
        end_date = date.today()

    start_date = end_date - timedelta(weeks=weeks)

    rows = conn.execute("""
        SELECT
            es.started_at,
            es.muscle_group,
            COUNT(es.id)        AS sets,
            SUM(COALESCE(es.reps, 0)) AS reps,
            COUNT(DISTINCT es.session_id) AS sessions
        FROM exercise_sets es
        WHERE es.muscle_group NOT IN ('Inconnu', 'Cardio')
          AND es.muscle_group IS NOT NULL
          AND date(es.started_at) >= ?
          AND date(es.started_at) <= ?
          AND es.set_type = 'active'
        GROUP BY
            strftime('%Y-W%W', es.started_at),
            es.muscle_group
    """, (str(start_date), str(end_date))).fetchall()

    weekly: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: {"sets": 0, "reps": 0, "sessions": 0}))

    for row in rows:
        ts_str = row[0] or ""
        try:
            d = date.fromisoformat(ts_str[:10])
            # Lundi de la semaine ISO
            week_start = d - timedelta(days=d.weekday())
            week_key   = week_start.strftime("%Y-%m-%d")
        except ValueError:
            continue

        mg = row[1]
        weekly[week_key][mg]["sets"]     += row[2]
        weekly[week_key][mg]["reps"]     += row[3]
        weekly[week_key][mg]["sessions"] += row[4]

    return {k: dict(v) for k, v in sorted(weekly.items())}


def get_cumulative_volume(
    conn: sqlite3.Connection,
    weeks: int = 4,
    end_date: date | None = None,
) -> dict[str, dict]:
    """
    Volume total par groupe musculaire sur les N dernières semaines.
    Retourne aussi sets/semaine en moyenne.
    """
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    rows = conn.execute("""
        SELECT
            es.muscle_group,
            COUNT(es.id)                   AS total_sets,
            SUM(COALESCE(es.reps, 0))      AS total_reps,
            COUNT(DISTINCT es.session_id)  AS sessions
        FROM exercise_sets es
        WHERE es.muscle_group NOT IN ('Inconnu', 'Cardio')
          AND es.muscle_group IS NOT NULL
          AND date(es.started_at) >= ?
          AND es.set_type = 'active'
        GROUP BY es.muscle_group
        ORDER BY total_sets DESC
    """, (str(start_date),)).fetchall()

    result = {}
    for row in rows:
        mg = row[0]
        total_sets = row[1]
        result[mg] = {
            "total_sets":   total_sets,
            "total_reps":   row[2],
            "sessions":     row[3],
            "sets_per_week": round(total_sets / weeks, 1),
        }

    # Ajouter les muscles non entraînés
    for mg in VOLUME_TARGETS:
        if mg not in result:
            result[mg] = {"total_sets": 0, "total_reps": 0, "sessions": 0, "sets_per_week": 0}

    return result


def analyze_imbalances(
    volume: dict[str, dict],
    weeks: int = 4,
) -> list[dict]:
    """
    Détecte les déséquilibres et retourne une liste d'alertes.

    Chaque alerte :
    {
        "level":   "critique" | "faible" | "ok" | "optimal",
        "type":    "volume" | "balance",
        "muscle":  str,
        "message": str,
        "current": float,   # sets/semaine actuels
        "target":  float,   # sets/semaine cible
        "emoji":   str,
    }
    """
    alerts = []

    # ── 1. Alertes volume absolu ──────────────────────────────────
    for mg, targets in VOLUME_TARGETS.items():
        spw = volume.get(mg, {}).get("sets_per_week", 0)
        min_sets  = targets["min"]
        hyp_sets  = targets["hyper"]
        icon      = targets["icon"]

        if spw == 0:
            level = "critique"
            msg   = f"⛔ {mg} — Aucun entraînement sur {weeks} semaines !"
        elif spw < min_sets * ALERT_THRESHOLDS["critique"]:
            level = "critique"
            msg   = f"🔴 {mg} — Volume très insuffisant : {spw:.1f} sets/sem (min recommandé : {min_sets})"
        elif spw < min_sets * ALERT_THRESHOLDS["faible"]:
            level = "faible"
            msg   = f"🟠 {mg} — Volume faible : {spw:.1f} sets/sem (min recommandé : {min_sets})"
        elif spw < min_sets:
            level = "ok"
            msg   = f"🟡 {mg} — Volume acceptable : {spw:.1f} sets/sem (idéal : {hyp_sets})"
        elif spw <= hyp_sets * ALERT_THRESHOLDS["optimal"]:
            level = "optimal"
            msg   = f"✅ {mg} — Volume optimal : {spw:.1f} sets/sem"
        else:
            level = "excessif"
            msg   = f"⚠️ {mg} — Volume élevé : {spw:.1f} sets/sem (max conseillé : {targets['max']})"

        alerts.append({
            "level":   level,
            "type":    "volume",
            "muscle":  mg,
            "message": msg,
            "current": spw,
            "target":  hyp_sets,
            "icon":    icon,
        })

    # ── 2. Alertes déséquilibres agoniste/antagoniste ──────────────
    for mg_a, mg_b, label, (ratio_min, ratio_max) in AGONIST_PAIRS:
        sets_a = volume.get(mg_a, {}).get("sets_per_week", 0)
        sets_b = volume.get(mg_b, {}).get("sets_per_week", 0)

        if sets_b > 0:
            ratio = sets_a / sets_b
            if ratio < ratio_min:
                alerts.append({
                    "level":   "faible",
                    "type":    "balance",
                    "muscle":  mg_a,
                    "message": f"⚖️ Déséquilibre {label} : ratio {ratio:.2f} (idéal {ratio_min}-{ratio_max}). Entraîner davantage {mg_a}.",
                    "current": ratio,
                    "target":  (ratio_min + ratio_max) / 2,
                    "icon":    "⚖️",
                })
            elif ratio > ratio_max:
                alerts.append({
                    "level":   "faible",
                    "type":    "balance",
                    "muscle":  mg_b,
                    "message": f"⚖️ Déséquilibre {label} : ratio {ratio:.2f} (idéal {ratio_min}-{ratio_max}). Entraîner davantage {mg_b}.",
                    "current": ratio,
                    "target":  (ratio_min + ratio_max) / 2,
                    "icon":    "⚖️",
                })

    # Trier par priorité (critique > faible > ok > optimal)
    level_order = {"critique": 0, "faible": 1, "ok": 2, "optimal": 3, "excessif": 4}
    alerts.sort(key=lambda x: level_order.get(x["level"], 5))

    return alerts


def get_top_exercises(
    conn: sqlite3.Connection,
    weeks: int = 12,
    end_date: date | None = None,
) -> dict[str, list]:
    """
    Retourne les exercices les plus fréquents par groupe musculaire.
    """
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    rows = conn.execute("""
        SELECT
            muscle_group,
            exercise_name,
            exercise_category,
            COUNT(*) AS sets,
            SUM(COALESCE(reps, 0)) AS total_reps
        FROM exercise_sets
        WHERE exercise_name IS NOT NULL
          AND exercise_name NOT IN ('None', 'none')
          AND muscle_group NOT IN ('Inconnu', 'Cardio')
          AND date(started_at) >= ?
          AND set_type = 'active'
        GROUP BY muscle_group, exercise_name
        ORDER BY muscle_group, sets DESC
    """, (str(start_date),)).fetchall()

    by_muscle: dict[str, list] = defaultdict(list)
    for row in rows:
        by_muscle[row[0]].append({
            "exercise":  row[1],
            "category":  row[2],
            "sets":      row[3],
            "total_reps": row[4],
        })

    return dict(by_muscle)


def compute_muscle_score(volume: dict[str, dict]) -> float:
    """
    Score global de balance musculaire (0-100).
    Basé sur le respect des volumes minimums pour chaque groupe.
    """
    scores = []
    for mg, targets in VOLUME_TARGETS.items():
        spw     = volume.get(mg, {}).get("sets_per_week", 0)
        min_s   = targets["min"]
        hyp_s   = targets["hyper"]

        # Score de 0 à 100 pour ce muscle
        if spw == 0:
            s = 0
        elif spw >= hyp_s:
            s = 100
        elif spw >= min_s:
            s = 60 + 40 * (spw - min_s) / (hyp_s - min_s)
        else:
            s = 60 * spw / min_s

        scores.append(s)

    return round(sum(scores) / len(scores), 1)


def get_recent_sessions(
    conn: sqlite3.Connection,
    limit: int = 10,
) -> list[dict]:
    """Retourne les dernières séances de musculation."""
    rows = conn.execute("""
        SELECT
            ss.started_at,
            ss.workout_name,
            ss.total_sets,
            ss.total_reps,
            ss.duration_s,
            GROUP_CONCAT(DISTINCT es.muscle_group) AS muscles
        FROM strength_sessions ss
        LEFT JOIN exercise_sets es
            ON es.session_id = ss.id AND es.muscle_group NOT IN ('Inconnu','Cardio')
        GROUP BY ss.id
        ORDER BY ss.started_at DESC
        LIMIT ?
    """, (limit,)).fetchall()

    sessions = []
    for row in rows:
        muscles = sorted(set(m for m in (row[5] or "").split(",") if m and m != "Inconnu"))
        dur_min = round(row[4] / 60) if row[4] else 0
        sessions.append({
            "date":         row[0][:10] if row[0] else "?",
            "workout_name": row[1],
            "total_sets":   row[2],
            "total_reps":   row[3],
            "duration_min": dur_min,
            "muscles":      muscles,
        })

    return sessions


# ─────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────
def run(
    db_path: Path = DB_PATH,
    weeks:   int  = 4,
    verbose: bool = True,
) -> dict:
    """
    Analyse complète des groupes musculaires.
    Retourne un dict avec toutes les métriques pour le dashboard.
    """
    conn = sqlite3.connect(str(db_path))

    # Volume par semaine
    weekly_vol  = get_weekly_volume(conn, weeks=max(weeks, 8))
    # Volume cumulé (N dernières semaines)
    cum_volume  = get_cumulative_volume(conn, weeks=weeks)
    # Déséquilibres
    imbalances  = analyze_imbalances(cum_volume, weeks=weeks)
    # Top exercices
    top_exercises = get_top_exercises(conn)
    # Score
    score       = compute_muscle_score(cum_volume)
    # Séances récentes
    recent      = get_recent_sessions(conn, limit=8)

    conn.close()

    if verbose:
        print(f"\n📊 Analyse Musculaire ({weeks} dernières semaines)")
        print(f"   Score de balance : {score}/100")
        print()
        print("   Volume (sets/semaine) :")
        for mg, data in cum_volume.items():
            bar_len = min(int(data['sets_per_week'] * 2), 30)
            bar     = "█" * bar_len
            target  = VOLUME_TARGETS.get(mg, {}).get("hyper", 12)
            status  = "✅" if data['sets_per_week'] >= target else ("🟡" if data['sets_per_week'] > 0 else "⛔")
            print(f"   {status} {mg:12} {bar:30} {data['sets_per_week']:.1f}/sem (cible: {target})")
        print()
        print("   Alertes :")
        for a in imbalances[:6]:
            print(f"   {a['message']}")

    return {
        "weekly_volume":  weekly_vol,
        "cumulative":     cum_volume,
        "imbalances":     imbalances,
        "top_exercises":  top_exercises,
        "muscle_score":   score,
        "recent_sessions": recent,
        "weeks_analyzed": weeks,
        "targets":        VOLUME_TARGETS,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--db",    default=str(DB_PATH))
    p.add_argument("--weeks", type=int, default=4)
    args = p.parse_args()
    run(Path(args.db), args.weeks)
