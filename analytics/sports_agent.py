"""
sports_agent.py — Bord · Intelligent Sports Analysis Agent

Analyses performed:
  - Running: trends, pace progression, predictions, consistency score
  - Strength: session frequency, recovery gaps, muscle balance
  - Wakeboard/Tennis/Snow: sport-specific insights
  - Recovery: composite score from Garmin metrics
  - Weekly summary: AI-style narrative insights
  - Recommendations: prioritized, actionable, with severity
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────


def _conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _to_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _days_ago(d: date | None) -> int:
    if d is None:
        return 9999
    return (date.today() - d).days


def _safe_mean(vals: list) -> float | None:
    vals = [v for v in vals if v is not None]
    return mean(vals) if vals else None


def _pace_str(mpm: float | None) -> str:
    if not mpm or mpm <= 0:
        return "–"
    m = int(mpm)
    s = int((mpm - m) * 60)
    return f"{m}'{s:02d}\""


def _trend_arrow(
    current: float | None, previous: float | None, higher_is_better: bool = True
) -> str:
    """Returns ↑ ↓ → based on change."""
    if current is None or previous is None or previous == 0:
        return "→"
    change_pct = (current - previous) / abs(previous)
    if abs(change_pct) < 0.03:
        return "→"
    improving = (change_pct > 0) == higher_is_better
    return "↑" if improving else "↓"


# ─────────────────────────────────────────────────────────────────
# RUNNING ANALYSIS AGENT
# ─────────────────────────────────────────────────────────────────


def analyze_running(conn: sqlite3.Connection, months: int = 12) -> dict:
    since = (date.today() - timedelta(days=months * 30)).isoformat()
    rows = list(
        conn.execute(
            """
        SELECT started_at, duration_s, distance_m, avg_hr, max_hr, avg_pace_mpm, calories
        FROM activities
        WHERE type = 'Running' AND distance_m > 0 AND started_at >= ?
        ORDER BY started_at ASC
        """,
            (since,),
        )
    )

    if not rows:
        return {"sessions": 0, "status": "no_data"}

    sessions = []
    for r in rows:
        d = _to_date(r["started_at"])
        dist_km = (r["distance_m"] or 0) / 1000
        pace = r["avg_pace_mpm"]
        sessions.append(
            {
                "date": str(d),
                "dist_km": round(dist_km, 2),
                "duration_min": round((r["duration_s"] or 0) / 60, 1),
                "pace_mpm": pace,
                "pace_str": _pace_str(pace),
                "avg_hr": r["avg_hr"],
                "calories": r["calories"],
            }
        )

    total_km = sum(s["dist_km"] for s in sessions)
    total_sessions = len(sessions)

    # Monthly breakdown
    monthly: dict[str, dict] = defaultdict(lambda: {"sessions": 0, "km": 0.0, "paces": []})
    for s in sessions:
        key = s["date"][:7]
        monthly[key]["sessions"] += 1
        monthly[key]["km"] += s["dist_km"]
        if s["pace_mpm"]:
            monthly[key]["paces"].append(s["pace_mpm"])

    monthly_list = []
    for k in sorted(monthly.keys())[-12:]:
        m = monthly[k]
        avg_pace = _safe_mean(m["paces"])
        monthly_list.append(
            {
                "month": k,
                "sessions": m["sessions"],
                "km": round(m["km"], 1),
                "avg_pace_mpm": round(avg_pace, 2) if avg_pace else None,
                "avg_pace_str": _pace_str(avg_pace),
            }
        )

    # Recent trend (last 8 sessions)
    recent = sessions[-8:] if len(sessions) >= 2 else sessions
    older = sessions[:-8] if len(sessions) > 8 else []

    recent_paces = [s["pace_mpm"] for s in recent if s["pace_mpm"]]
    older_paces = [s["pace_mpm"] for s in older if s["pace_mpm"]]

    avg_recent_pace = _safe_mean(recent_paces)
    avg_older_pace = _safe_mean(older_paces)

    # Pace improving = lower mpm
    pace_trend = _trend_arrow(avg_recent_pace, avg_older_pace, higher_is_better=False)
    pace_improved_pct = None
    if avg_recent_pace and avg_older_pace:
        pace_improved_pct = round(((avg_older_pace - avg_recent_pace) / avg_older_pace) * 100, 1)

    # Best pace (shortest distance races > 3km)
    long_runs = [s for s in sessions if s["dist_km"] >= 3 and s["pace_mpm"]]
    best_pace = min((s["pace_mpm"] for s in long_runs), default=None)

    # Riegel predictions
    predictions = {}
    if best_pace and long_runs:
        # Find the run with best pace to use as reference
        best_run = min(long_runs, key=lambda s: s["pace_mpm"])
        ref_dist = best_run["dist_km"]
        ref_pace = best_run["pace_mpm"]
        ref_time = ref_dist * ref_pace  # minutes

        for target_name, target_km in [
            ("5km", 5),
            ("10km", 10),
            ("semi", 21.1),
            ("marathon", 42.2),
        ]:
            if target_km >= ref_dist * 0.5:  # Only predict distances near or above reference
                pred_time = ref_time * ((target_km / ref_dist) ** 1.06)
                h, r = divmod(pred_time, 60)
                m, s = divmod(r, 1)
                if h >= 1:
                    pred_str = f"{int(h)}h{int(m):02d}'"
                else:
                    pred_str = f"{int(m)}'{int(s * 60):02d}\""
                predictions[target_name] = {
                    "distance_km": target_km,
                    "time_min": round(pred_time, 1),
                    "label": pred_str,
                    "pace_str": _pace_str(pred_time / target_km),
                }

    # Consistency score (sessions per month vs target of 6/month)
    if monthly_list:
        recent_months = monthly_list[-3:]
        avg_sessions_per_month = _safe_mean([m["sessions"] for m in recent_months]) or 0
        consistency = min(100, int((avg_sessions_per_month / 6) * 100))
    else:
        consistency = 0

    last_run = _to_date(sessions[-1]["date"]) if sessions else None

    return {
        "sessions": total_sessions,
        "total_km": round(total_km, 1),
        "monthly": monthly_list,
        "recent_pace_str": _pace_str(avg_recent_pace),
        "best_pace_str": _pace_str(best_pace),
        "pace_trend": pace_trend,
        "pace_improved_pct": pace_improved_pct,
        "predictions": predictions,
        "consistency_score": consistency,
        "last_run_days_ago": _days_ago(last_run),
        "last_run_date": str(last_run) if last_run else None,
        "recent_sessions": sessions[-5:][::-1],
    }


# ─────────────────────────────────────────────────────────────────
# STRENGTH TRAINING AGENT
# ─────────────────────────────────────────────────────────────────


def analyze_strength(conn: sqlite3.Connection, weeks: int = 12) -> dict:
    since = (date.today() - timedelta(weeks=weeks)).isoformat()
    rows = list(
        conn.execute(
            """
        SELECT started_at, name, duration_s, avg_hr, calories
        FROM activities
        WHERE type IN ('Strength Training', 'Cross Training')
          AND started_at >= ?
        ORDER BY started_at DESC
        """,
            (since,),
        )
    )

    if not rows:
        return {"sessions": 0, "status": "no_data"}

    sessions = []
    for r in rows:
        sessions.append(
            {
                "date": str(r["started_at"])[:10],
                "name": r["name"] or "Muscu",
                "duration_min": round((r["duration_s"] or 0) / 60, 0),
                "avg_hr": r["avg_hr"],
                "calories": r["calories"],
            }
        )

    # Frequency per week
    week_counts: dict[str, int] = defaultdict(int)
    for s in sessions:
        d = _to_date(s["date"])
        if d:
            week_start = d - timedelta(days=d.weekday())
            week_counts[str(week_start)] += 1

    recent_weeks = sorted(week_counts.keys())[-8:]
    avg_per_week = _safe_mean([week_counts[w] for w in recent_weeks]) or 0

    # Recovery gaps (days between sessions)
    dates: list[date] = [d for s in sessions if (d := _to_date(s["date"])) is not None]
    dates.sort()
    gaps = []
    for i in range(1, len(dates)):
        gaps.append((dates[i] - dates[i - 1]).days)

    avg_gap = _safe_mean(gaps)
    last_session = dates[0] if dates else None  # sorted desc from query

    return {
        "sessions": len(sessions),
        "avg_per_week": round(avg_per_week, 1),
        "avg_gap_days": round(avg_gap, 1) if avg_gap else None,
        "last_session_date": str(last_session) if last_session else None,
        "last_session_days_ago": _days_ago(last_session),
        "recent_sessions": sessions[:6],
        "weekly_distribution": {w: week_counts[w] for w in recent_weeks},
    }


# ─────────────────────────────────────────────────────────────────
# RECOVERY AGENT
# ─────────────────────────────────────────────────────────────────


def analyze_recovery(conn: sqlite3.Connection, days: int = 30) -> dict:
    since = (date.today() - timedelta(days=days)).isoformat()

    def fetch_metric(metric: str, limit: int = 30) -> list[dict]:
        rows = conn.execute(
            "SELECT date, value FROM health_metrics WHERE metric=? AND date >= ? ORDER BY date DESC LIMIT ?",
            (metric, since, limit),
        ).fetchall()
        return [{"date": r["date"], "value": r["value"]} for r in rows]

    rhr_data = fetch_metric("rhr")
    sleep_data = fetch_metric("sleep_h")
    battery_data = fetch_metric("body_battery")
    hrv_data = fetch_metric("hrv_sdnn", limit=60)
    stress_data = fetch_metric("stress_avg")

    # Compute averages
    rhr_vals = [r["value"] for r in rhr_data if r["value"]]
    sleep_vals = [r["value"] for r in sleep_data if r["value"]]
    battery_vals = [r["value"] for r in battery_data if r["value"]]
    hrv_vals = [r["value"] for r in hrv_data if r["value"]]
    stress_vals = [r["value"] for r in stress_data if r["value"]]

    avg_rhr = _safe_mean(rhr_vals)
    avg_sleep = _safe_mean(sleep_vals)
    avg_battery = _safe_mean(battery_vals)
    avg_hrv = _safe_mean(hrv_vals)
    avg_stress = _safe_mean(stress_vals)

    # Latest values
    latest_rhr = rhr_vals[0] if rhr_vals else None
    latest_battery = battery_vals[0] if battery_vals else None
    latest_sleep = sleep_vals[0] if sleep_vals else None
    latest_hrv = hrv_vals[0] if hrv_vals else None
    latest_stress = stress_vals[0] if stress_vals else None

    # Recovery score (0-100)
    score = 0.0
    weight_sum = 0.0

    # RHR component (lower = better) — 40 bpm = perfect, 80 = 0
    if latest_rhr:
        rhr_score = max(0.0, min(100.0, (80 - latest_rhr) / (80 - 40) * 100))
        score += rhr_score * 0.25
        weight_sum += 0.25

    # Sleep component — 8h = 100, 4h = 0
    if latest_sleep:
        sleep_score = max(0.0, min(100.0, (latest_sleep / 8.0) * 100))
        score += sleep_score * 0.25
        weight_sum += 0.25

    # Body battery — direct 0-100
    if latest_battery:
        score += float(latest_battery) * 0.30
        weight_sum += 0.30

    # HRV component — 80ms = 100, 20ms = 0
    if avg_hrv:
        hrv_score = max(0.0, min(100.0, ((avg_hrv - 20) / 60) * 100))
        score += hrv_score * 0.15
        weight_sum += 0.15

    # Stress (lower = better) — 0 = 100, 100 = 0
    if latest_stress:
        stress_score = max(0.0, 100.0 - float(latest_stress))
        score += stress_score * 0.05
        weight_sum += 0.05

    recovery_score = int(score / weight_sum) if weight_sum > 0 else 50

    # Trend: compare last 7 vs 7-14 days
    rhr_recent = [r["value"] for r in rhr_data[:7] if r["value"]]
    rhr_older = [r["value"] for r in rhr_data[7:14] if r["value"]]
    rhr_trend = _trend_arrow(_safe_mean(rhr_recent), _safe_mean(rhr_older), higher_is_better=False)

    # Days since HRV
    last_hrv_date = _to_date(hrv_data[0]["date"]) if hrv_data else None
    hrv_stale_days = _days_ago(last_hrv_date)

    return {
        "score": recovery_score,
        "label": _recovery_label(recovery_score),
        "color": _recovery_color(recovery_score),
        "latest": {
            "rhr": latest_rhr,
            "sleep_h": latest_sleep,
            "body_battery": latest_battery,
            "hrv_sdnn": latest_hrv,
            "stress": latest_stress,
        },
        "averages": {
            "rhr": round(avg_rhr, 1) if avg_rhr else None,
            "sleep_h": round(avg_sleep, 1) if avg_sleep else None,
            "body_battery": round(avg_battery, 1) if avg_battery else None,
            "hrv_sdnn": round(avg_hrv, 1) if avg_hrv else None,
            "stress": round(avg_stress, 1) if avg_stress else None,
        },
        "trends": {"rhr": rhr_trend},
        "hrv_stale_days": hrv_stale_days,
        "data": {
            "rhr": rhr_data[:30][::-1],
            "sleep": sleep_data[:30][::-1],
            "body_battery": battery_data[:30][::-1],
            "hrv": hrv_data[:60][::-1],
            "stress": stress_data[:30][::-1],
        },
    }


def _recovery_label(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Bon"
    if score >= 45:
        return "Modéré"
    if score >= 25:
        return "Fatigué"
    return "Épuisé"


def _recovery_color(score: int) -> str:
    if score >= 80:
        return "#00d4aa"
    if score >= 65:
        return "#6ee7b7"
    if score >= 45:
        return "#fbbf24"
    if score >= 25:
        return "#f97316"
    return "#ef4444"


# ─────────────────────────────────────────────────────────────────
# SPORT BREAKDOWN AGENT
# ─────────────────────────────────────────────────────────────────

SPORT_ICONS = {
    "Running": "🏃",
    "Strength Training": "🏋️",
    "Swimming": "🏊",
    "Cycling": "🚴",
    "Tennis": "🎾",
    "Snowboarding": "🏂",
    "Resort Snowboarding": "🏂",
    "SnowSports": "⛷️",
    "Cross Training": "⚡",
    "Cross_country_skiing": "⛷️",
    "Track Running": "🏃",
    "Treadmill Running": "🏃",
    "Walking": "🚶",
    "Yoga": "🧘",
    "Hiking": "🥾",
    "Elliptical": "⚙️",
    "Tennis v2": "🎾",
    "Tennis V2": "🎾",
    "Skating": "⛸️",
    "DownhillSkiing": "🎿",
    "Other": "🏅",
    "Wakeboard": "🏄",
}

SPORT_COLORS = {
    "Running": "#f97316",
    "Strength Training": "#8b5cf6",
    "Swimming": "#06b6d4",
    "Cycling": "#10b981",
    "Tennis": "#84cc16",
    "Snowboarding": "#60a5fa",
    "Resort Snowboarding": "#60a5fa",
    "Cross Training": "#f59e0b",
    "Cross_country_skiing": "#a78bfa",
    "Walking": "#94a3b8",
    "Yoga": "#f472b6",
    "Other": "#6b7280",
}


def analyze_sport_breakdown(conn: sqlite3.Connection, months: int = 12) -> dict:
    since = (date.today() - timedelta(days=months * 30)).isoformat()
    rows = list(
        conn.execute(
            """
        SELECT type, COUNT(*) as n,
               SUM(duration_s) as total_s,
               SUM(CASE WHEN distance_m > 0 THEN distance_m ELSE 0 END) as total_m,
               SUM(calories) as total_cal,
               MAX(started_at) as last_session
        FROM activities
        WHERE started_at >= ?
        GROUP BY type
        ORDER BY n DESC
        """,
            (since,),
        )
    )

    sports = []
    total_sessions = sum(r["n"] for r in rows)
    for r in rows:
        pct = round(r["n"] / total_sessions * 100) if total_sessions > 0 else 0
        sports.append(
            {
                "type": r["type"],
                "icon": SPORT_ICONS.get(r["type"], "🏅"),
                "color": SPORT_COLORS.get(r["type"], "#6b7280"),
                "sessions": r["n"],
                "hours": round((r["total_s"] or 0) / 3600, 1),
                "km": round((r["total_m"] or 0) / 1000, 1),
                "calories": r["total_cal"] or 0,
                "pct": pct,
                "last_session": str(r["last_session"])[:10] if r["last_session"] else None,
                "days_since": _days_ago(
                    _to_date(str(r["last_session"])[:10] if r["last_session"] else None)
                ),
            }
        )

    # Monthly sport heatmap data
    monthly_rows = list(
        conn.execute(
            """
        SELECT strftime('%Y-%m', started_at) as month,
               type,
               COUNT(*) as n,
               SUM(duration_s) as total_s
        FROM activities
        WHERE started_at >= ?
        GROUP BY month, type
        ORDER BY month DESC
        """,
            (since,),
        )
    )

    monthly_by_month: dict[str, dict] = defaultdict(dict)
    for r in monthly_rows:
        monthly_by_month[r["month"]][r["type"]] = {
            "sessions": r["n"],
            "hours": round((r["total_s"] or 0) / 3600, 1),
        }

    return {
        "total_sessions": total_sessions,
        "sports": sports,
        "monthly_breakdown": dict(monthly_by_month),
    }


# ─────────────────────────────────────────────────────────────────
# RECOMMENDATIONS AGENT
# ─────────────────────────────────────────────────────────────────


def generate_recommendations(
    running: dict,
    strength: dict,
    recovery: dict,
    acwr_val: float,
    sport_breakdown: dict,
) -> list[dict]:
    """Generate prioritized, actionable recommendations."""
    recs = []

    # ─── Recovery recommendations ───
    battery = recovery.get("latest", {}).get("body_battery")
    rhr = recovery.get("latest", {}).get("rhr")
    sleep = recovery.get("latest", {}).get("sleep_h")
    recovery.get("score", 50)

    if battery is not None and battery < 20:
        recs.append(
            {
                "severity": "critical",
                "icon": "🔋",
                "title": "Body Battery très bas",
                "body": f"Body Battery à {int(battery)}/100. Ton corps est épuisé. Priorité : sommeil et repos actif aujourd'hui.",
                "action": "Repos ou marche légère uniquement",
                "category": "recovery",
            }
        )
    elif battery is not None and battery < 40:
        recs.append(
            {
                "severity": "warning",
                "icon": "⚡",
                "title": "Récupération incomplète",
                "body": f"Body Battery à {int(battery)}/100. Évite les séances intenses. Opte pour mobilité ou cardio léger.",
                "action": "Séance légère ou récupération active",
                "category": "recovery",
            }
        )

    if rhr is not None and rhr > 65:
        recs.append(
            {
                "severity": "warning",
                "icon": "❤️",
                "title": "FC repos élevée",
                "body": f"RHR à {int(rhr)} bpm (ta normale ~50-58 bpm). Signe de fatigue ou début d'infection. Surveille l'évolution.",
                "action": "Limiter l'intensité, bien s'hydrater",
                "category": "recovery",
            }
        )

    # ─── ACWR recommendations ───
    if acwr_val > 1.5:
        recs.append(
            {
                "severity": "critical",
                "icon": "⚠️",
                "title": "Risque blessure élevé (ACWR)",
                "body": f"ACWR = {round(acwr_val, 2)}. Tu t'entraînes trop vite après une période de repos. Risque de blessure significatif.",
                "action": "Réduire le volume de 20-30% cette semaine",
                "category": "load",
            }
        )
    elif acwr_val > 1.3:
        recs.append(
            {
                "severity": "warning",
                "icon": "📈",
                "title": "Charge d'entraînement élevée",
                "body": f"ACWR = {round(acwr_val, 2)}. Zone de risque modéré. Maintiens le volume sans augmenter.",
                "action": "Stabiliser le volume cette semaine",
                "category": "load",
            }
        )
    elif acwr_val < 0.5:
        recs.append(
            {
                "severity": "info",
                "icon": "💤",
                "title": "Volume très faible",
                "body": f"ACWR = {round(acwr_val, 2)}. Période de sous-entraînement. C'est OK si c'est voulu (déload, vacances).",
                "action": "Reprendre progressivement si pas de déload planifié",
                "category": "load",
            }
        )
    elif 0.8 <= acwr_val <= 1.3:
        recs.append(
            {
                "severity": "success",
                "icon": "✅",
                "title": "Zone optimale d'entraînement",
                "body": f"ACWR = {round(acwr_val, 2)}. Tu es dans la zone verte. C'est le bon moment pour progresser.",
                "action": "Maintien possible ou légère augmentation du volume",
                "category": "load",
            }
        )

    # ─── Running recommendations ───
    last_run_days = running.get("last_run_days_ago", 999)
    if last_run_days > 14:
        recs.append(
            {
                "severity": "info",
                "icon": "🏃",
                "title": "Reprise running recommandée",
                "body": f"Dernière sortie running il y a {last_run_days} jours. Une séance légère (30-40min) maintient la base cardio.",
                "action": "Run facile 5km, allure conversation",
                "category": "sport",
            }
        )

    consistency = running.get("consistency_score", 0)
    if consistency < 40 and running.get("sessions", 0) > 0:
        recs.append(
            {
                "severity": "info",
                "icon": "📅",
                "title": "Régularité running à améliorer",
                "body": f"Score de régularité : {consistency}/100. Vise 4-6 sorties par mois pour progresser.",
                "action": "Planifier 2 runs cette semaine dans le calendrier",
                "category": "sport",
            }
        )

    # ─── Strength recommendations ───
    last_strength_days = strength.get("last_session_days_ago", 999)
    if last_strength_days > 7:
        recs.append(
            {
                "severity": "info",
                "icon": "🏋️",
                "title": "Séance muscu recommandée",
                "body": f"Dernière séance de force il y a {last_strength_days} jours. Pour maintenir la masse, vise 2-3x/semaine.",
                "action": "Séance Push ou Full Body",
                "category": "sport",
            }
        )

    # ─── Sleep recommendation ───
    if sleep is not None and sleep < 7:
        recs.append(
            {
                "severity": "warning",
                "icon": "😴",
                "title": "Sommeil insuffisant",
                "body": f"{round(sleep, 1)}h de sommeil. En dessous des 7-9h recommandés. Impact sur récupération et performance.",
                "action": "Coucher 30min plus tôt ce soir",
                "category": "recovery",
            }
        )

    # Sort by severity
    order = {"critical": 0, "warning": 1, "info": 2, "success": 3}
    recs.sort(key=lambda r: order.get(r["severity"], 9))

    return recs[:5]  # Top 5 recommendations


# ─────────────────────────────────────────────────────────────────
# WEEKLY SUMMARY AGENT
# ─────────────────────────────────────────────────────────────────


def generate_weekly_summary(
    running: dict,
    strength: dict,
    recovery: dict,
    sport_breakdown: dict,
    acwr_val: float,
) -> dict:
    """Generate a narrative weekly summary."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # This week's activities
    week_start.isoformat()
    for _sport in sport_breakdown.get("sports", []):
        sport_breakdown.get("monthly_breakdown", {}).get(today.strftime("%Y-%m"), {})
        # Just approximate from recent sessions
        pass

    highlights = []

    # Recovery status
    rec_score = recovery.get("score", 50)
    rec_label = recovery.get("label", "Modéré")
    highlights.append(f"Récupération {rec_label} ({rec_score}/100)")

    # ACWR zone
    if acwr_val >= 0.8 and acwr_val <= 1.3:
        highlights.append(f"Charge optimale (ACWR {round(acwr_val, 2)})")
    elif acwr_val > 1.3:
        highlights.append(f"⚠️ Charge élevée (ACWR {round(acwr_val, 2)})")

    # Last sport
    last_run_days = running.get("last_run_days_ago", 999)
    last_strength_days = strength.get("last_session_days_ago", 999)

    if last_run_days <= 3:
        highlights.append(f"Running il y a {last_run_days}j")
    if last_strength_days <= 3:
        highlights.append(f"Muscu il y a {last_strength_days}j")

    return {
        "week": week_start.strftime("Semaine du %d %b"),
        "highlights": highlights,
        "ready_to_train": rec_score >= 50 and acwr_val <= 1.3,
    }


# ─────────────────────────────────────────────────────────────────
# MAIN AGENT ENTRY POINT
# ─────────────────────────────────────────────────────────────────


def run_sports_agent(db_path: Path, acwr_val: float = 1.0) -> dict:
    """
    Run all sports analysis agents and return consolidated insights.

    Args:
        db_path: Path to SQLite database
        acwr_val: Current ACWR from training_load analytics

    Returns:
        dict with keys: running, strength, recovery, sport_breakdown,
                        recommendations, weekly_summary
    """
    try:
        conn = _conn(db_path)

        running = analyze_running(conn)
        strength = analyze_strength(conn)
        recovery = analyze_recovery(conn)
        sport_breakdown = analyze_sport_breakdown(conn)
        recommendations = generate_recommendations(
            running=running,
            strength=strength,
            recovery=recovery,
            acwr_val=acwr_val,
            sport_breakdown=sport_breakdown,
        )
        weekly_summary = generate_weekly_summary(
            running=running,
            strength=strength,
            recovery=recovery,
            sport_breakdown=sport_breakdown,
            acwr_val=acwr_val,
        )

        conn.close()

        return {
            "running": running,
            "strength": strength,
            "recovery": recovery,
            "sport_breakdown": sport_breakdown,
            "recommendations": recommendations,
            "weekly_summary": weekly_summary,
        }

    except Exception as e:
        return {
            "error": str(e),
            "running": {},
            "strength": {},
            "recovery": {},
            "sport_breakdown": {},
            "recommendations": [],
            "weekly_summary": {},
        }
