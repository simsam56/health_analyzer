"""
generator.py — PerformOS cockpit (v4)
UI centered on weekly planning + health progression.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

TYPE_DEFS = {
    "cardio": {"label": "Cardio", "category": "sport", "color": "#22c55e", "icon": "🏃"},
    "musculation": {"label": "Musculation", "category": "sport", "color": "#f97316", "icon": "🏋️"},
    "sport_libre": {"label": "Sport", "category": "sport", "color": "#14b8a6", "icon": "🎾"},
    "mobilite": {"label": "Yoga", "category": "yoga", "color": "#a78bfa", "icon": "🧘"},
    "yoga": {"label": "Yoga", "category": "yoga", "color": "#a78bfa", "icon": "🧘"},
    "travail": {"label": "Travail", "category": "travail", "color": "#3b82f6", "icon": "💼"},
    "formation": {"label": "Formation", "category": "formation", "color": "#f59e0b", "icon": "📚"},
    "apprentissage": {
        "label": "Formation",
        "category": "formation",
        "color": "#f59e0b",
        "icon": "📚",
    },
    "lecon": {"label": "Leçon", "category": "lecon", "color": "#06b6d4", "icon": "🎓"},
    "social": {"label": "Social", "category": "social", "color": "#ec4899", "icon": "💬"},
    "relationnel": {"label": "Social", "category": "social", "color": "#ec4899", "icon": "💬"},
    "autre": {"label": "Autre", "category": "autre", "color": "#64748b", "icon": "🧩"},
}

# Couleurs par domaine (category)
DOMAIN_COLORS = {
    "sport": "#22c55e",
    "yoga": "#a78bfa",
    "travail": "#3b82f6",
    "formation": "#f59e0b",
    "lecon": "#06b6d4",
    "social": "#ec4899",
    "autre": "#64748b",
    # rétro-compat
    "sante": "#22c55e",
    "relationnel": "#ec4899",
    "apprentissage": "#f59e0b",
}

DOMAIN_ICONS = {
    "sport": "🏃",
    "yoga": "🧘",
    "travail": "💼",
    "formation": "📚",
    "lecon": "🎓",
    "social": "💬",
    "autre": "🧩",
    "sante": "🏃",
    "relationnel": "💬",
    "apprentissage": "📚",
}

CATEGORY_LABELS = {
    "sport": "Sport",
    "yoga": "Yoga",
    "travail": "Travail",
    "formation": "Formation",
    "lecon": "Leçon",
    "social": "Social",
    "autre": "Autre",
    # rétro-compat
    "sante": "Sport",
    "relationnel": "Social",
    "apprentissage": "Formation",
}


ICONS_BY_ACTIVITY = {
    "Running": "🏃",
    "Strength Training": "🏋️",
    "Cycling": "🚴",
    "Swimming": "🏊",
    "Tennis": "🎾",
    "Yoga": "🧘",
    "Hiking": "🥾",
    "Walking": "🚶",
    "Golf": "⛳",
}


def _latest_metric(metrics_history: list[dict], metric: str, default: float = 0.0) -> float:
    vals = [m for m in metrics_history if m.get("metric") == metric and m.get("value") is not None]
    if not vals:
        return float(default)
    return float(vals[-1]["value"])


def _infer_event_type(event: dict) -> str:
    title = (event.get("title") or "").lower()
    cat = (event.get("category") or "").lower()

    if any(k in title for k in ["muscu", "strength", "gym", "halt", "full body"]):
        return "musculation"
    if any(k in title for k in ["yoga", "mobil", "stretch", "souplesse", "pilates"]):
        return "yoga"
    if any(k in title for k in ["run", "course", "jog", "10km", "cardio", "trail"]):
        return "cardio"
    if any(k in title for k in ["tennis", "golf", "swim", "natation", "vélo", "velo", "sport"]):
        return "sport_libre"
    if cat in ("travail", "work"):
        return "travail"
    if cat in ("formation", "apprentissage", "learning"):
        return "formation"
    if cat in ("lecon", "lesson"):
        return "lecon"
    if any(k in title for k in ["leçon", "lecon", "lesson", "cours de"]):
        return "lecon"
    if cat in ("social", "relationnel"):
        return "social"
    if cat in ("yoga",):
        return "yoga"
    if cat in ("sport", "sante"):
        return "cardio"
    return "autre"


def _prepare_pilot_events(pilot_events: list[dict]) -> list[dict]:
    rows = []
    for e in pilot_events:
        t = _infer_event_type(e)
        d = TYPE_DEFS.get(t, TYPE_DEFS["autre"])
        rows.append(
            {
                "id": str(e.get("id") or ""),
                "task_id": e.get("task_id"),
                "title": e.get("title") or "Événement",
                "start_at": e.get("start_at"),
                "end_at": e.get("end_at"),
                "source": e.get("source") or "local",
                "calendar_name": e.get("calendar_name") or "",
                "category": d["category"],
                "type": t,
                "icon": d["icon"],
                "color": d["color"],
                "triage_status": e.get("triage_status") or "a_planifier",
                "scheduled": True,
                "last_bucket_before_scheduling": e.get("last_bucket_before_scheduling"),
                "calendar_uid": e.get("calendar_uid"),
            }
        )
    return rows


def _series_labels_values(rows: list[dict], limit: int = 260) -> tuple[list[str], list[float]]:
    if not rows:
        return [], []
    cut = rows[-limit:]
    labels = [str(r.get("label") or r.get("week") or "") for r in cut]
    values = [float(r.get("value") or 0) for r in cut]
    return labels, values


def generate_html(
    training: dict,
    muscles: dict,
    metrics_history: list[dict],
    daily_load_rows: list[dict],
    output_path: str | Path,
    api_token: str = "",
    sports_agent: dict | None = None,
) -> None:
    _ = daily_load_rows  # kept for signature compatibility (unused)

    today = date.today().strftime("%d/%m/%Y")
    now = datetime.now().strftime("%H:%M")

    wakeboard = training.get("wakeboard", {})
    acwr = training.get("acwr", {})
    running = training.get("running", {})
    health = training.get("health", {})
    muscle_quality = muscles.get("data_quality", {}) or {}
    recent_activities = training.get("recent_activities", [])[:5]
    pilotage = training.get("pilotage", {})
    progress = training.get("progress", {})
    calendar_sync = training.get("calendar_sync", {})

    planner_events = _prepare_pilot_events(pilotage.get("events", []))
    planner_events_json = json.dumps(planner_events, ensure_ascii=False).replace("</", "<\\/")

    week_start = pilotage.get("week_start", str(date.today()))
    summary = pilotage.get("summary", {})
    sante_h = float(summary.get("sante_h", 0) or 0)
    travail_h = float(summary.get("travail_h", 0) or 0)
    relationnel_h = float(summary.get("relationnel_h", 0) or 0)
    apprentissage_h = float(summary.get("apprentissage_h", 0) or 0)
    autre_h = float(summary.get("autre_h", 0) or 0)
    total_h = float(summary.get("total_h", 0) or 0)

    goal_h = 6.0
    goal_done = sante_h
    goal_left = max(0.0, goal_h - goal_done)
    goal_pct = min(100.0, (goal_done / goal_h) * 100 if goal_h else 0)

    wbs = float(wakeboard.get("score", 0) or 0)
    wbs_label = wakeboard.get("label", "-")
    acwr_val = float(acwr.get("acwr", 0) or 0)
    acwr_zone = acwr.get("zone", "-")
    pred_10k = (running.get("estimated_10k") or {}).get("label") or running.get(
        "predictions", {}
    ).get("10km", "-")

    hrv = float(health.get("hrv") or _latest_metric(metrics_history, "hrv_sdnn", 0))
    sleep_h = float(health.get("sleep_h") or _latest_metric(metrics_history, "sleep_h", 0))
    vo2max = float(health.get("vo2max") or _latest_metric(metrics_history, "vo2max", 0))
    steps = float(_latest_metric(metrics_history, "steps", 0))
    body_battery = float(
        health.get("body_battery") or _latest_metric(metrics_history, "body_battery", 0)
    )
    rhr = float(health.get("rhr") or 0)
    hrv_days_old = health.get("hrv_days_old")
    sleep_days_old = health.get("sleep_days_old")
    rhr_days_old = health.get("rhr_days_old")
    freshness_vals = [
        float(health.get("hrv_freshness", 0) or 0),
        float(health.get("sleep_freshness", 0) or 0),
        float(health.get("rhr_freshness", 0) or 0),
    ]
    freshness_score = (
        round((sum(freshness_vals) / len(freshness_vals)) * 100.0, 1) if freshness_vals else 0.0
    )
    freshness_label = (
        "Excellente" if freshness_score >= 80 else "Moyenne" if freshness_score >= 55 else "Faible"
    )
    vo2_for_score = float(vo2max or 0)
    vo2_norm = min(100.0, max(0.0, (vo2_for_score - 25.0) * 2.5)) if vo2_for_score else 0.0
    readiness_global = round(
        max(0.0, min(100.0, (wbs * 0.5) + (body_battery * 0.3) + (vo2_norm * 0.2))), 1
    )

    # --- PMC metrics (TSB, CTL, ATL) ---
    pmc_today = training.get("pmc", {})
    tsb = float(pmc_today.get("tsb", 0) or 0)
    ctl = float(pmc_today.get("ctl", 0) or 0)
    atl = float(pmc_today.get("atl", 0) or 0)

    # --- RHR & HRV deltas vs baseline ---
    rhr_baseline = float(health.get("rhr_baseline") or rhr or 0)
    hrv_baseline = float(health.get("hrv_baseline") or hrv or 0)
    rhr_delta = round(rhr - rhr_baseline, 1) if rhr and rhr_baseline else 0.0
    hrv_delta = round(hrv - hrv_baseline, 1) if hrv and hrv_baseline else 0.0
    rhr_delta_str = (f"+{rhr_delta:.0f}" if rhr_delta > 0 else f"{rhr_delta:.0f}") if rhr else "—"
    hrv_trend_arrow = "↑" if hrv_delta > 2 else ("↓" if hrv_delta < -2 else "→")
    hrv_trend_color = "#22c55e" if hrv_delta > 2 else ("#ef4444" if hrv_delta < -2 else "#f59e0b")
    rhr_delta_class = "positive" if rhr_delta < 0 else ("negative" if rhr_delta > 2 else "neutral")

    # --- 3 Rings (0-100) ---
    RING_CIRC = 220  # 2*pi*35 ≈ 219.9

    def _ring_color(s: float) -> str:
        return "#22c55e" if s >= 67 else ("#f59e0b" if s >= 34 else "#ef4444")

    def _ring_offset(s: float) -> str:
        return f"{RING_CIRC * (1.0 - max(0.0, min(100.0, s)) / 100.0):.1f}"

    ring_recovery = round(float(wbs), 1)
    ring_activity = round(min(100.0, (goal_done / goal_h) * 100.0 if goal_h else 0.0), 1)
    ring_sleep = round(min(100.0, (sleep_h / 7.5) * 100.0 if sleep_h else 0.0), 1)

    # --- TSB / ACWR colors ---
    tsb_color = "#22c55e" if tsb > 0 else ("#f59e0b" if tsb > -10 else "#ef4444")
    tsb_class = "danger" if tsb < -15 else ""
    acwr_color = (
        "#22c55e" if 0.8 <= acwr_val <= 1.3 else ("#f59e0b" if acwr_val <= 1.5 else "#ef4444")
    )
    acwr_class = "danger" if acwr_val > 1.5 else ""
    acwr_alert_display = "flex" if acwr_val > 1.5 else "none"

    # --- Sync badge ---
    cal_last_sync_raw = calendar_sync.get("last_sync_at") or calendar_sync.get("synced_at") or ""
    sync_badge_label = "Sync"
    sync_badge_class = "warn"
    if cal_last_sync_raw:
        try:
            sync_dt = _dt.fromisoformat(str(cal_last_sync_raw)[:19])
            hours_ago = (_dt.now() - sync_dt).total_seconds() / 3600
            sync_time_str = sync_dt.strftime("%H:%M")
            if hours_ago < 12:
                sync_badge_class = "ok"
                sync_badge_label = f"Sync · {sync_time_str}"
            elif hours_ago < 24:
                sync_badge_class = "warn"
                sync_badge_label = f"Sync · {sync_time_str}"
            else:
                sync_badge_class = "err"
                sync_badge_label = f"Sync · J-{int(hours_ago // 24)}"
        except Exception:
            sync_badge_label = "Sync · ?"

    # --- Work/Social week ---
    work_week_pct = round((travail_h / 40.0) * 100.0, 1) if travail_h else 0.0
    social_week_pct = round(min(100.0, (relationnel_h / 5.0) * 100.0), 1) if relationnel_h else 0.0

    # Weekly load split by activity type
    try:
        ws = date.fromisoformat(str(week_start)[:10])
    except Exception:
        ws = date.today()
    we = ws + timedelta(days=7)
    load_split = {"cardio": 0.0, "musculation": 0.0, "mobilite": 0.0, "sport_libre": 0.0}
    for ev in pilotage.get("events", []):
        sraw = str(ev.get("start_at") or "")
        eraw = str(ev.get("end_at") or "")
        if len(sraw) < 10:
            continue
        try:
            d_ev = date.fromisoformat(sraw[:10])
        except Exception:
            continue
        if not (ws <= d_ev < we):
            continue
        try:
            sdt = datetime.fromisoformat(sraw.replace("Z", ""))
            edt = datetime.fromisoformat(eraw.replace("Z", ""))
            dur_h = max(0.0, (edt - sdt).total_seconds() / 3600.0)
        except Exception:
            dur_h = 0.0
        t = _infer_event_type(ev)
        if t in load_split:
            load_split[t] += dur_h

    load_split_html = ""
    for t in ("cardio", "musculation", "mobilite", "sport_libre"):
        val = load_split[t]
        lbl = TYPE_DEFS[t]["label"]
        c = TYPE_DEFS[t]["color"]
        load_split_html += (
            '<div class="hrow">'
            f"<span>{lbl}</span>"
            f'<div class="track"><div class="fill" style="width:{min(100.0, val * 20):.1f}%;background:{c};"></div></div>'
            f"<span>{val:.1f}h</span>"
            "</div>"
        )
    if not load_split_html:
        load_split_html = '<div class="muted">Aucune charge planifiée cette semaine.</div>'

    # Muscle map / bars
    muscle_order = ["Pecs", "Dos", "Épaules", "Biceps", "Triceps", "Core", "Jambes"]
    cumulative = muscles.get("cumulative", {}) or {}
    targets = muscles.get("targets", {}) or {}
    muscle_bars_html = ""
    zone_alpha = {}
    for mg in muscle_order:
        data = cumulative.get(mg, {})
        sets_week = float(data.get("sets_per_week", 0) or 0)
        tgt = float((targets.get(mg) or {}).get("hyper", 12) or 12)
        pct = min(100.0, (sets_week / tgt * 100.0) if tgt else 0.0)
        color = "#ef4444" if pct < 50 else "#f59e0b" if pct < 90 else "#22c55e"
        zone_alpha[mg] = 0.12 + (pct / 100.0) * 0.78
        muscle_bars_html += (
            '<div class="muscle-row">'
            f"<span>{escape(mg)}</span>"
            f'<div class="track"><div class="fill" style="width:{pct:.1f}%;background:{color};"></div></div>'
            f"<span>{sets_week:.1f}/{tgt:.0f}</span>"
            "</div>"
        )
    if not muscle_bars_html:
        muscle_bars_html = '<div class="muted">Pas de données musculation disponibles.</div>'

    # Progress datasets
    train_labels, train_values = _series_labels_values(
        progress.get("training_hours_weekly", []), limit=260
    )
    run_labels, run_values = _series_labels_values(progress.get("running_km_weekly", []), limit=260)
    tenk_labels, tenk_values = _series_labels_values(progress.get("est_10k_weekly", []), limit=260)
    vo2_labels, vo2_values = _series_labels_values(progress.get("vo2max_series", []), limit=260)

    # Sports mix from planner series fallback
    sport_mix = pilotage.get("series", {}).get("sport_mix_hours", [])
    total_mix = sum(float(r.get("hours", 0) or 0) for r in sport_mix) or 1.0
    sport_mix_html = ""
    for row in sport_mix[:8]:
        t = escape(str(row.get("type", "Other")))
        h = float(row.get("hours", 0) or 0)
        pct = h / total_mix * 100
        sport_mix_html += (
            f'<div class="mix-row"><span>{t}</span><span>{h:.1f}h ({pct:.0f}%)</span></div>'
        )
    if not sport_mix_html:
        sport_mix_html = '<div class="muted">Pas assez de données sport.</div>'

    recent_html = ""
    for act in recent_activities:
        at_raw = str(act.get("type") or "Activité")
        at = escape(at_raw)
        icon = ICONS_BY_ACTIVITY.get(at_raw, "🏃")
        dt = escape((act.get("started_at") or "")[:16].replace("T", " "))
        dur = int(act.get("duration_s") or 0)
        dur_m = max(1, dur // 60) if dur else 0
        recent_html += (
            '<div class="recent-row">'
            f'<span class="recent-icon">{icon}</span>'
            f'<span class="recent-name">{at}</span>'
            f'<span class="recent-meta">{dur_m} min · {dt}</span>'
            "</div>"
        )
    if not recent_html:
        recent_html = '<div class="muted">Aucune activité récente.</div>'

    # cal_enabled = True dès que macOS + EventKit disponible (permission vérifiée à runtime via /calendar/status)
    import sys as _sys

    _cal_err = calendar_sync.get("error", "")
    cal_enabled = (
        _sys.platform == "darwin"
        and _cal_err != "eventkit_unavailable"
        and _cal_err != "apple_calendar_macos_only"
    )
    pending_sync = int(calendar_sync.get("pending_tasks", 0) or 0)

    # Recommendations
    recommendations = []
    if acwr_val > 1.4:
        recommendations.append("Charge élevée: allège 2-3 jours (récup active, mobilité).")
    elif acwr_val < 0.8:
        recommendations.append(
            "Charge basse: remonte progressivement le volume (+10% max/semaine)."
        )
    else:
        recommendations.append("Charge équilibrée: maintiens le rythme actuel.")

    if wbs < 55:
        recommendations.append("Readiness basse: priorise sommeil, hydratation, intensité modérée.")
    elif wbs > 75:
        recommendations.append("Readiness haute: fenêtre favorable pour une séance qualitative.")

    imbalances = muscles.get("imbalances", [])
    weak = [
        im.get("muscle")
        for im in imbalances
        if (im.get("status") or im.get("level")) in ("faible", "critique")
    ]
    weak = sorted({w for w in weak if w})
    if weak:
        recommendations.append("Priorité renforcement cette semaine: " + ", ".join(weak) + ".")
    if freshness_score < 55:
        recommendations.append(
            "Données santé peu fraîches: relance une sync Garmin/Apple pour fiabiliser les décisions."
        )
    if pending_sync > 0:
        recommendations.append(
            f"Synchronisation Apple incomplète: {pending_sync} tâche(s) à pousser depuis le cockpit."
        )
    unresolved_unk = int(muscle_quality.get("unknown_sets_unresolved", 0) or 0)
    if unresolved_unk > 0:
        recommendations.append(
            f"Qualité musculation partielle: {unresolved_unk} sets non attribués à un groupe musculaire."
        )

    reco_html = "".join([f'<div class="reco-item">{escape(r)}</div>' for r in recommendations[:4]])

    # Template (no f-string to keep CSS/JS braces simple)
    html = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>PerformOS Cockpit</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<style>
:root {
  /* Surfaces */
  --bg: #0a0e1a;
  --surface-0: rgba(255,255,255,0.03);
  --surface-1: rgba(255,255,255,0.06);
  --surface-2: rgba(255,255,255,0.10);
  --surface-3: rgba(255,255,255,0.14);
  --card: rgba(255,255,255,0.06);
  /* Text */
  --text: #f1f5f9;
  --text-secondary: #94a3b8;
  --muted: #64748b;
  /* Borders */
  --line: rgba(255,255,255,0.08);
  --border-hover: rgba(255,255,255,0.16);
  /* Accent */
  --accent: #3b82f6;
  --accent-hover: #2563eb;
  --accent-muted: rgba(59,130,246,0.15);
  /* Shadows */
  --shadow: 0 12px 32px rgba(0,0,0,.45);
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.15);
  --shadow-glow: 0 0 20px rgba(59,130,246,0.15);
  /* Ring */
  --ring: rgba(255,255,255,0.08);
  /* Status */
  --green: #22c55e;
  --yellow: #f59e0b;
  --red: #ef4444;
  --blue: #3b82f6;
  /* Domaines */
  --sante: #22c55e;
  --sante-bg: rgba(34,197,94,0.10);
  --travail: #3b82f6;
  --travail-bg: rgba(59,130,246,0.10);
  --relationnel: #ec4899;
  --social-bg: rgba(236,72,153,0.10);
  --apprentissage: #f59e0b;
  --apprentissage-bg: rgba(245,158,11,0.10);
  --autre: #64748b;
  /* Spacing */
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-5: 20px; --space-6: 24px;
  /* Radius */
  --radius-sm: 8px; --radius-md: 12px; --radius-lg: 16px; --radius-xl: 20px; --radius-full: 999px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  background-image: radial-gradient(circle at 20% 10%, rgba(59,130,246,.07) 0, transparent 45%),
    radial-gradient(circle at 80% 90%, rgba(236,72,153,.05) 0, transparent 38%);
  min-height: 100vh;
  font-family: Inter, -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
  color: var(--text);
}
.app {
  max-width: 1540px;
  margin: 0 auto;
  padding: 18px 16px 100px;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.brand-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
/* ─── MASCOT 3D ─────────────────────────────────────────────── */
.mascot { width:52px; height:52px; cursor:pointer; user-select:none; flex-shrink:0; }
.mascot-body { width:100%; height:100%; background:radial-gradient(circle at 35% 30%,#c7d2fe,#6366f1 60%,#4338ca); border-radius:18px; display:flex; align-items:center; justify-content:center; animation:mascotBreathe 3.5s ease-in-out infinite; box-shadow:0 6px 20px rgba(99,102,241,.35); transition:box-shadow .2s; }
.mascot:hover .mascot-body { box-shadow:0 8px 28px rgba(99,102,241,.5); }
.mascot-face { display:flex; flex-direction:column; align-items:center; gap:5px; }
.mascot-eyes { display:flex; gap:7px; }
.mascot-eye { width:7px; height:7px; background:#fff; border-radius:50%; animation:mascotBlink 5s infinite; }
.mascot-eye:nth-child(2) { animation-delay:.08s; }
.mascot-mouth { width:12px; height:4px; border-bottom:2px solid rgba(255,255,255,.75); border-radius:0 0 8px 8px; }
.mascot.bounce .mascot-body { animation:mascotBounce .5s ease forwards; }
@keyframes mascotBreathe { 0%,100%{ transform:scale(1); } 50%{ transform:scale(1.04); } }
@keyframes mascotBlink { 0%,93%,97%,100%{ transform:scaleY(1); } 95%{ transform:scaleY(0.1); } }
@keyframes mascotBounce { 0%{ transform:scale(1) rotate(0deg); } 25%{ transform:scale(.88) rotate(-6deg); } 60%{ transform:scale(1.12) rotate(4deg); } 100%{ transform:scale(1) rotate(0deg); } }

/* ─── APPLE CALENDAR STATUS ──────────────────────────────────── */
.apple-cal-status { display:inline-flex; align-items:center; gap:8px; padding:7px 12px; border:1px solid var(--line); background:var(--surface-1); border-radius:var(--radius-sm); cursor:pointer; transition:background .15s, border-color .15s; text-align:left; font-family:inherit; color:var(--text); white-space:nowrap; }
.apple-cal-status:hover { background:var(--surface-2); }
.apple-cal-icon { font-size:16px; line-height:1; }
.apple-cal-body { display:flex; flex-direction:column; gap:1px; }
.apple-cal-label { font-size:11px; font-weight:700; color:var(--text); }
.apple-cal-sub { font-size:10px; color:var(--muted); }
.apple-cal-spinner { font-size:13px; display:none; }
.apple-cal-status.ok { border-color:rgba(34,197,94,.3); background:rgba(34,197,94,.08); }
.apple-cal-status.ok .apple-cal-label { color:#22c55e; }
.apple-cal-status.error,.apple-cal-status.err { border-color:rgba(239,68,68,.3); background:rgba(239,68,68,.06); }
.apple-cal-status.error .apple-cal-label,.apple-cal-status.err .apple-cal-label { color:#ef4444; }
.apple-cal-status.warn { border-color:rgba(245,158,11,.3); background:rgba(245,158,11,.06); }
.apple-cal-status.warn .apple-cal-label { color:#f59e0b; }
.apple-cal-status.syncing { border-color:rgba(59,130,246,.3); background:rgba(59,130,246,.06); }
.apple-cal-status.syncing .apple-cal-spinner { display:inline; animation:spin 1s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }

/* ─── DONUT RÉPARTITION ──────────────────────────────────────── */
.donut-card { flex:none !important; min-width:auto !important; }
.donut-canvas-wrap { display:flex; align-items:center; gap:10px; margin-top:6px; }
.donut-legend { display:flex; flex-direction:column; gap:3px; flex:1; overflow:hidden; }
.donut-leg-row { display:flex; align-items:center; gap:5px; font-size:10px; font-weight:600; }
.donut-leg-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.donut-leg-label { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.donut-leg-val { color:var(--muted); }

/* ─── FORMULAIRE INLINE JOUR "+" ─────────────────────────────── */
.day-quick-form { background:var(--surface-2); border:1px solid var(--line); border-radius:var(--radius-sm); padding:6px; display:flex; flex-direction:column; gap:5px; margin-bottom:6px; }
.day-quick-input { background:var(--surface-0); border:1px solid var(--line); border-radius:6px; padding:5px 7px; font-size:11px; color:var(--text); width:100%; font-family:inherit; box-sizing:border-box; }
.day-quick-input:focus { outline:none; border-color:#3b82f6; box-shadow:0 0 0 2px rgba(59,130,246,.2); }
.day-quick-select { background:var(--surface-0); border:1px solid var(--line); border-radius:6px; padding:4px 6px; font-size:10px; color:var(--text); font-family:inherit; width:100%; }
.day-quick-time-row { display:flex; gap:4px; align-items:center; }
.day-quick-time-row .day-quick-input { flex:1; min-width:0; width:auto; padding:4px 5px; }
.day-quick-time-row .dqt-sep { font-size:10px; color:var(--muted); flex-shrink:0; }
.day-quick-actions { display:flex; gap:4px; }
.day-quick-submit { flex:1; padding:4px 6px; background:#3b82f6; color:#fff; border:none; border-radius:5px; font-size:10px; font-weight:700; cursor:pointer; font-family:inherit; }
.day-quick-submit:hover { background:#2563eb; }
.day-quick-cancel { padding:4px 7px; background:transparent; color:var(--muted); border:1px solid var(--line); border-radius:5px; font-size:10px; cursor:pointer; font-family:inherit; }

/* ─── MODAL PLANIFICATION ─────────────────────────────────────── */
.plan-modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.6); backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px); z-index:9000; display:flex; align-items:center; justify-content:center; animation:fadeIn .2s ease; }
.plan-modal { background:rgba(15,23,42,0.9); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border:1px solid rgba(255,255,255,0.12); border-radius:18px; padding:22px 26px; width:min(360px,92vw); box-shadow:0 32px 80px rgba(0,0,0,.6); animation:modalIn .25s cubic-bezier(.4,0,.2,1); }
@keyframes modalIn { from { opacity:0; transform:scale(.92) translateY(12px); } to { opacity:1; transform:scale(1) translateY(0); } }
.plan-modal h3 { margin:0 0 16px; font-size:14px; font-weight:700; color:var(--text); }
.plan-modal label { display:block; font-size:11px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; margin-bottom:4px; margin-top:12px; }
.plan-modal label:first-of-type { margin-top:0; }
.plan-modal input { width:100%; padding:8px 10px; background:var(--surface-0); border:1px solid var(--line); border-radius:8px; color:var(--text); font-size:13px; font-family:inherit; box-sizing:border-box; }
.plan-modal input:focus { outline:none; border-color:var(--accent); box-shadow:0 0 0 2px rgba(99,102,241,.25); }
.plan-modal .pm-time-row { display:flex; gap:8px; align-items:center; }
.plan-modal .pm-time-row input { flex:1; }
.plan-modal .pm-time-row span { color:var(--muted); font-size:12px; flex-shrink:0; }
.plan-modal .pm-footer { display:flex; gap:8px; margin-top:20px; }
.plan-modal .pm-ok { flex:1; padding:9px; background:var(--accent); color:#fff; border:none; border-radius:9px; font-size:13px; font-weight:700; cursor:pointer; font-family:inherit; transition:background .15s; }
.plan-modal .pm-ok:hover { background:#4f46e5; }
.plan-modal .pm-cancel { padding:9px 14px; background:transparent; color:var(--muted); border:1px solid var(--line); border-radius:9px; font-size:13px; cursor:pointer; font-family:inherit; }
.plan-modal select, .pm-select { width:100%; padding:8px 10px; background:var(--surface-0); border:1px solid var(--line); border-radius:8px; color:var(--text); font-size:13px; font-family:inherit; box-sizing:border-box; appearance:auto; }
.plan-modal select:focus { outline:none; border-color:var(--accent); box-shadow:0 0 0 2px rgba(99,102,241,.25); }

/* ─── TODAY BADGE ────────────────────────────────────────────── */
.today-badge { display:inline-block; background:#3b82f6; color:#fff; border-radius:4px; font-size:9px; font-weight:800; padding:1px 5px; margin-left:4px; }
.brand h1 {
  margin: 0;
  font-size: 30px;
  letter-spacing: -0.02em;
}
.brand p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}
.top-right {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  gap: 8px;
}
.hero-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(150px, 1fr));
  gap: 8px;
  flex: 1;
  max-width: 620px;
}
.hero-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255,255,255,0.05);
  padding: 8px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.hero-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.hero-icon.health { background: #ecfdf5; }
.hero-icon.work { background: #eff6ff; }
.hero-icon.social { background: #fff1f2; }
.hero-meta { display: flex; flex-direction: column; gap: 1px; }
.hero-label { font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #64748b; font-weight: 700; }
.hero-value { font-size: 13px; font-weight: 700; color: #0f172a; }
.badge {
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 11px;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  cursor: pointer;
  transition: transform .14s ease, box-shadow .14s ease, border-color .14s ease;
}
.badge.ok { color: #22c55e; border-color: rgba(34,197,94,.3); background: rgba(34,197,94,.08); }
.badge.warn { color: #f59e0b; border-color: rgba(245,158,11,.3); background: rgba(245,158,11,.08); }
.badge:hover { transform: translateY(-1px); box-shadow: 0 6px 14px rgba(0,0,0,.3); }
.quick-sync {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.tab {
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  color: var(--muted);
  transition: all .2s ease;
  font-family: inherit;
}
.tab:hover { background:rgba(255,255,255,0.08); color:var(--text); border-color:rgba(255,255,255,0.14); transform:translateY(-1px); }
.tab.active {
  background: rgba(59,130,246,0.15);
  border-color: rgba(59,130,246,0.4);
  color: #93c5fd;
  box-shadow: 0 0 16px rgba(59,130,246,.12);
}
.section { display: none; }
.section.active { display: block; }
.grid-planning {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  align-items: start;
}
.planning-secondary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stack-sticky {
  position: static;
  top: auto;
}
.card {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,.3);
  padding: 14px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 48px rgba(0,0,0,.35);
  border-color: rgba(255,255,255,0.14);
}
.card h3 {
  margin: 0 0 12px;
  font-size: 14px;
  letter-spacing: .01em;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.btn {
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.06);
  color: var(--text);
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
  cursor: pointer;
}
.week-label { font-size: 13px; color: var(--muted); font-weight: 600; }
.week-wrap { overflow-x: auto; }
.week-grid {
  min-width: 1240px;
  display: grid;
  grid-template-columns: repeat(7, minmax(180px, 1fr));
  gap: 10px;
}
.day-col {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid var(--line);
  border-radius: 14px;
  min-height: 300px;
  padding: 10px;
  transition: border-color .16s ease, background .16s ease;
}
.day-col.drop-target {
  border-color: #93c5fd;
  background: linear-gradient(180deg, #ffffff 0%, #eff6ff 100%);
}
.day-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 8px;
}
.day-add {
  border: none;
  background: #e8f0ff;
  color: #1d4ed8;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  cursor: pointer;
}
.event {
  border-left: 4px solid #9ca3af;
  background: #fff;
  border: 1px solid #edf0f5;
  border-left-width: 4px;
  border-radius: 12px;
  padding: 8px;
  margin-bottom: 7px;
  cursor: grab;
  transition: transform .15s ease, box-shadow .15s ease;
}
.event:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(15,23,42,.08);
}
.event.dragging { opacity: .45; }
.event-title {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
}
.event-meta {
  margin-top: 3px;
  font-size: 11px;
  color: var(--muted);
  display: flex;
  justify-content: space-between;
}
.event-x, .event-del {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
  border-radius: 4px;
}
.stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.stat {
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.08);
  padding: 12px;
  transition: border-color .2s, box-shadow .2s, transform .2s;
}
.stat:hover {
  border-color: rgba(255,255,255,0.14);
  box-shadow: 0 8px 32px rgba(0,0,0,.3);
  transform: translateY(-1px);
}
.stat .v { font-size: 24px; font-weight: 700; letter-spacing: -0.01em; }
.stat .l { font-size: 11px; color: var(--muted); margin-top: 2px; text-transform: uppercase; letter-spacing: .04em; }
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.hbar {
  margin-top: 8px;
}
.hrow {
  display: grid;
  grid-template-columns: 130px 1fr 54px;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}
.track {
  height: 10px;
  background: #eef2f7;
  border-radius: 999px;
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 999px;
}
.goal {
  margin-top: 8px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255,255,255,0.04);
}
.sync-box {
  display: none;
}
.sync-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.sync-title {
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}
.sync-meta {
  font-size: 12px;
  color: var(--muted);
}
.sync-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
.quick-ideas {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255,255,255,0.04);
}
.quick-row {
  display: grid;
  grid-template-columns: 1fr 180px 110px;
  gap: 8px;
}
.idea-board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 8px;
}
.decision-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px;
  margin-bottom: 10px;
}
.decision-col {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255,255,255,0.03);
  padding: 8px;
}
.decision-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: #475569;
  margin-bottom: 6px;
  font-weight: 700;
}
.decision-item {
  font-size: 11px;
  border-radius: 10px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  padding: 6px;
  margin-bottom: 6px;
  line-height: 1.35;
  color: var(--text);
}
.idea-draggable { cursor: grab; }
.idea-draggable.dragging {
  opacity: .5;
}
.decision-col[data-lane="urgent"] { background: rgba(239,68,68,.07); border-color: rgba(239,68,68,.25); }
.decision-col[data-lane="planifier"] { background: rgba(245,158,11,.06); border-color: rgba(245,158,11,.2); }
.decision-col[data-lane="non_urgent"] { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.08); }
.decision-col[data-lane="done"] { background: rgba(34,197,94,.06); border-color: rgba(34,197,94,.2); }
.decision-lane { min-height: 108px; }
.idea-item {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  background: rgba(255,255,255,0.04);
  padding: 8px;
  margin-bottom: 8px;
}
.idea-item.done {
  opacity: .72;
}
.idea-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.idea-title {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
}
.idea-meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.pill {
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  color: var(--muted);
  background: rgba(255,255,255,0.05);
}
.idea-actions {
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.btn-mini {
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  background: rgba(255,255,255,0.05);
  color: var(--text);
  font-size: 11px;
  padding: 5px 8px;
  cursor: pointer;
}
.btn-mini.primary {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}
.btn-mini.success {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
}
.goal-top {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 8px;
}
.goal-bar {
  height: 14px;
  border-radius: 999px;
  background: var(--ring);
  overflow: hidden;
}
.goal-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%);
}
.recent-row, .mix-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
}
.recent-row:last-child, .mix-row:last-child { border-bottom: none; }
.recent-icon { width: 22px; text-align: center; }
.recent-name { flex: 1; font-size: 13px; font-weight: 600; }
.recent-meta { font-size: 11px; color: var(--muted); }
.health-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.kpi {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255,255,255,0.04);
  padding: 12px;
}
.kpi.hero {
  background: rgba(255,255,255,0.07);
  border-color: rgba(255,255,255,0.12);
}
.kpi .v { font-size: 26px; font-weight: 700; }
.kpi .l { font-size: 12px; color: var(--muted); margin-top: 3px; }
.reco-item {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255,255,255,0.04);
  padding: 10px;
  font-size: 13px;
  line-height: 1.45;
  margin-bottom: 8px;
}
.split-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.muscle-map {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.zone {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  background: rgba(16, 185, 129, var(--alpha, .2));
}
.zone.zone-pecs { background: rgba(34, 197, 94, var(--alpha, .2)); }
.zone.zone-dos { background: rgba(59, 130, 246, var(--alpha, .2)); }
.zone.zone-epaules { background: rgba(249, 115, 22, var(--alpha, .2)); }
.zone.zone-biceps { background: rgba(244, 63, 94, var(--alpha, .2)); }
.zone.zone-triceps { background: rgba(168, 85, 247, var(--alpha, .2)); }
.zone.zone-core { background: rgba(14, 165, 233, var(--alpha, .2)); }
.zone.zone-jambes { background: rgba(16, 185, 129, var(--alpha, .2)); }
.zone.core, .zone.jambes {
  grid-column: span 2;
}
.muscle-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.muscle-row {
  display: grid;
  grid-template-columns: 92px 1fr 58px;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.muted { color: var(--muted); }
.fab {
  position: fixed;
  right: 18px;
  bottom: 20px;
  border: none;
  border-radius: 999px;
  background: #111827;
  color: #fff;
  padding: 14px 16px;
  font-weight: 600;
  box-shadow: 0 10px 24px rgba(17,24,39,.25);
  cursor: pointer;
}
.modal-bg {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,.45);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal {
  width: min(520px, 92vw);
  background: #fff;
  border-radius: 16px;
  border: 1px solid var(--line);
  padding: 14px;
}
.cmdk-bg {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,.45);
  display: none;
  align-items: flex-start;
  justify-content: center;
  z-index: 260;
  padding-top: 12vh;
}
.cmdk {
  width: min(640px, 94vw);
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 24px 60px rgba(15,23,42,.22);
  overflow: hidden;
}
.cmdk input {
  border: none;
  border-bottom: 1px solid #e5ebf3;
  border-radius: 0;
  font-size: 14px;
  padding: 14px 16px;
}
.cmdk input:focus {
  box-shadow: none;
}
.cmdk-list {
  max-height: 300px;
  overflow: auto;
  padding: 8px;
}
.cmdk-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  cursor: pointer;
}
.cmdk-item:hover,
.cmdk-item.active {
  background: #f1f7ff;
  border-color: #dbeafe;
}
.cmdk-key {
  font-size: 11px;
  color: #64748b;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.form-grid .full { grid-column: 1 / -1; }
label { font-size: 12px; color: var(--muted); display: block; margin-bottom: 4px; }
input, select {
  width: 100%;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 13px;
  background: rgba(255,255,255,0.06);
  color: var(--text);
}
input:focus, select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,.2);
}
.checkline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}
.checkline input {
  width: auto;
}
.modal-actions {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
}
.btn-primary {
  border: none;
  background: #111827;
  color: #fff;
  border-radius: 10px;
  padding: 9px 12px;
  cursor: pointer;
}
.btn-soft {
  border: 1px solid var(--line);
  background: #fff;
  color: #334155;
  border-radius: 10px;
  padding: 8px 10px;
  cursor: pointer;
}
.btn-soft.primary {
  border-color: #c7d2fe;
  background: #eef2ff;
  color: #3730a3;
  font-weight: 700;
}
.toast-wrap {
  position: fixed;
  right: 16px;
  top: 16px;
  z-index: 500;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toast {
  min-width: 260px;
  max-width: 420px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  background: rgba(15,23,42,0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 14px 40px rgba(0,0,0,.5);
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  animation: toastIn .25s cubic-bezier(.4,0,.2,1);
}
.toast.ok { border-color: rgba(34,197,94,.35); background: rgba(34,197,94,.12); color: #86efac; }
.toast.warn { border-color: rgba(245,158,11,.35); background: rgba(245,158,11,.12); color: #fcd34d; }
.toast.err { border-color: rgba(239,68,68,.35); background: rgba(239,68,68,.12); color: #fca5a5; }
@keyframes toastIn {
  from { opacity: 0; transform: translateY(-10px) scale(.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.btn-danger {
  border: 1px solid #fecaca;
  color: #b91c1c;
  background: #fff5f5;
  border-radius: 10px;
  padding: 9px 12px;
  cursor: pointer;
}
@media (max-width: 1100px) {
  .grid-planning { grid-template-columns: 1fr; }
  .planning-secondary { flex-direction: column; }
  .stack-sticky { position: static; }
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .health-grid { grid-template-columns: repeat(2, 1fr); }
  .split-grid { grid-template-columns: 1fr; }
}
@media (max-width: 680px) {
  .quick-row, .decision-grid { grid-template-columns: 1fr; }
  .stat-grid { grid-template-columns: 1fr 1fr; }
  .health-grid { grid-template-columns: 1fr 1fr; }
  .top { align-items: flex-start; flex-direction: column; gap: 8px; }
  .top-right { align-items: flex-start; flex-wrap: wrap; }
  .hero-strip { max-width: 100%; width: 100%; grid-template-columns: 1fr; }
}

/* ─── HERO RINGS ─────────────────────────────────────────────── */
.hero-rings-wrap { display:flex; flex-direction:column; gap:16px; margin-bottom:16px; }
.hero-rings { display:flex; gap:20px; align-items:center; justify-content:center; padding:20px 16px 16px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:20px; backdrop-filter:blur(20px); }
.ring-wrap { display:flex; flex-direction:column; align-items:center; gap:6px; }
.ring-container { position:relative; width:80px; height:80px; }
.ring-svg { width:80px; height:80px; transform:rotate(-90deg); }
.ring-bg { fill:none; stroke:rgba(255,255,255,0.08); stroke-width:7; }
.ring-fill { fill:none; stroke-width:7; stroke-linecap:round; stroke-dasharray:220; stroke-dashoffset:220; transition:stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1); }
.ring-label { font-size:10px; text-transform:uppercase; letter-spacing:0.07em; color:var(--muted); font-weight:700; text-align:center; }
.ring-center { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(90deg); text-align:center; line-height:1; }
.ring-score { font-size:19px; font-weight:800; letter-spacing:-0.02em; }

/* ─── TOP-NEW (barre de contrôle) ─────────────────────────────── */
.top-new { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:14px; padding:10px 14px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:16px; backdrop-filter:blur(20px); flex-wrap:wrap; }
.brand-compact { display:flex; align-items:center; gap:10px; }
.brand-compact h1 { font-size:20px; margin:0; letter-spacing:-0.02em; }
.brand-compact p { margin:2px 0 0; color:var(--muted); font-size:11px; }

/* ─── HERO METRICS STRIP ─────────────────────────────────────── */
.hero-metrics { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.hm-item { display:flex; flex-direction:column; align-items:flex-start; gap:1px; padding:7px 11px; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); border-radius:12px; min-width:64px; }
.hm-label { font-size:9px; text-transform:uppercase; letter-spacing:0.07em; color:var(--muted); font-weight:700; }
.hm-value { font-size:16px; font-weight:800; letter-spacing:-0.02em; line-height:1.1; }
.hm-delta { font-size:10px; font-weight:600; }
.hm-delta.positive { color:#22c55e; }
.hm-delta.negative { color:#ef4444; }
.hm-delta.neutral { color:var(--muted); }

/* ─── SYNC BTN & DEBUG ───────────────────────────────────────── */
.top-actions { display:flex; align-items:center; gap:8px; }
.btn-icon { width:34px; height:34px; border:1px solid rgba(255,255,255,0.10); background:rgba(255,255,255,0.05); border-radius:10px; display:inline-flex; align-items:center; justify-content:center; cursor:pointer; font-size:13px; transition:background .15s, transform .12s; color:var(--text); }
.btn-icon:hover { background:rgba(255,255,255,0.12); transform:scale(1.08); }

/* ─── DEBUG PANEL ────────────────────────────────────────────── */
.debug-panel { position:fixed; bottom:0; right:0; width:min(460px,95vw); max-height:55vh; background:#0a0f1e; border:1px solid #3b82f6; border-radius:16px 0 0 0; padding:14px 16px; overflow-y:auto; z-index:400; display:none; font-family:'SF Mono',monospace; font-size:11px; color:#94a3b8; }
.debug-panel.open { display:block; }
.debug-title { color:#3b82f6; font-weight:700; font-size:12px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; }
.debug-row { margin-bottom:3px; }
.debug-key { color:#64748b; }
.debug-val { color:#e2e8f0; }

/* ─── COCKPIT SEMAINE - nouveau ─────────────────────────────── */
.week-kpis { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:12px; }
.week-kpi { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:10px 12px; }
.week-kpi.danger { border-color:rgba(239,68,68,.35); background:rgba(239,68,68,.06); }
.week-kpi .wk-v { font-size:20px; font-weight:800; letter-spacing:-0.02em; }
.week-kpi .wk-l { font-size:9px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin-top:2px; font-weight:700; }
.acwr-alert { display:flex; align-items:center; gap:8px; padding:9px 12px; background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.3); border-radius:12px; font-size:11px; color:#fca5a5; margin-bottom:10px; }

/* ─── DONUT CATÉGORIES ───────────────────────────────────────── */
.cat-donut-wrap { display:flex; align-items:center; gap:16px; }
.cat-legend { display:flex; flex-direction:column; gap:6px; flex:1; }
.cat-leg-row { display:flex; align-items:center; gap:7px; font-size:11px; }
.cat-leg-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }

/* ─── PLANNING - agrandir ────────────────────────────────────── */
.week-wrap { overflow-x:auto; }
.day-col { min-height:500px; background:rgba(255,255,255,0.02); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px); border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:8px; flex:1; min-width:115px; position:relative; transition:border-color .2s, background .2s; }
.day-col:hover { border-color:rgba(255,255,255,0.14); background:rgba(255,255,255,0.035); }
.day-col.today { border-color:rgba(59,130,246,.3); background:rgba(59,130,246,0.04); box-shadow:0 0 24px rgba(59,130,246,.08); }
.day-col.drop-target { border-color:rgba(59,130,246,.5); background:rgba(59,130,246,0.08); box-shadow:0 0 30px rgba(59,130,246,.12); }
.day-head { font-size:11px; font-weight:700; color:var(--muted); margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; }
.day-add { background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); color:var(--muted); width:22px; height:22px; border-radius:6px; cursor:pointer; font-size:14px; font-weight:700; display:flex; align-items:center; justify-content:center; transition:all .15s; padding:0; }
.day-add:hover { background:rgba(59,130,246,.2); color:#60a5fa; border-color:rgba(59,130,246,.4); transform:scale(1.1); }
.event { border-left:3px solid #9ca3af; background:rgba(255,255,255,0.04); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); border-top:1px solid rgba(255,255,255,0.08); border-right:1px solid rgba(255,255,255,0.05); border-bottom:1px solid rgba(255,255,255,0.05); border-radius:10px; padding:6px 8px; margin-bottom:4px; cursor:grab; transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease, background .18s; overflow:hidden; box-sizing:border-box; }
.event:hover { transform:translateY(-1px) scale(1.01); box-shadow:0 8px 24px rgba(0,0,0,.4); background:rgba(255,255,255,0.08); border-top-color:rgba(255,255,255,0.12); }
.event.dragging { opacity:.5; transform:scale(.95); }
.event-title { font-size:11px; font-weight:700; line-height:1.3; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.event-meta { display:flex; align-items:center; gap:6px; margin-top:3px; flex-wrap:nowrap; }
.event-cat-pill { display:inline-flex; align-items:center; border-radius:4px; padding:1px 5px; font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; }
.event-x, .event-del { background:none; border:none; color:var(--muted); cursor:pointer; font-size:14px; padding:2px 6px; margin-left:4px; border-radius:4px; transition:all .15s; opacity:.6; }
.event-x:hover { background:rgba(59,130,246,.2); color:#60a5fa; opacity:1; }
.event-del:hover { background:rgba(239,68,68,.2); color:#f87171; opacity:1; }

/* ─── IDÉES - Quick Capture ─────────────────────────────────── */
.idea-capture-sticky { position:sticky; top:0; z-index:10; background:var(--bg); padding:8px 0 6px; }
.idea-inbox-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; margin-top:8px; }
.idea-filter-tabs { display:flex; gap:5px; flex-wrap:wrap; }
.idea-filter-tab { padding:3px 9px; border:1px solid rgba(255,255,255,.10); border-radius:999px; font-size:10px; font-weight:700; cursor:pointer; background:transparent; color:var(--muted); transition:all .12s; }
.idea-filter-tab.active { background:#3b82f6; border-color:#3b82f6; color:#fff; }
.idea-plan-btn { font-size:10px; padding:3px 8px; border:1px solid rgba(59,130,246,.4); background:rgba(59,130,246,.1); border-radius:6px; cursor:pointer; color:#93c5fd; font-weight:700; white-space:nowrap; }

/* ─── TRAVAIL & SOCIAL ───────────────────────────────────────── */
.prod-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px; }
.prod-stat { padding:14px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:16px; }
.prod-stat .ps-v { font-size:28px; font-weight:800; letter-spacing:-0.03em; }
.prod-stat .ps-l { font-size:10px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin-top:4px; }
.work-progress-bar { height:6px; background:rgba(255,255,255,0.08); border-radius:999px; overflow:hidden; margin-top:10px; }
.work-progress-fill { height:100%; background:linear-gradient(90deg,#3b82f6,#60a5fa); border-radius:999px; transition:width .8s ease; }
.social-progress-fill { height:100%; background:linear-gradient(90deg,#ec4899,#f472b6); border-radius:999px; transition:width .8s ease; }

/* ─── MISC OVERRIDES ─────────────────────────────────────────── */
.tabs { display:flex; gap:5px; margin-bottom:14px; background:rgba(255,255,255,0.04); padding:4px; border-radius:14px; border:1px solid rgba(255,255,255,0.08); width:fit-content; }
.tab { border:none; background:transparent; border-radius:10px; padding:7px 14px; font-size:13px; font-weight:600; cursor:pointer; color:var(--muted); transition:all .15s; position:relative; }
.tab::after { content:''; position:absolute; bottom:-1px; left:50%; width:0; height:2px; background:var(--accent); border-radius:2px; transition:width .25s cubic-bezier(0.4,0,0.2,1), left .25s cubic-bezier(0.4,0,0.2,1); }
.tab.active { background:rgba(255,255,255,0.10); color:var(--text); box-shadow:0 2px 6px rgba(0,0,0,.2); }
.tab.active::after { width:100%; left:0; }
.tab:hover:not(.active) { color:var(--text); }

/* ─── TOP-COCKPIT v4 ────────────────────────────────────────── */
.top-cockpit { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:14px; padding:12px 16px; background:var(--surface-1); border:1px solid var(--line); border-radius:var(--radius-lg); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); flex-wrap:wrap; }
.top-cockpit .brand-zone { display:flex; align-items:center; gap:10px; }
.top-cockpit .brand-zone h1 { font-size:22px; margin:0; letter-spacing:-0.03em; font-weight:800; }
.top-cockpit .brand-zone .sub { margin:2px 0 0; color:var(--muted); font-size:11px; }

/* ─── INDICATOR STRIP v4 (replaces hero-rings) ───────────────── */
.indicator-strip { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
.indicator-card { flex:1; min-width:220px; display:flex; flex-direction:column; gap:8px; padding:14px 16px; background:var(--surface-0); border:1px solid var(--line); border-radius:var(--radius-lg); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); transition:border-color .15s, background .15s; }
.indicator-card:hover { border-color:var(--border-hover); background:rgba(255,255,255,0.08); }
.indicator-card .ic-top { display:flex; align-items:center; justify-content:space-between; }
.indicator-card .ic-label { display:flex; align-items:center; gap:6px; font-size:12px; font-weight:700; color:var(--text-secondary); }
.indicator-card .ic-label .ic-icon { font-size:16px; }
.indicator-card .ic-value { font-size:16px; font-weight:800; letter-spacing:-0.02em; }
.indicator-card .ic-bar { height:8px; background:var(--surface-2); border-radius:var(--radius-full); overflow:hidden; }
.indicator-card .ic-fill { height:100%; border-radius:var(--radius-full); transition:width .8s cubic-bezier(0.4,0,0.2,1); }

/* ─── PLANNING PAGE v6 ────────────────────────────────────────── */
.planning-top-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:16px; }
@media (max-width:768px) { .planning-top-row { grid-template-columns:1fr; } }
.planning-donut-card { background:var(--surface-0); border:1px solid var(--line); border-radius:var(--radius-lg); padding:18px 20px; }
.planning-donut-title { font-size:14px; font-weight:800; letter-spacing:-0.02em; margin-bottom:12px; }
.planning-donut-body { display:flex; align-items:center; gap:18px; }
.planning-donut-legend { display:flex; flex-direction:column; gap:5px; flex:1; }
.planning-sync-card { background:var(--surface-0); border:1px solid var(--line); border-radius:var(--radius-lg); padding:18px 20px; display:flex; flex-direction:column; gap:10px; }
.planning-sync-top { display:flex; align-items:center; gap:8px; }
.btn-sync-large { display:flex; align-items:center; justify-content:center; gap:8px; width:100%; padding:12px 20px; background:linear-gradient(135deg,#3b82f6,#6366f1); color:#fff; border:none; border-radius:var(--radius-md); font-size:14px; font-weight:700; cursor:pointer; transition:opacity .15s, transform .12s; font-family:inherit; }
.btn-sync-large:hover { opacity:.9; transform:translateY(-1px); }
.btn-sync-large:disabled { opacity:.4; cursor:default; transform:none; }
.btn-sync-large .sync-icon { font-size:16px; }
.planning-sync-info { font-size:11px; color:var(--muted); text-align:center; }
.planning-mini-strip { display:flex; gap:6px; flex-wrap:wrap; }
.pm-chip { display:inline-flex; align-items:center; gap:4px; padding:4px 10px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:var(--radius-full); font-size:11px; color:var(--text-secondary); }
.pm-chip b { color:var(--chip-color, var(--text)); font-weight:800; }
.cal-card { padding:14px; }
.cal-nav { padding:8px 14px; font-size:14px; font-weight:700; }
.board-header-row { display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; }
.board-header-row h3 { margin:0; font-size:16px; font-weight:800; letter-spacing:-0.02em; }
.board-tip { font-size:11px; color:var(--muted); margin-bottom:12px; padding:6px 10px; background:rgba(59,130,246,0.06); border:1px solid rgba(59,130,246,0.15); border-radius:var(--radius-sm); }

/* ─── PILOTAGE v5 (legacy compat) ─────────────────────────────── */
.pilotage-header { display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:16px; }
.pilotage-header h2 { margin:0; font-size:18px; font-weight:800; letter-spacing:-.02em; flex:1; }
.sync-status { display:flex; align-items:center; gap:8px; font-size:12px; color:var(--muted); }
.sync-dot-big { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.sync-dot-big.ok { background:#22c55e; box-shadow:0 0 6px #22c55e66; }
.sync-dot-big.warn { background:#f59e0b; }
.sync-dot-big.err { background:#ef4444; }
.sync-dot-big.off { background:#64748b; }
.btn-sync { display:inline-flex; align-items:center; gap:6px; padding:7px 14px; background:var(--accent); color:#fff; border:none; border-radius:var(--radius-sm); font-size:12px; font-weight:700; cursor:pointer; transition:opacity .15s; }
.btn-sync:hover { opacity:.85; }
.btn-sync:disabled { opacity:.45; cursor:default; }

/* ─── PILOTAGE MINI INDICATORS ───────────────────────────────── */
.pilotage-mini-strip { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:16px; }
.pilotage-mini { display:flex; align-items:center; gap:8px; padding:10px 14px; background:var(--surface-0); border:1px solid var(--line); border-radius:var(--radius-sm); font-size:12px; font-weight:700; min-width:120px; flex:1; transition:border-color .15s, background .15s, transform .15s ease; }
.pilotage-mini:hover { border-color:var(--border-hover); background:rgba(255,255,255,0.08); transform:translateY(-1px); }
.pilotage-mini .pm-icon { font-size:18px; }
.pilotage-mini .pm-body { display:flex; flex-direction:column; gap:2px; }
.pilotage-mini .pm-label { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); }
.pilotage-mini .pm-value { font-size:15px; font-weight:800; }

/* ─── PILOTAGE CALENDAR ───────────────────────────────────────── */
.pilotage-cal-header { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
.pilotage-cal-header h3 { margin:0; font-size:14px; font-weight:700; flex:1; }

/* ─── DAY-COL TODAY highlight ─────────────────────────────────── */
.day-col.today { border:2px solid var(--accent); background:rgba(59,130,246,0.04); }
.day-col.today .day-head { color:var(--accent); }
.today-badge { display:inline-block; font-size:8px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; background:var(--accent); color:#fff; padding:1px 5px; border-radius:4px; margin-left:4px; }

/* ─── BOARD v5 ────────────────────────────────────────────────── */
.board-section { margin-top:16px; }
.board-section h3 { margin:0 0 12px; font-size:14px; font-weight:700; }
.quick-add-row { display:flex; gap:8px; margin-bottom:14px; flex-wrap:wrap; }
.quick-add-row input { flex:1; min-width:180px; padding:9px 12px; background:var(--surface-1); border:1px solid var(--line); border-radius:var(--radius-sm); color:var(--text); font-size:13px; font-family:inherit; outline:none; }
.quick-add-row input:focus { border-color:var(--accent); }
.quick-add-row select { padding:9px 10px; background:var(--surface-1); border:1px solid var(--line); border-radius:var(--radius-sm); color:var(--text); font-size:12px; font-family:inherit; cursor:pointer; }
.board-grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; align-items:start; }
@media (max-width:1200px) { .board-grid { grid-template-columns:repeat(3, 1fr); } }
@media (max-width:768px)  { .board-grid { grid-template-columns:1fr; } }
.board-col { background:rgba(255,255,255,0.025); backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.07); border-radius:var(--radius-md); padding:10px; min-height:120px; transition:border-color .2s, background .2s; }
.board-col.drop-target { border-color:rgba(59,130,246,.45); background:rgba(59,130,246,.06); }
.board-col-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
.board-col-title { font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; }
.board-col-count { font-size:11px; font-weight:700; padding:2px 7px; border-radius:99px; background:rgba(255,255,255,.07); }
.board-lane { min-height:60px; display:flex; flex-direction:column; gap:6px; }
.board-card { background:rgba(255,255,255,0.05); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); border:1px solid rgba(255,255,255,0.08); border-left:3px solid var(--accent); border-radius:var(--radius-sm); padding:8px 10px; cursor:grab; position:relative; transition:transform .18s ease, box-shadow .18s ease, background .18s; }
.board-card:hover { box-shadow:0 8px 24px rgba(0,0,0,.4); transform:translateY(-2px) scale(1.01); background:rgba(255,255,255,0.08); }
.board-card.dragging { opacity:.4; transform:scale(.95); }
.board-card .bc-title { font-size:12px; font-weight:700; margin-bottom:4px; line-height:1.3; word-break:break-word; }
.board-card .bc-domain { font-size:10px; font-weight:700; margin-bottom:4px; }
.board-card .bc-actions { display:flex; gap:4px; flex-wrap:wrap; margin-top:5px; }
.bc-btn { font-size:10px; padding:3px 7px; border:1px solid var(--line); border-radius:4px; background:var(--surface-0); color:var(--muted); cursor:pointer; font-family:inherit; font-weight:600; transition:background .12s, color .12s; }
.bc-btn:hover { background:var(--surface-2); color:var(--text); }
.bc-btn.danger:hover { background:#ef444420; color:#ef4444; border-color:#ef444460; }
.board-col-empty { font-size:11px; color:var(--muted); padding:8px 0; text-align:center; }
/* Couleurs par colonne */
.board-col[data-triage="a_determiner"] .board-col-title { color:#94a3b8; }
.board-col[data-triage="urgent"]       .board-col-title { color:#ef4444; }
.board-col[data-triage="a_planifier"]  .board-col-title { color:#3b82f6; }
.board-col[data-triage="non_urgent"]   .board-col-title { color:#64748b; }
.board-col[data-triage="termine"]      .board-col-title { color:#22c55e; }
.board-col[data-triage="urgent"] { border-top:2px solid #ef4444; }
.board-col[data-triage="a_planifier"] { border-top:2px solid #3b82f6; }

/* ─── CAL + DROP ZONES ────────────────────────────────────────── */
.drop-target { background:rgba(59,130,246,0.08) !important; border-color:var(--accent) !important; }
.day-col.drop-from-cal { background:rgba(239,68,68,0.06) !important; border-color:#ef444440 !important; }
</style>
</head>
<body>
<div class="app">
  <!-- ═══ TOP COCKPIT v4 ═══ -->
  <div class="top-cockpit">
    <div class="brand-zone">
      <div class="mascot" id="mascot" title="PerformOS"><div class="mascot-body"><div class="mascot-face"><div class="mascot-eyes"><div class="mascot-eye"></div><div class="mascot-eye"></div></div><div class="mascot-mouth"></div></div></div></div>
      <div>
        <h1>Simsam</h1>
        <p class="sub">__TODAY__ · __NOW__</p>
      </div>
    </div>
    <div class="top-actions">
      <button class="apple-cal-status __SYNC_BADGE_CLASS__" id="appleCalBtn" onclick="syncAll()">
        <span class="apple-cal-icon">📅</span>
        <div class="apple-cal-body">
          <span class="apple-cal-label">Calendrier Apple</span>
          <span class="apple-cal-sub" id="appleCalSub">__SYNC_BADGE_LABEL__</span>
        </div>
        <span class="apple-cal-spinner" id="appleCalSpinner" style="display:none">⟳</span>
      </button>
      <button class="btn-icon" id="debugPanelBtn" title="Debug PerformOS">🐛</button>
      <button class="badge __CAL_BADGE_CLASS__" id="calendarBadgeBtn" style="display:none"></button>
    </div>
  </div>

  <!-- ═══ INDICATOR STRIP v4 (replaces hero-rings) ═══ -->
  <div class="indicator-strip">
    <div class="indicator-card">
      <div class="ic-top">
        <span class="ic-label"><span class="ic-icon">🫀</span> Readiness</span>
        <span class="ic-value" style="color:__RING_RECOVERY_COLOR__">__RING_RECOVERY__<span style="font-size:10px;color:var(--muted)">/100</span></span>
      </div>
      <div class="ic-bar"><div class="ic-fill" style="width:__RING_RECOVERY__%;background:__RING_RECOVERY_COLOR__"></div></div>
    </div>
    <div class="indicator-card">
      <div class="ic-top">
        <span class="ic-label"><span class="ic-icon">🏃</span> Charge sport</span>
        <span class="ic-value" style="color:var(--sante)">__GOAL_DONE__h<span style="font-size:10px;color:var(--muted)"> / __GOAL_TARGET__h</span></span>
      </div>
      <div class="ic-bar"><div class="ic-fill" style="width:__GOAL_PCT__%;background:var(--sante)"></div></div>
    </div>
    <div class="indicator-card">
      <div class="ic-top">
        <span class="ic-label"><span class="ic-icon">💼</span> Travail</span>
        <span class="ic-value" style="color:var(--travail)">__WORK_WEEK_H__h<span style="font-size:10px;color:var(--muted)"> / 40h</span></span>
      </div>
      <div class="ic-bar"><div class="ic-fill" style="width:__WORK_WEEK_PCT__%;background:var(--travail)"></div></div>
    </div>
    <div class="indicator-card donut-card">
      <div class="ic-top">
        <span class="ic-label"><span class="ic-icon">🎯</span> Répartition</span>
      </div>
      <div class="donut-canvas-wrap">
        <canvas id="weekDonutChart" width="80" height="80" style="flex-shrink:0"></canvas>
        <div class="donut-legend" id="donutLegend"><div style="font-size:10px;color:var(--muted)">Chargement…</div></div>
      </div>
    </div>
  </div>

  <div class="tabs">
    <button class="tab active" data-tab="planning">Pilotage</button>
    <button class="tab" data-tab="sante">Santé</button>
    <button class="tab" data-tab="travail">Travail</button>
    <button class="tab" data-tab="social">Social</button>
  </div>

  <section class="section active" id="sec-planning">

    <!-- ═══ PLANNING HEADER — donut + sync ═══ -->
    <div class="planning-top-row">
      <div class="planning-donut-card">
        <div class="planning-donut-title">Ma semaine</div>
        <div class="planning-donut-body">
          <canvas id="weekDonutChart2" width="120" height="120"></canvas>
          <div class="planning-donut-legend" id="donutLegend2"></div>
        </div>
      </div>
      <div class="planning-sync-card">
        <div class="planning-sync-top">
          <span class="sync-dot-big" id="syncDotBig"></span>
          <span id="syncStatusText" style="font-size:12px;color:var(--muted)">—</span>
          <span id="syncLastTime" style="color:var(--muted);font-size:11px;"></span>
        </div>
        <button class="btn-sync-large" id="syncBtn" onclick="syncAll()">
          <span class="sync-icon">⟳</span> Synchroniser
        </button>
        <div class="planning-sync-info">Apple Calendar + Gmail</div>
        <!-- Mini indicateurs inline -->
        <div class="planning-mini-strip">
          <div class="pm-chip" style="--chip-color:#22c55e"><span>🏃</span> <b id="mini-sport">__GOAL_DONE__h</b></div>
          <div class="pm-chip" style="--chip-color:#a78bfa"><span>🧘</span> <b id="mini-yoga">0h</b></div>
          <div class="pm-chip" style="--chip-color:#3b82f6"><span>💼</span> <b id="mini-travail">__WORK_WEEK_H__h</b></div>
          <div class="pm-chip" style="--chip-color:#06b6d4"><span>🎓</span> <b id="mini-lecon">0h</b></div>
        </div>
      </div>
    </div>

    <!-- ═══ PLANNING SEMAINE ═══ -->
    <div class="card cal-card">
      <div class="pilotage-cal-header">
        <button class="btn cal-nav" id="prevWeek">&larr;</button>
        <h3 id="weekLabel">Semaine</h3>
        <button class="btn cal-nav" id="nextWeek">&rarr;</button>
      </div>
      <div class="week-wrap">
        <div class="week-grid" id="weekGrid"></div>
      </div>
    </div>

    <!-- ═══ BOARD TÂCHES ═══ -->
    <div class="card board-section">
      <div class="board-header-row">
        <h3>Mes tâches</h3>
      </div>
      <div class="quick-add-row">
        <input id="taskText" type="text" placeholder="Nouvelle tâche…" />
        <select id="taskDomain">
          <option value="sport">🏃 Sport</option>
          <option value="travail">💼 Travail</option>
          <option value="yoga">🧘 Yoga</option>
          <option value="lecon">🎓 Leçon</option>
          <option value="formation">📚 Formation</option>
          <option value="social">💬 Social</option>
          <option value="autre">🧩 Autre</option>
        </select>
        <select id="taskCalendar" title="Calendrier cible">
          <option value="Personnel">📘 Personnel (iCloud)</option>
          <option value="simon.hingant@gmail.com">📧 Gmail</option>
          <option value="Calendrier">📙 Calendrier (partagé)</option>
        </select>
        <button class="btn-primary" id="addTaskBtn">+ Ajouter</button>
      </div>
      <div class="board-tip">Glisse une tâche vers le calendrier · Clic ✕ pour supprimer</div>
      <div class="board-grid" id="boardGrid"></div>
    </div>

  </section>

  <section class="section" id="sec-sante">
    <div class="card" style="margin-bottom:12px;">
      <h3>Synthèse santé</h3>
      <div class="health-grid">
        <div class="kpi hero"><div class="v">__READINESS_GLOBAL__</div><div class="l">Condition globale /100</div></div>
        <div class="kpi hero"><div class="v">__WBS__</div><div class="l">Readiness /100</div></div>
        <div class="kpi hero"><div class="v">__BODY_BATTERY__%</div><div class="l">Body Battery</div></div>
        <div class="kpi hero"><div class="v">__HRV__</div><div class="l">HRV (ms)</div></div>
        <div class="kpi"><div class="v">__RHR__</div><div class="l">RHR (bpm)</div></div>
        <div class="kpi"><div class="v">__SLEEP_H__h</div><div class="l">Sommeil</div></div>
        <div class="kpi"><div class="v">__VO2MAX__</div><div class="l">VO2Max</div></div>
        <div class="kpi"><div class="v">__STEPS__</div><div class="l">Pas (dernier)</div></div>
        <div class="kpi"><div class="v">__PRED_10K__</div><div class="l">Estimation 10km</div></div>
        <div class="kpi"><div class="v">__ACWR__</div><div class="l">ACWR</div></div>
        <div class="kpi"><div class="v">__FRESHNESS__</div><div class="l">Fraîcheur data (__FRESHNESS_LABEL__)</div></div>
      </div>
      <div class="muted" style="font-size:12px; margin-top:8px;">Âge données: HRV J-__HRV_DAYS__, RHR J-__RHR_DAYS__, sommeil J-__SLEEP_DAYS__</div>
    </div>

    <div class="split-grid" style="margin-bottom:12px;">
      <div class="card">
        <h3>Charge entraînement (semaine)</h3>
        __LOAD_SPLIT_HTML__
      </div>
      <div class="card">
        <h3>Analyse musculaire</h3>
        <div class="muscle-map" style="margin-bottom:10px;">
          <div class="zone zone-pecs" style="--alpha: __ZONE_PECS__;">Pecs</div>
          <div class="zone zone-dos" style="--alpha: __ZONE_DOS__;">Dos</div>
          <div class="zone zone-epaules" style="--alpha: __ZONE_EPAULES__;">Épaules</div>
          <div class="zone zone-biceps" style="--alpha: __ZONE_BICEPS__;">Biceps</div>
          <div class="zone zone-triceps" style="--alpha: __ZONE_TRICEPS__;">Triceps</div>
          <div class="zone core zone-core" style="--alpha: __ZONE_CORE__;">Core</div>
          <div class="zone jambes zone-jambes" style="--alpha: __ZONE_JAMBES__;">Jambes</div>
        </div>
        <div class="muscle-rows">
          __MUSCLE_BARS_HTML__
        </div>
      </div>
    </div>

    <div class="card">
      <h3>Recommandations</h3>
      __RECO_HTML__
      <div class="muted" style="font-size:12px; margin-top:8px;">Ces recommandations sont recalculées à chaque génération.</div>
    </div>
  </section>

  <section class="section" id="sec-travail">
    <div class="card">
      <h3>Travail</h3>
      <div class="prod-grid">
        <div class="prod-stat">
          <div class="ps-v" style="color:#3b82f6">__WORK_WEEK_H__h</div>
          <div class="ps-l">Heures planifiées cette semaine</div>
          <div class="work-progress-bar" style="margin-top:10px;"><div class="work-progress-fill" style="width:__WORK_WEEK_PCT__%"></div></div>
        </div>
        <div class="prod-stat">
          <div class="ps-v" id="workFocusHrs">—</div>
          <div class="ps-l">Focus planifié (h)</div>
        </div>
      </div>
      <h4 style="margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);">Tâches cette semaine</h4>
      <div id="workTasksList" style="display:flex;flex-direction:column;gap:6px;margin-bottom:16px;"></div>
      <h4 style="margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);">Tendance 4 semaines</h4>
      <canvas id="workTrendChart" width="320" height="100" style="width:100%;height:100px;max-width:100%;"></canvas>
    </div>
  </section>

  <section class="section" id="sec-social">
    <div class="card">
      <h3>Social</h3>
      <div class="prod-grid">
        <div class="prod-stat">
          <div class="ps-v" style="color:#ec4899">__SOCIAL_WEEK_H__h</div>
          <div class="ps-l">Relationnel cette semaine</div>
          <div class="work-progress-bar" style="margin-top:10px;"><div class="social-progress-fill" style="width:__SOCIAL_WEEK_PCT__%"></div></div>
        </div>
        <div class="prod-stat">
          <div class="ps-v" id="socialUpcoming">—</div>
          <div class="ps-l">Événements à venir</div>
        </div>
      </div>
      <h4 style="margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);">Événements sociaux</h4>
      <div id="socialEventsList" style="display:flex;flex-direction:column;gap:6px;margin-bottom:16px;"></div>
      <h4 style="margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);">Tendance 4 semaines</h4>
      <canvas id="socialTrendChart" width="320" height="100" style="width:100%;height:100px;max-width:100%;"></canvas>
    </div>
  </section>
</div>

<div class="toast-wrap" id="toastWrap"></div>

<div class="debug-panel" id="debugPanel">
  <div class="debug-title">🐛 Debug PerformOS <button onclick="document.getElementById('debugPanel').classList.remove('open')" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:12px;">✕</button></div>
  <div class="debug-row"><span class="debug-key">API:</span> <span class="debug-val" id="dbgApi">—</span></div>
  <div class="debug-row"><span class="debug-key">WBS:</span> <span class="debug-val">__WBS__</span></div>
  <div class="debug-row"><span class="debug-key">TSB:</span> <span class="debug-val">__TSB__</span></div>
  <div class="debug-row"><span class="debug-key">CTL:</span> <span class="debug-val">__CTL__</span></div>
  <div class="debug-row"><span class="debug-key">ATL:</span> <span class="debug-val">__ATL__</span></div>
  <div class="debug-row"><span class="debug-key">ACWR:</span> <span class="debug-val">__ACWR__</span></div>
  <div class="debug-row"><span class="debug-key">HRV:</span> <span class="debug-val">__HRV__ ms (Δ __HRV_DELTA__ ms)</span></div>
  <div class="debug-row"><span class="debug-key">RHR:</span> <span class="debug-val">__RHR__ bpm (Δ __RHR_DELTA__ / base __RHR_BASELINE__)</span></div>
  <div class="debug-row"><span class="debug-key">Sleep:</span> <span class="debug-val">__SLEEP_H__h</span></div>
  <div class="debug-row"><span class="debug-key">Rings R/A/S:</span> <span class="debug-val">__RING_RECOVERY__ / __RING_ACTIVITY__ / __RING_SLEEP__</span></div>
  <div class="debug-row"><span class="debug-key">Sync:</span> <span class="debug-val">__SYNC_BADGE_LABEL__ (__SYNC_BADGE_CLASS__)</span></div>
  <div class="debug-row"><span class="debug-key">Events:</span> <span class="debug-val" id="dbgEvents">—</span></div>
  <div class="debug-row"><span class="debug-key">Ideas:</span> <span class="debug-val" id="dbgIdeas">—</span></div>
</div>

<script>
// ── PerformOS Cockpit v5 — Pilotage JS ────────────────────────────────────────
const TYPE_DEFS = __TYPE_DEFS__;
const CATEGORY_LABELS = __CATEGORY_LABELS__;
const BASE_EVENTS = __PLANNER_EVENTS__;
const STORAGE_KEY = 'performos_planner_v5';
const WEEK_START_ISO = '__WEEK_START__';
const GOAL_TARGET = __GOAL_TARGET_NUM__;
const READINESS_GLOBAL = __READINESS_GLOBAL_NUM__;
const API_TOKEN = __API_TOKEN_JS__;
const CAL_SYNC_ENABLED = __CAL_SYNC_ENABLED__;
let API_ENABLED = location.protocol.startsWith('http');
const API_BASE = '/api/planner';
// Domain colors and icons
const DOM_COLORS = {
  sport:'#22c55e', yoga:'#a78bfa', travail:'#3b82f6',
  formation:'#f59e0b', lecon:'#06b6d4', social:'#ec4899', autre:'#64748b',
  sante:'#22c55e', relationnel:'#ec4899', apprentissage:'#f59e0b',
};
const DOM_ICONS = {
  sport:'🏃', yoga:'🧘', travail:'💼',
  formation:'📚', lecon:'🎓', social:'💬', autre:'🧩',
  sante:'🏃', relationnel:'💬', apprentissage:'📚',
};

let weekOffset = 0;
let currentEvents = [];
let currentBoard  = [];
let _workChart = null;
let _socialChart = null;

function escapeHtml(v) {
  return String(v||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

function showToast(message, kind) {
  const wrap = document.getElementById('toastWrap');
  if (!wrap) return;
  const el = document.createElement('div');
  el.className = 'toast ' + (kind || 'ok');
  el.textContent = message;
  wrap.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(-4px)'; setTimeout(() => el.remove(), 220); }, 3200);
}

function parseIso(s) { if (!s) return null; const x = new Date(String(s).replace(' ','T')); return Number.isNaN(x.getTime()) ? null : x; }
function toIsoNoMs(d) {
  // Local ISO (pas UTC) pour éviter le décalage timezone
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')
    +'T'+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')+':'+String(d.getSeconds()).padStart(2,'0');
}
function addMin(d,m) { return new Date(d.getTime()+m*60000); }
function startOfWeek(b) { const d=new Date(b); const day=(d.getDay()+6)%7; d.setDate(d.getDate()-day); d.setHours(0,0,0,0); return d; }
function addDays(d,n) { const x=new Date(d); x.setDate(x.getDate()+n); return x; }
function isoDate(d) { return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function hm(d) { return String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0'); }
function relativeTime(isoStr) {
  if (!isoStr) return '';
  const d = typeof isoStr === 'string' ? new Date(isoStr) : isoStr;
  if (isNaN(d)) return isoStr;
  const diff = Math.floor((Date.now() - d) / 1000);
  if (diff < 60) return "\u00e0 l'instant";
  if (diff < 3600) return 'il y a ' + Math.floor(diff/60) + ' min';
  if (diff < 86400) return 'il y a ' + Math.floor(diff/3600) + 'h';
  return 'il y a ' + Math.floor(diff/86400) + 'j';
}
function shortDateFr(d) { return String(d.getDate()).padStart(2,'0')+'/'+String(d.getMonth()+1).padStart(2,'0'); }
function domainColor(cat) { return DOM_COLORS[cat]||DOM_COLORS.autre; }
function domainIcon(cat) { return DOM_ICONS[cat]||'🧩'; }

function inferTypeFromEvent(ev) {
  if (ev.type && TYPE_DEFS[ev.type]) return ev.type;
  const text = ((ev.title||'')+' '+(ev.category||'')).toLowerCase();
  if (/muscu|strength|gym|full body/.test(text)) return 'musculation';
  if (/yoga|mobil|stretch|pilates/.test(text)) return 'yoga';
  if (/run|course|cardio|10km|trail/.test(text)) return 'cardio';
  if (/tennis|golf|swim|natation|sport/.test(text)) return 'sport_libre';
  const c = ev.category||'';
  if (c==='travail') return 'travail';
  if (c==='formation'||c==='apprentissage') return 'formation';
  if (c==='lecon') return 'lecon';
  if (/leçon|lecon|lesson|cours de/.test(text)) return 'lecon';
  if (c==='social'||c==='relationnel') return 'social';
  if (c==='yoga') return 'yoga';
  if (c==='sport'||c==='sante') return 'cardio';
  return 'autre';
}

function eventDurationMin(ev) {
  const s=parseIso(ev.start_at), e=parseIso(ev.end_at);
  if (!s||!e) return 60;
  return Math.max(5, Math.round((e-s)/60000));
}

function apiHeaders() {
  const h={'Content-Type':'application/json'};
  if (API_TOKEN) h['X-PerformOS-Token']=API_TOKEN;
  return h;
}

// ─── Sync status UI ───────────────────────────────────────────────────────────
function updateSyncUI(connected, lastTime, error) {
  const dot=document.getElementById('syncDotBig');
  const txt=document.getElementById('syncStatusText');
  const ts=document.getElementById('syncLastTime');
  if (!dot) return;
  dot.className='sync-dot-big '+(error?'err':connected?'ok':'off');
  txt.textContent=error?'Erreur sync':connected?'Apple connecté':'Apple non connecté';
  if (lastTime && ts) ts.textContent='· '+lastTime;
  updateAppleCalStatus(error?'error':connected?'ok':'idle', lastTime||null);
}

// ─── Apple Calendar status (top bar) ──────────────────────────────────────────
function updateAppleCalStatus(state, time, errorDetail) {
  const btn=document.getElementById('appleCalBtn');
  const sub=document.getElementById('appleCalSub');
  const spinner=document.getElementById('appleCalSpinner');
  if(!btn) return;
  btn.className='apple-cal-status';
  if(spinner) spinner.style.display='none';
  if(state==='syncing'){
    btn.classList.add('syncing');
    if(sub) sub.textContent='Synchronisation\u2026';
    if(spinner) spinner.style.display='inline';
  } else if(state==='ok'){
    btn.classList.add('ok');
    if(sub) sub.textContent='Sync \u00b7 '+relativeTime(time);
  } else if(state==='permission_denied'){
    btn.classList.add('error');
    if(sub) sub.textContent='\u26a0\ufe0f Autorisation requise';
    btn.title='Acc\u00e8s Calendriers refus\u00e9 \u2014 Syst\u00e8me > Confidentialit\u00e9 > Calendriers';
  } else if(state==='error'){
    btn.classList.add('error');
    if(sub) sub.textContent=errorDetail||'Erreur de synchro';
  } else {
    if(sub) sub.textContent=CAL_SYNC_ENABLED?'Connect\u00e9':'Non connect\u00e9';
  }
}

// ─── Vérification permission calendrier au démarrage ─────────────────────────
async function checkCalendarPermission() {
  if(!CAL_SYNC_ENABLED) return;
  try {
    const r=await fetch(API_BASE+'/calendar/status');
    if(!r.ok) return;
    const d=await r.json();
    if(d.permission==='denied'||d.error==='calendar_permission_denied'){
      updateAppleCalStatus('permission_denied');
      updateSyncUI(false,null,true);
      // Toast d'aide persistant avec instructions
      showToast('\u26a0\ufe0f Acc\u00e8s Calendriers refus\u00e9 \u2014 Syst\u00e8me > Confidentialit\u00e9 & S\u00e9curit\u00e9 > Calendriers > Terminal \u2713','warn');
    } else if(d.ok && d.permission==='granted'){
      updateAppleCalStatus('idle');
      updateSyncUI(true,null,false);
    }
  } catch(_){}
}

// ─── Donut répartition semaine ─────────────────────────────────────────────────
let _weekDonut=null;
function renderWeekDonut(dur) {
  const cv=document.getElementById('weekDonutChart2')||document.getElementById('weekDonutChart');
  if(!cv||typeof Chart==='undefined') return;
  if(_weekDonut){_weekDonut.destroy();_weekDonut=null;}
  const cats=[
    {k:'sport',   label:'Sport',     color:'#22c55e'},
    {k:'travail', label:'Travail',   color:'#3b82f6'},
    {k:'yoga',    label:'Yoga',      color:'#a78bfa'},
    {k:'lecon',   label:'Leçon',     color:'#06b6d4'},
    {k:'social',  label:'Social',    color:'#ec4899'},
    {k:'formation',label:'Formation',color:'#f59e0b'},
    {k:'autre',   label:'Autre',     color:'#64748b'},
  ];
  const total=Object.values(dur).reduce((a,b)=>a+(b||0),0);
  const data=cats.map(c=>Math.max(0,dur[c.k]||0));
  const hasData=data.some(v=>v>0);
  _weekDonut=new Chart(cv,{
    type:'doughnut',
    data:{
      labels:cats.map(c=>c.label),
      datasets:[{
        data:hasData?data:[1],
        backgroundColor:hasData?cats.map(c=>c.color):['rgba(255,255,255,0.06)'],
        borderWidth:0,hoverOffset:4
      }]
    },
    options:{
      responsive:false,
      plugins:{
        legend:{display:false},
        tooltip:{callbacks:{label:ctx=>{
          if(!hasData) return 'Aucune donnée';
          const pct=total>0?((ctx.raw/total)*100).toFixed(0):0;
          return ctx.label+' · '+(ctx.raw||0).toFixed(1)+'h · '+pct+'%';
        }}}
      },
      cutout:'62%'
    }
  });
  const leg=document.getElementById('donutLegend2')||document.getElementById('donutLegend');
  if(leg){
    const rows=cats.filter(c=>(dur[c.k]||0)>0.01).map(c=>`<div class="donut-leg-row"><span class="donut-leg-dot" style="background:${c.color}"></span><span class="donut-leg-label">${c.label}</span><span class="donut-leg-val">${(dur[c.k]||0).toFixed(1)}h</span></div>`);
    leg.innerHTML=rows.length?rows.join(''):'<div style="font-size:10px;color:var(--muted)">Aucune donnée</div>';
  }
}

// ─── Mascot ───────────────────────────────────────────────────────────────────
function initMascot() {
  const m=document.getElementById('mascot'); if(!m) return;
  m.addEventListener('click',()=>{
    m.classList.remove('bounce');
    void m.offsetWidth; // force reflow
    m.classList.add('bounce');
    setTimeout(()=>m.classList.remove('bounce'),520);
  });
}

// ─── Category durations ───────────────────────────────────────────────────────
function normCat(c) { return {sante:'sport',relationnel:'social',apprentissage:'formation'}[c]||c; }

function categoryDurations(events) {
  const out={sport:0,yoga:0,travail:0,formation:0,lecon:0,social:0,autre:0};
  events.forEach(ev=>{
    const s=parseIso(ev.start_at), e=parseIso(ev.end_at);
    if(!s||!e) return;
    const h=Math.max(0,(e-s)/3600000);
    const cat=normCat(ev.category||'autre');
    out[cat]=(out[cat]||0)+h;
  });
  return out;
}

function updateMiniIndicators(dur) {
  const fmt=v=>v.toFixed(1)+'h';
  const el=id=>document.getElementById(id);
  if(el('mini-sport'))     el('mini-sport').textContent=fmt(dur.sport||0);
  if(el('mini-yoga'))      el('mini-yoga').textContent=fmt(dur.yoga||0);
  if(el('mini-travail'))   el('mini-travail').textContent=fmt(dur.travail||0);
  if(el('mini-formation')) el('mini-formation').textContent=fmt(dur.formation||0);
  if(el('mini-lecon'))     el('mini-lecon').textContent=fmt(dur.lecon||0);
  if(el('heroWork'))       el('heroWork').textContent=fmt(dur.travail||0);
  if(el('heroSocial'))     el('heroSocial').textContent=fmt(dur.social||0);
  if(el('sum-sante'))      el('sum-sante').textContent=(dur.sport||0).toFixed(1);
  if(el('sum-total'))      el('sum-total').textContent=Object.values(dur).reduce((a,b)=>a+b,0).toFixed(1);
  renderWeekDonut(dur);
}

// ─── API calls ────────────────────────────────────────────────────────────────
async function fetchApiEvents(startIso, endIso) {
  const r=await fetch(API_BASE+'/events?start='+encodeURIComponent(startIso)+'&end='+encodeURIComponent(endIso));
  if(!r.ok) throw new Error('events_api');
  const d=await r.json();
  return (d.events||[]).map((ev,i)=>({...ev,_uid:String(ev.id||ev.task_id||'api:'+i)}));
}

async function fetchBoardTasks() {
  const r=await fetch(API_BASE+'/board');
  if(!r.ok) throw new Error('board_api');
  const d=await r.json();
  return (d.tasks||[]);
}

async function apiCreateTask(payload) {
  const r=await fetch(API_BASE+'/tasks',{method:'POST',headers:apiHeaders(),body:JSON.stringify(payload)});
  if(!r.ok) throw new Error('create_failed');
  return r.json();
}

async function apiUpdateTask(taskId, payload) {
  const r=await fetch(API_BASE+'/tasks/'+taskId,{method:'PATCH',headers:apiHeaders(),body:JSON.stringify(payload)});
  if(!r.ok) throw new Error('update_failed');
  return r.json();
}

async function apiDeleteTask(taskId) {
  const r=await fetch(API_BASE+'/tasks/'+taskId,{method:'DELETE',headers:apiHeaders()});
  if(!r.ok) throw new Error('delete_failed');
  return r.json();
}

// ─── Sync Apple Calendar ──────────────────────────────────────────────────────
async function syncAll() {
  updateAppleCalStatus('syncing');
  const btn=document.getElementById('syncBtn');
  if(btn){btn.disabled=true;btn.textContent='\u29d7 Sync\u2026';}
  try {
    // 0. V\u00e9rifier permission macOS avant tout
    try {
      const sr=await fetch(API_BASE+'/calendar/status');
      if(sr.ok){
        const sd=await sr.json();
        if(sd.permission==='denied'||sd.error==='calendar_permission_denied'){
          updateAppleCalStatus('permission_denied');
          updateSyncUI(false,null,true);
          showToast('\u26a0\ufe0f Acc\u00e8s Calendriers refus\u00e9 \u2014 R\u00e8gles: Syst\u00e8me \u203a Confidentialit\u00e9 \u203a Calendriers','err');
          return;
        }
      }
    } catch(_){}
    // 1. Push local tasks \u2192 Apple Calendar (t\u00e2ches non encore synch\u00e9es)
    let pushInfo='';
    try {
      const pr=await fetch(API_BASE+'/calendar/push',{method:'POST',headers:apiHeaders(),body:'{}'});
      const pd=await pr.json();
      if(pd.result){
        const s=pd.result.synced||0; if(s>0) pushInfo=` +${s} envoy\u00e9${s>1?'s':''}`;
      }
    } catch(_){}
    // 2. Pull Apple Calendar \u2192 SQLite
    const r=await fetch(API_BASE+'/calendar/sync',{method:'POST',headers:apiHeaders(),body:'{}'});
    const d=await r.json();
    if(d.ok){
      const nowIso=new Date().toISOString();
      updateSyncUI(true,nowIso,null);
      updateAppleCalStatus('ok',nowIso);
      if(d.events) currentEvents=d.events.map((ev,i)=>({...ev,_uid:String(ev.id||'api:'+i)}));
      if(d.board)  currentBoard=d.board;
      await renderWeek(); renderBoard();
      showToast('Calendrier synchronis\u00e9'+pushInfo+'.','ok');
    } else {
      updateAppleCalStatus('error');
      showToast('Synchronisation \u00e9chou\u00e9e.','err');
    }
  } catch(e){ updateSyncUI(false,null,true); updateAppleCalStatus('error'); showToast('Impossible de synchroniser.','err'); }
  finally { if(btn){btn.disabled=false;btn.textContent='\u29d7 Synchroniser';} }
}

// ─── Local state fallback ─────────────────────────────────────────────────────
function loadState() { try{return JSON.parse(localStorage.getItem(STORAGE_KEY)||'{}');}catch(_){return{};} }

function mergedEvents() {
  const state=loadState(); const ov=state.overrides||{}; const custom=state.custom||[];
  const base=BASE_EVENTS.map((ev,i)=>{
    const uid='b:'+(ev.id||i); const o=ov[uid]||{};
    if(o.deleted) return null; return {...ev,...o,_uid:uid};
  }).filter(Boolean);
  return base.concat(custom.map(ev=>({...ev,_uid:ev._uid||'c:'+Date.now()})));
}

function setEventLocal(uid,payload) {
  const state=loadState(); state.overrides=state.overrides||{}; state.custom=state.custom||[];
  if(uid.startsWith('c:')) state.custom=state.custom.map(ev=>ev._uid===uid?{...ev,...payload}:ev);
  else state.overrides[uid]={...(state.overrides[uid]||{}),...payload};
  localStorage.setItem(STORAGE_KEY,JSON.stringify(state));
}

// ─── Event helpers ────────────────────────────────────────────────────────────
function findCurrentEvent(uid) { return currentEvents.find(e=>e._uid===uid); }

function getTaskId(ev) {
  if(ev.task_id) return ev.task_id;
  if(ev.id && String(ev.id).startsWith('task:')) return parseInt(String(ev.id).split(':')[1]);
  return null;
}

async function updateEvent(uid, payload) {
  const ev=findCurrentEvent(uid); if(!ev) return;
  if(API_ENABLED) {
    try {
      const tid=getTaskId(ev);
      if(tid) { const out=await apiUpdateTask(tid,{...payload,sync_apple:true}); if(out.events) currentEvents=out.events.map((e,i)=>({...e,_uid:String(e.id||'api:'+i)})); if(out.board) currentBoard=out.board; return; }
      if(ev.calendar_uid||(ev.id&&String(ev.id).startsWith('apple:'))) {
        const cu=ev.calendar_uid||String(ev.id).slice(6);
        await fetch(API_BASE+'/apple/'+encodeURIComponent(cu),{method:'PATCH',headers:apiHeaders(),body:JSON.stringify(payload)});
        return;
      }
    } catch(_){API_ENABLED=false;}
  }
  setEventLocal(uid,payload);
}

async function removeEvent(uid) {
  const ev=findCurrentEvent(uid); if(!ev) return;
  if(API_ENABLED) {
    try {
      const tid=getTaskId(ev);
      if(tid){
        const out=await apiDeleteTask(tid);
        if(out.events) currentEvents=out.events.map((e,i)=>({...e,_uid:String(e.id||'api:'+i)}));
        if(out.board) currentBoard=out.board;
        showToast('Tâche supprimée.','ok');
        return;
      }
      // Événement Apple Calendar (pas de task_id) — supprimer via l'API Apple
      const calUid=ev.calendar_uid||(ev.id&&String(ev.id).startsWith('apple:')?String(ev.id).slice(6):'');
      if(calUid){
        const r=await fetch(API_BASE+'/apple/'+encodeURIComponent(calUid),{method:'DELETE',headers:apiHeaders()});
        const out=await r.json();
        if(out.events) currentEvents=out.events.map((e,i)=>({...e,_uid:String(e.id||'api:'+i)}));
        showToast('Événement supprimé du calendrier.','ok');
        return;
      }
    } catch(_){API_ENABLED=false;}
  }
  setEventLocal(uid,{deleted:true});
}

// ─── Schedule / Unschedule ────────────────────────────────────────────────────
async function scheduleTaskOnDate(taskId, dateIso) {
  // Heure intelligente : si même jour → heure courante arrondie au quart ; sinon 09:00
  const today=isoDate(new Date());
  let startTime='09:00:00';
  if(dateIso===today){
    const n=new Date(); const m=Math.ceil(n.getMinutes()/15)*15;
    const h=n.getHours()+Math.floor(m/60);
    startTime=String(h%24).padStart(2,'0')+':'+String(m%60).padStart(2,'0')+':00';
  }
  const start=new Date(dateIso+'T'+startTime); const end=addMin(start,60);
  const task=currentBoard.find(t=>(t.task_id||t.id)==taskId)||{};
  const lastBucket=task.triage_status||'a_planifier';
  try {
    const calName=task.calendar_name||'Personnel';
    const out=await apiUpdateTask(taskId,{scheduled:true,scheduled_date:dateIso,scheduled_start:toIsoNoMs(start),scheduled_end:toIsoNoMs(end),start_at:toIsoNoMs(start),end_at:toIsoNoMs(end),calendar_name:calName,last_bucket_before_scheduling:lastBucket,sync_apple:true});
    if(out.events) currentEvents=out.events.map((e,i)=>({...e,_uid:String(e.id||'api:'+i)}));
    if(out.board)  currentBoard=out.board;
    showToast('Tâche planifiée.','ok');
  } catch(e){ showToast('Impossible de planifier.','err'); }
}

async function unscheduleTask(taskId, lastBucket) {
  try {
    const out=await apiUpdateTask(taskId,{scheduled:false,scheduled_date:null,scheduled_start:null,scheduled_end:null,start_at:'',end_at:'',triage_status:lastBucket||'a_planifier',sync_apple:true});
    if(out.events) currentEvents=out.events.map((e,i)=>({...e,_uid:String(e.id||'api:'+i)}));
    if(out.board)  currentBoard=out.board;
    showToast('Tâche retirée du planning.','ok');
  } catch(e){ showToast('Impossible de retirer.','err'); }
}

// ─── Board task actions ───────────────────────────────────────────────────────
async function addBoardTask() {
  const textEl=document.getElementById('taskText');
  const domEl=document.getElementById('taskDomain');
  const calEl=document.getElementById('taskCalendar');
  const title=String((textEl&&textEl.value)||'').trim();
  if(!title){showToast('Saisis un titre.','warn');return;}
  const category=(domEl&&domEl.value)||'autre';
  const calendar_name=(calEl&&calEl.value)||'Personnel';
  try {
    const out=await apiCreateTask({title,category,calendar_name,triage_status:'a_determiner',scheduled:false,sync_apple:false});
    if(out.board) currentBoard=out.board;
    else currentBoard.push({task_id:out.created?.task_id,title,category,triage_status:'a_determiner',scheduled:false});
    if(textEl) textEl.value='';
    renderBoard(); showToast('Tâche ajoutée dans À déterminer.','ok');
  } catch(e){ showToast('Impossible de créer la tâche.','err'); }
}

async function updateTaskTriage(taskId, triageStatus) {
  try {
    const out=await apiUpdateTask(taskId,{triage_status:triageStatus,scheduled:false});
    if(out.board) currentBoard=out.board;
    else currentBoard=currentBoard.map(t=>((t.task_id||t.id)==taskId)?{...t,triage_status:triageStatus}:t);
    renderBoard();
  } catch(e){ showToast('Impossible de mettre à jour.','err'); }
}

async function terminateTask(taskId) {
  try {
    const out=await apiUpdateTask(taskId,{triage_status:'termine',scheduled:false});
    if(out.board) currentBoard=out.board;
    renderBoard(); showToast('Tâche terminée ✓','ok');
  } catch(e){ showToast('Impossible de terminer.','err'); }
}

async function deleteBoardTask(taskId) {
  try {
    const out=await apiDeleteTask(taskId);
    if(out.board) currentBoard=out.board;
    else currentBoard=currentBoard.filter(t=>(t.task_id||t.id)!=taskId);
    renderBoard(); showToast('Tâche supprimée.','ok');
  } catch(e){ showToast('Impossible de supprimer.','err'); }
}

// ─── Modal planification depuis board ────────────────────────────────────────
function showPlanModal(taskId) {
  document.querySelectorAll('.plan-modal-overlay').forEach(el=>el.remove());
  const today=isoDate(new Date());
  const defStart=defaultStartTime(today);
  const defEnd=addMinToTimeStr(defStart,60);
  const ov=document.createElement('div'); ov.className='plan-modal-overlay';
  ov.innerHTML=`<div class="plan-modal">
    <h3>📅 Planifier la t\u00e2che</h3>
    <label>Date</label>
    <input type="date" id="pm-date" value="${today}" min="${today}" />
    <label>Heure d\u00e9but \u2192 fin</label>
    <div class="pm-time-row">
      <input type="time" id="pm-start" value="${defStart}" />
      <span>\u2192</span>
      <input type="time" id="pm-end" value="${defEnd}" />
    </div>
    <label>Calendrier</label>
    <select id="pm-calendar" class="pm-select">
      <option value="Personnel">📘 Personnel (iCloud)</option>
      <option value="simon.hingant@gmail.com">📧 Gmail</option>
      <option value="Calendrier">📙 Calendrier (partag\u00e9)</option>
    </select>
    <div class="pm-footer">
      <button class="pm-cancel">\u2715 Annuler</button>
      <button class="pm-ok">\u2713 Planifier</button>
    </div>
  </div>`;
  document.body.appendChild(ov);
  const pmDate=ov.querySelector('#pm-date');
  const pmStart=ov.querySelector('#pm-start');
  const pmEnd=ov.querySelector('#pm-end');
  let endTouched=false;
  pmDate.addEventListener('change',()=>{
    const v=defaultStartTime(pmDate.value); pmStart.value=v;
    if(!endTouched) pmEnd.value=addMinToTimeStr(v,60);
  });
  pmStart.addEventListener('change',()=>{ if(!endTouched) pmEnd.value=addMinToTimeStr(pmStart.value,60); });
  pmEnd.addEventListener('change',()=>{ endTouched=true; });
  ov.querySelector('.pm-cancel').addEventListener('click',()=>ov.remove());
  ov.addEventListener('click',ev=>{ if(ev.target===ov) ov.remove(); });
  ov.querySelector('.pm-ok').addEventListener('click',async()=>{
    const dt=pmDate.value;
    if(!dt||!/^\\d{4}-\\d{2}-\\d{2}$/.test(dt)){showToast('Date invalide.','warn');return;}
    if(pmStart.value>=pmEnd.value){showToast('Heure fin \u2265 d\u00e9but.','warn');return;}
    ov.remove();
    const s=new Date(dt+'T'+pmStart.value+':00');
    const e=new Date(dt+'T'+pmEnd.value+':00');
    const task=currentBoard.find(t=>(t.task_id||t.id)==taskId)||{};
    const lastBucket=task.triage_status||'a_planifier';
    try {
      const pmCal=ov.querySelector('#pm-calendar');
      const calName=(pmCal&&pmCal.value)||'Personnel';
      const out=await apiUpdateTask(taskId,{scheduled:true,scheduled_date:dt,
        scheduled_start:toIsoNoMs(s),scheduled_end:toIsoNoMs(e),
        start_at:toIsoNoMs(s),end_at:toIsoNoMs(e),
        calendar_name:calName,
        last_bucket_before_scheduling:lastBucket,sync_apple:true});
      if(out.events) currentEvents=out.events.map((ev,i)=>({...ev,_uid:String(ev.id||'api:'+i)}));
      if(out.board) currentBoard=out.board;
      await renderWeek(); renderBoard();
      showToast('T\u00e2che planifi\u00e9e.','ok');
    } catch(_){ showToast('Impossible de planifier.','err'); }
  });
  pmDate.focus();
}

async function planFromBoard(taskId) {
  showPlanModal(taskId);
}

// ─── Render board ─────────────────────────────────────────────────────────────
const TRIAGE_COLS=[
  {key:'a_determiner',label:'À déterminer',color:'#94a3b8'},
  {key:'urgent',      label:'Urgent',       color:'#ef4444'},
  {key:'a_planifier', label:'À planifier',  color:'#3b82f6'},
  {key:'non_urgent',  label:'Non urgent',   color:'#64748b'},
  {key:'termine',     label:'Terminé',      color:'#22c55e'},
];

// ─── Heure par défaut arrondie au prochain quart d'heure ──────────────────────
function defaultStartTime(dateIso) {
  const today=isoDate(new Date());
  if(dateIso===today){
    const n=new Date(); const raw=Math.ceil(n.getMinutes()/15)*15;
    const m=raw%60; const h=(n.getHours()+Math.floor(raw/60))%24;
    return String(h).padStart(2,'0')+':'+String(m).padStart(2,'0');
  }
  return '09:00';
}
function addMinToTimeStr(hhmm, mins) {
  const [h,m]=hhmm.split(':').map(Number);
  const t=h*60+m+mins; return String(Math.floor(t/60)%24).padStart(2,'0')+':'+String(t%60).padStart(2,'0');
}

// ─── Quick form inline pour ajout jour ────────────────────────────────────────
function showDayQuickForm(col, dateIso) {
  document.querySelectorAll('.day-quick-form').forEach(f=>f.remove());
  const defStart=defaultStartTime(dateIso);
  const defEnd=addMinToTimeStr(defStart,60);
  const form=document.createElement('div'); form.className='day-quick-form';
  form.innerHTML=
    `<input class="day-quick-input" type="text" placeholder="Titre de la t\u00e2che\u2026" />`
    +`<select class="day-quick-select">`
    +`<option value="sport">🏃 Sport</option>`
    +`<option value="travail">💼 Travail</option>`
    +`<option value="yoga">🧘 Yoga</option>`
    +`<option value="lecon">🎓 Leçon</option>`
    +`<option value="formation">📚 Formation</option>`
    +`<option value="social">💬 Social</option>`
    +`<option value="autre">🧩 Autre</option>`
    +`</select>`
    +`<select class="day-quick-select day-quick-cal">`
    +`<option value="Personnel">📘 Personnel</option>`
    +`<option value="simon.hingant@gmail.com">📧 Gmail</option>`
    +`<option value="Calendrier">📙 Calendrier</option>`
    +`</select>`
    +`<div class="day-quick-time-row">`
    +`<input class="day-quick-input" type="time" id="dqt-start" value="${defStart}" title="Heure d\u00e9but" />`
    +`<span class="dqt-sep">\u2192</span>`
    +`<input class="day-quick-input" type="time" id="dqt-end" value="${defEnd}" title="Heure fin" />`
    +`</div>`
    +`<div class="day-quick-actions">`
    +`<button class="day-quick-submit">\u2713 Ajouter</button>`
    +`<button class="day-quick-cancel">\u2715</button>`
    +`</div>`;
  const firstEvent=col.querySelector('.event');
  if(firstEvent) col.insertBefore(form,firstEvent); else col.appendChild(form);
  const inp=form.querySelector('input[type=text]');
  const tStart=form.querySelector('#dqt-start');
  const tEnd=form.querySelector('#dqt-end');
  inp.focus();
  // Auto-recalcule fin quand début change (si fin pas manuellement modifiée)
  let endTouched=false;
  tStart.addEventListener('change',()=>{
    if(!endTouched) tEnd.value=addMinToTimeStr(tStart.value,60);
  });
  tEnd.addEventListener('change',()=>{ endTouched=true; });
  async function submit(){
    const title=inp.value.trim(); if(!title){inp.focus();return;}
    const domain=form.querySelector('.day-quick-select:not(.day-quick-cal)').value;
    const calSel=form.querySelector('.day-quick-cal');
    const calName=(calSel&&calSel.value)||'Personnel';
    if(tStart.value>=tEnd.value){showToast('Heure fin \u2265 heure d\u00e9but.','warn');return;}
    const s2=new Date(dateIso+'T'+tStart.value+':00');
    const e2=new Date(dateIso+'T'+tEnd.value+':00');
    form.remove();
    try{
      const out=await apiCreateTask({title,category:domain,calendar_name:calName,triage_status:'a_planifier',scheduled:true,
        scheduled_date:dateIso,scheduled_start:toIsoNoMs(s2),scheduled_end:toIsoNoMs(e2),
        start_at:toIsoNoMs(s2),end_at:toIsoNoMs(e2),sync_apple:true});
      if(out.board) currentBoard=out.board;
      showToast('T\u00e2che ajout\u00e9e \u2014 '+dateIso,'ok'); await renderWeek();
    }catch(_){showToast('Impossible de cr\u00e9er.','err');}
  }
  form.querySelector('.day-quick-submit').addEventListener('click',submit);
  form.querySelector('.day-quick-cancel').addEventListener('click',()=>form.remove());
  inp.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();submit();}if(ev.key==='Escape')form.remove();});
}

function renderBoard() {
  const grid=document.getElementById('boardGrid'); if(!grid) return;
  const buckets={}; TRIAGE_COLS.forEach(c=>{buckets[c.key]=[];});
  (currentBoard||[]).forEach(t=>{const ts=t.triage_status||'a_determiner';if(buckets[ts])buckets[ts].push(t);});

  grid.innerHTML=TRIAGE_COLS.map(col=>{
    const items=buckets[col.key]||[];
    const cardsHtml=items.length===0
      ?'<div class="board-col-empty">—</div>'
      :items.map(t=>{
          const tid=t.task_id||t.id||'';
          const cat=t.category||'autre'; const color=domainColor(cat); const icon=domainIcon(cat);
          const isDone=col.key==='termine';
          return `<div class="board-card" draggable="true" data-task-id="${escapeHtml(String(tid))}" data-triage="${col.key}" style="border-left-color:${color};">
            <div class="bc-title">${escapeHtml(t.title||'Tâche')}</div>
            <div class="bc-domain" style="color:${color}">${icon} ${escapeHtml(CATEGORY_LABELS[cat]||cat)}</div>
            <div class="bc-actions">
              ${!isDone?`<button class="bc-btn" onclick="planFromBoard(${tid})">📅 Planifier</button>`:''}
              ${!isDone?`<button class="bc-btn" onclick="terminateTask(${tid})">✓</button>`:''}
              <button class="bc-btn danger" onclick="deleteBoardTask(${tid})">✕</button>
            </div>
          </div>`;
        }).join('');
    return `<div class="board-col" data-triage="${col.key}"
      ondragover="event.preventDefault();this.classList.add('drop-target')"
      ondragleave="this.classList.remove('drop-target')"
      ondrop="handleBoardDrop(event,'${col.key}')">
      <div class="board-col-header">
        <span class="board-col-title" style="color:${col.color}">${col.label}</span>
        <span class="board-col-count">${items.length}</span>
      </div>
      <div class="board-lane" data-triage="${col.key}">${cardsHtml}</div>
    </div>`;
  }).join('');

  // Bind drag events
  grid.querySelectorAll('.board-card[data-task-id]').forEach(card=>{
    card.addEventListener('dragstart',ev=>{
      card.classList.add('dragging');
      ev.dataTransfer.setData('application/x-board-task',card.dataset.taskId);
      ev.dataTransfer.setData('text/plain','board:'+card.dataset.taskId);
      ev.dataTransfer.effectAllowed='move';
    });
    card.addEventListener('dragend',()=>card.classList.remove('dragging'));
  });

  // Sortable between columns
  if(typeof Sortable!=='undefined'){
    grid.querySelectorAll('.board-lane').forEach(lane=>{
      if(lane.dataset.sortableBound==='1') return;
      Sortable.create(lane,{
        group:'performos-board', animation:160, draggable:'.board-card', ghostClass:'dragging',
        onEnd:evt=>{const tid=evt.item&&evt.item.dataset.taskId; const to=evt.to&&evt.to.dataset.triage; if(tid&&to) updateTaskTriage(tid,to);}
      });
      lane.dataset.sortableBound='1';
    });
  }
}

function handleBoardDrop(ev, targetTriage) {
  ev.preventDefault();
  document.querySelectorAll('.board-col').forEach(c=>c.classList.remove('drop-target'));
  const tid=ev.dataTransfer.getData('application/x-board-task');
  if(tid&&targetTriage) updateTaskTriage(tid,targetTriage);
}

// ─── Trend charts ─────────────────────────────────────────────────────────────
async function computeAndRenderTrendCharts(currentWeekEvents) {
  const MS_WEEK=7*24*60*60*1000; const today=new Date();
  const dow=today.getDay()===0?6:today.getDay()-1;
  const thisMonday=new Date(today.getTime()-dow*24*60*60*1000); thisMonday.setHours(0,0,0,0);
  const weeks=[];
  for(let w=3;w>=0;w--){
    const wStart=new Date(thisMonday.getTime()-w*MS_WEEK); const wEnd=new Date(wStart.getTime()+MS_WEEK);
    const label=w===0?'Cette sem.':'S-'+w;
    if(w===0){
      weeks.push({label,work:sumHoursForCat(currentWeekEvents,'travail'),social:sumHoursForCat(currentWeekEvents,'social')});
    } else {
      try{const wEvts=await fetchApiEvents(toIsoNoMs(wStart),toIsoNoMs(wEnd)); weeks.push({label,work:sumHoursForCat(wEvts,'travail'),social:sumHoursForCat(wEvts,'social')});}
      catch(_){weeks.push({label,work:0,social:0});}
    }
  }
  renderWorkTrendChart(weeks); renderSocialTrendChart(weeks);
}

function sumHoursForCat(evts,cat) {
  return evts.reduce((acc,ev)=>{const c=normCat(ev.category||''); if(c===cat) acc+=(eventDurationMin(ev)||0)/60; return acc;},0);
}

function renderWorkTrendChart(wd) {
  const cv=document.getElementById('workTrendChart'); if(!cv||typeof Chart==='undefined') return;
  if(_workChart){_workChart.destroy();_workChart=null;}
  _workChart=new Chart(cv,{type:'line',data:{labels:wd.map(w=>w.label),datasets:[{data:wd.map(w=>+(w.work||0).toFixed(1)),borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,.12)',borderWidth:2,pointRadius:3,fill:true,tension:0.35}]},options:{responsive:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#64748b',font:{size:10}},grid:{color:'rgba(255,255,255,.05)'}},y:{ticks:{color:'#64748b',font:{size:10}},grid:{color:'rgba(255,255,255,.05)'},beginAtZero:true}}}});
}

function renderSocialTrendChart(wd) {
  const cv=document.getElementById('socialTrendChart'); if(!cv||typeof Chart==='undefined') return;
  if(_socialChart){_socialChart.destroy();_socialChart=null;}
  _socialChart=new Chart(cv,{type:'line',data:{labels:wd.map(w=>w.label),datasets:[{data:wd.map(w=>+(w.social||0).toFixed(1)),borderColor:'#ec4899',backgroundColor:'rgba(236,72,153,.12)',borderWidth:2,pointRadius:3,fill:true,tension:0.35}]},options:{responsive:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#64748b',font:{size:10}},grid:{color:'rgba(255,255,255,.05)'}},y:{ticks:{color:'#64748b',font:{size:10}},grid:{color:'rgba(255,255,255,.05)'},beginAtZero:true}}}});
}

// ─── Calendar week ────────────────────────────────────────────────────────────
async function renderWeek() {
  const baseStart=startOfWeek(parseIso(WEEK_START_ISO)||new Date());
  const start=addDays(baseStart,weekOffset*7); const end=addDays(start,7);
  const days=['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];
  const lbl=document.getElementById('weekLabel');
  if(lbl) lbl.textContent=shortDateFr(start)+' – '+shortDateFr(addDays(end,-1));

  let allEvents=[];
  if(API_ENABLED){
    try { allEvents=await fetchApiEvents(isoDate(start)+'T00:00:00',isoDate(addDays(end,1))+'T00:00:00'); }
    catch(_){ API_ENABLED=false; allEvents=mergedEvents(); }
  } else { allEvents=mergedEvents(); }

  const events=allEvents.filter(ev=>{const s=parseIso(ev.start_at); return s&&s>=start&&s<end;});
  currentEvents=events.slice();

  const dur=categoryDurations(events); updateMiniIndicators(dur);

  // Travail section
  const wfl=document.getElementById('workFocusHrs'); if(wfl) wfl.textContent=(dur.travail||0).toFixed(1)+'h';
  const wtl=document.getElementById('workTasksList');
  if(wtl){
    const we=events.filter(ev=>normCat(ev.category||'')==='travail').sort((a,b)=>parseIso(a.start_at)-parseIso(b.start_at));
    wtl.innerHTML=we.length===0?'<div class="muted" style="font-size:12px">Aucune tâche travail.</div>':we.slice(0,8).map(ev=>{const s=parseIso(ev.start_at);return '<div class="event" style="border-left-color:#3b82f6"><div class="event-title">💼 '+escapeHtml(ev.title||'Travail')+'</div><div class="event-meta"><span>'+(s?hm(s):'—')+'</span></div></div>';}).join('');
  }

  // Social section
  const now=new Date();
  const su=document.getElementById('socialUpcoming'); if(su) su.textContent=events.filter(ev=>{const s=parseIso(ev.start_at);return s&&s>=now&&normCat(ev.category||'')==='social';}).length;
  const sel=document.getElementById('socialEventsList');
  if(sel){
    const re=events.filter(ev=>normCat(ev.category||'')==='social').sort((a,b)=>parseIso(a.start_at)-parseIso(b.start_at));
    sel.innerHTML=re.length===0?'<div class="muted" style="font-size:12px">Aucun événement social.</div>':re.slice(0,8).map(ev=>{const s=parseIso(ev.start_at);return '<div class="event" style="border-left-color:#ec4899"><div class="event-title">💬 '+escapeHtml(ev.title||'Social')+'</div><div class="event-meta"><span>'+(s?hm(s):'—')+'</span></div></div>';}).join('');
  }

  computeAndRenderTrendCharts(events);

  const grid=document.getElementById('weekGrid'); if(!grid) return; grid.innerHTML='';
  for(let i=0;i<7;i++){
    const d=addDays(start,i); const dateIso=isoDate(d); const isToday=dateIso===isoDate(new Date());
    const col=document.createElement('div'); col.className='day-col'+(isToday?' today':''); col.dataset.date=dateIso;
    const head=document.createElement('div'); head.className='day-head';
    head.innerHTML='<span>'+days[i]+' '+shortDateFr(d)+(isToday?' <span class="today-badge">Auj.</span>':'')+'</span>'
      +'<button class="day-add" data-date="'+dateIso+'" title="Ajouter ici">+</button>';
    col.appendChild(head);

    // Drop zone pour tâches du board
    col.addEventListener('dragover',ev=>{ev.preventDefault();col.classList.add('drop-target');});
    col.addEventListener('dragleave',()=>col.classList.remove('drop-target'));
    col.addEventListener('drop',async ev=>{
      ev.preventDefault(); col.classList.remove('drop-target');
      const boardTaskId=ev.dataTransfer.getData('application/x-board-task');
      if(boardTaskId){await scheduleTaskOnDate(boardTaskId,dateIso);await renderWeek();renderBoard();return;}
      const uid=ev.dataTransfer.getData('text/plain');
      if(uid&&!uid.startsWith('board:')){await moveEventToDate(uid,dateIso);await renderWeek();}
    });

    const dayEvents=events.filter(ev=>{const s=parseIso(ev.start_at);return s&&isoDate(s)===dateIso;}).sort((a,b)=>parseIso(a.start_at)-parseIso(b.start_at));
    if(!dayEvents.length){const emp=document.createElement('div');emp.className='muted';emp.style.fontSize='12px';emp.textContent='—';col.appendChild(emp);}

    dayEvents.forEach(ev=>{
      const cat=normCat(ev.category||'autre'); const color=domainColor(cat); const icon=domainIcon(cat);
      const s=parseIso(ev.start_at); const e=parseIso(ev.end_at);
      const dur2=Math.max(5,Math.round(((e||s)-(s||e))/60000));
      // Hauteur proportionnelle : 30min=base(38px), 1h=60px, 2h=104px, etc.
      const PX_PER_MIN=1.1; const MIN_H=38;
      const propH=Math.max(MIN_H, Math.round(dur2*PX_PER_MIN));
      const card=document.createElement('div'); card.className='event'; card.draggable=true; card.style.borderLeftColor=color;
      card.style.minHeight=propH+'px';
      card.style.height=propH+'px';
      // Formater la durée lisiblement
      const durLabel=dur2>=60?(Math.floor(dur2/60)+'h'+(dur2%60?String(dur2%60).padStart(2,'0'):'')):(dur2+'min');
      card.innerHTML='<div class="event-title">'+icon+' '+escapeHtml(ev.title||'Événement')+'</div>'
        +'<div class="event-meta"><span>'+(s?hm(s):'—')+(e?' \u2192 '+hm(e):'')+' · '+durLabel+'</span>'
        +'<button class="event-x" title="Retirer du planning">\u2190</button>'
        +'<button class="event-del" title="Supprimer">\u2715</button></div>';
      card.addEventListener('dragstart',evd=>{card.classList.add('dragging');evd.dataTransfer.setData('text/plain',ev._uid);});
      card.addEventListener('dragend',()=>card.classList.remove('dragging'));
      card.querySelector('.event-x').addEventListener('click',async evx=>{
        evx.stopPropagation();
        const tid=getTaskId(ev);
        if(!tid){showToast('Cet événement Apple ne peut pas être retiré du planning.','warn');return;}
        await unscheduleTask(tid,ev.last_bucket_before_scheduling);
        await renderWeek(); renderBoard();
      });
      card.querySelector('.event-del').addEventListener('click',async evd=>{
        evd.stopPropagation();
        await removeEvent(ev._uid); await renderWeek(); renderBoard();
      });
      col.appendChild(card);
    });
    grid.appendChild(col);
  }

  // Bouton "+" sur chaque jour
  grid.querySelectorAll('.day-add').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const dayCol=btn.closest('.day-col');
      if(dayCol) showDayQuickForm(dayCol, btn.dataset.date);
    });
  });
}

async function moveEventToDate(uid, newDateIso) {
  const ev=findCurrentEvent(uid); if(!ev) return;
  const s=parseIso(ev.start_at); const e=parseIso(ev.end_at); if(!s||!e) return;
  const dur=e-s; const ms=new Date(newDateIso+'T'+hm(s)+':00'); const me=new Date(ms.getTime()+dur);
  await updateEvent(uid,{start_at:toIsoNoMs(ms),end_at:toIsoNoMs(me),scheduled_start:toIsoNoMs(ms),scheduled_end:toIsoNoMs(me),scheduled_date:newDateIso});
}

// ─── Debug panel ──────────────────────────────────────────────────────────────
function toggleDebugPanel() {
  const panel=document.getElementById('debugPanel'); if(!panel) return;
  panel.classList.toggle('open');
  const da=document.getElementById('dbgApi'); if(da) da.textContent=API_ENABLED?API_BASE:'local storage';
  const de=document.getElementById('dbgEvents'); if(de) de.textContent=currentEvents.length;
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────
function activateTab(tabId) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  const te=document.querySelector('.tab[data-tab="'+tabId+'"]'); if(te) te.classList.add('active');
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  const se=document.getElementById('sec-'+tabId); if(se) se.classList.add('active');
  window.scrollTo(0,0);
}

// ─── Rings animation ──────────────────────────────────────────────────────────
function initRings() {
  document.querySelectorAll('.ic-fill').forEach(el=>{
    const target=el.style.width||'0%'; el.style.transition='none'; el.style.width='0%';
    void el.getBoundingClientRect();
    requestAnimationFrame(()=>requestAnimationFrame(()=>{el.style.transition='width .8s cubic-bezier(0.4,0,0.2,1)';el.style.width=target;}));
  });
}

// ─── Init ─────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>activateTab(t.dataset.tab)));
  const prev=document.getElementById('prevWeek'); if(prev) prev.addEventListener('click',()=>{weekOffset-=1;renderWeek();});
  const next=document.getElementById('nextWeek'); if(next) next.addEventListener('click',()=>{weekOffset+=1;renderWeek();});
  const dbg=document.getElementById('debugPanelBtn'); if(dbg) dbg.addEventListener('click',toggleDebugPanel);
  const addBtn=document.getElementById('addTaskBtn'); if(addBtn) addBtn.addEventListener('click',addBoardTask);
  const taskInput=document.getElementById('taskText');
  if(taskInput) taskInput.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();addBoardTask();}});

  updateSyncUI(CAL_SYNC_ENABLED,null,false);

  (async()=>{
    const boardGrid = document.getElementById('boardGrid');
    if (boardGrid) boardGrid.innerHTML = '<div style="padding:20px;color:var(--muted);font-size:12px;text-align:center">Chargement\u2026</div>';
    try{ if(API_ENABLED) currentBoard=await fetchBoardTasks(); } catch(_){}
    renderBoard();
    await renderWeek();
    initRings(); initMascot();
    // Auto-sync calendrier au chargement
    if(CAL_SYNC_ENABLED && API_ENABLED) {
      try { await syncAll(); } catch(_){}
    } else if(CAL_SYNC_ENABLED) {
      checkCalendarPermission();
    }
  })();
});
</script>
</body>
</html>
"""

    repl = {
        "__TODAY__": today,
        "__NOW__": now,
        "__CAL_BADGE_CLASS__": "ok" if cal_enabled else "warn",
        "__CAL_SYNC_ENABLED__": "true" if cal_enabled else "false",
        "__READINESS_GLOBAL_NUM__": f"{readiness_global:.1f}",
        "__WBS__": f"{wbs:.0f}",
        "__WBS_LABEL__": str(wbs_label),
        "__READINESS_GLOBAL__": f"{readiness_global:.0f}",
        "__ACWR__": f"{acwr_val:.2f}",
        "__ACWR_ZONE__": str(acwr_zone),
        "__WEEK_START__": str(week_start),
        "__SUM_SANTE__": f"{sante_h:.1f}",
        "__SUM_TRAVAIL__": f"{travail_h:.1f}",
        "__SUM_REL__": f"{relationnel_h:.1f}",
        "__SUM_APP__": f"{apprentissage_h:.1f}",
        "__SUM_AUTRE__": f"{autre_h:.1f}",
        "__SUM_TOTAL__": f"{total_h:.1f}",
        "__GOAL_DONE__": f"{goal_done:.1f}",
        "__GOAL_TARGET__": f"{goal_h:.1f}",
        "__GOAL_TARGET_NUM__": f"{goal_h:.1f}",
        "__GOAL_LEFT__": f"{goal_left:.1f}",
        "__GOAL_PCT__": f"{goal_pct:.1f}",
        "__GOAL_PCT_DISPLAY__": f"{goal_pct:.0f}",
        "__HRV_TREND_CLASS__": "up" if hrv_delta > 2 else ("down" if hrv_delta < -2 else "flat"),
        "__RECENT_HTML__": recent_html,
        "__HRV__": f"{hrv:.0f}",
        "__RHR__": f"{rhr:.0f}" if rhr else "—",
        "__HRV_DAYS__": str(hrv_days_old if hrv_days_old is not None else "—"),
        "__RHR_DAYS__": str(rhr_days_old if rhr_days_old is not None else "—"),
        "__SLEEP_DAYS__": str(sleep_days_old if sleep_days_old is not None else "—"),
        "__SLEEP_H__": f"{sleep_h:.1f}",
        "__VO2MAX__": f"{vo2max:.1f}" if vo2max else "-",
        "__STEPS__": f"{steps:,.0f}",
        "__BODY_BATTERY__": f"{body_battery:.0f}",
        "__FRESHNESS__": f"{freshness_score:.0f}/100",
        "__FRESHNESS_LABEL__": freshness_label,
        "__PRED_10K__": str(pred_10k),
        "__RECO_HTML__": reco_html,
        "__LOAD_SPLIT_HTML__": load_split_html,
        "__MUSCLE_BARS_HTML__": muscle_bars_html,
        "__ZONE_PECS__": f"{zone_alpha.get('Pecs', 0.2):.2f}",
        "__ZONE_DOS__": f"{zone_alpha.get('Dos', 0.2):.2f}",
        "__ZONE_EPAULES__": f"{zone_alpha.get('Épaules', 0.2):.2f}",
        "__ZONE_BICEPS__": f"{zone_alpha.get('Biceps', 0.2):.2f}",
        "__ZONE_TRICEPS__": f"{zone_alpha.get('Triceps', 0.2):.2f}",
        "__ZONE_CORE__": f"{zone_alpha.get('Core', 0.2):.2f}",
        "__ZONE_JAMBES__": f"{zone_alpha.get('Jambes', 0.2):.2f}",
        "__SPORT_MIX_HTML__": sport_mix_html,
        "__TYPE_DEFS__": json.dumps(TYPE_DEFS, ensure_ascii=False),
        "__CATEGORY_LABELS__": json.dumps(CATEGORY_LABELS, ensure_ascii=False),
        "__PLANNER_EVENTS__": planner_events_json,
        "__HOURS_LABELS__": json.dumps(train_labels, ensure_ascii=False),
        "__HOURS_VALUES__": json.dumps(train_values, ensure_ascii=False),
        "__RUN_LABELS__": json.dumps(run_labels, ensure_ascii=False),
        "__RUN_VALUES__": json.dumps(run_values, ensure_ascii=False),
        "__TENK_LABELS__": json.dumps(tenk_labels, ensure_ascii=False),
        "__TENK_VALUES__": json.dumps(tenk_values, ensure_ascii=False),
        "__VO2_LABELS__": json.dumps(vo2_labels, ensure_ascii=False),
        "__VO2_VALUES__": json.dumps(vo2_values, ensure_ascii=False),
        # Laisser le placeholder pour injection dynamique par cockpit_server.py
        # Si api_token est fourni, l'injecter directement (mode fichier statique)
        # Sinon, garder le placeholder pour le serveur
        "__API_TOKEN_JS__": "__API_TOKEN_JS__"
        if not api_token
        else json.dumps(api_token, ensure_ascii=False),
        "__TSB__": f"{tsb:+.1f}",
        "__CTL__": f"{ctl:.1f}",
        "__ATL__": f"{atl:.1f}",
        "__RHR_BASELINE__": f"{rhr_baseline:.0f}" if rhr_baseline else "—",
        "__RHR_DELTA__": rhr_delta_str,
        "__RHR_DELTA_CLASS__": rhr_delta_class,
        "__HRV_DELTA__": f"{hrv_delta:+.0f}",
        "__HRV_TREND_ARROW__": hrv_trend_arrow,
        "__HRV_TREND_COLOR__": hrv_trend_color,
        "__RING_RECOVERY__": f"{ring_recovery:.0f}",
        "__RING_ACTIVITY__": f"{ring_activity:.0f}",
        "__RING_SLEEP__": f"{ring_sleep:.0f}",
        "__RING_RECOVERY_COLOR__": _ring_color(ring_recovery),
        "__RING_ACTIVITY_COLOR__": _ring_color(ring_activity),
        "__RING_SLEEP_COLOR__": _ring_color(ring_sleep),
        "__RING_RECOVERY_OFFSET__": _ring_offset(ring_recovery),
        "__RING_ACTIVITY_OFFSET__": _ring_offset(ring_activity),
        "__RING_SLEEP_OFFSET__": _ring_offset(ring_sleep),
        "__SYNC_BADGE_LABEL__": sync_badge_label,
        "__SYNC_BADGE_CLASS__": sync_badge_class,
        "__WORK_WEEK_H__": f"{travail_h:.1f}",
        "__WORK_WEEK_PCT__": f"{work_week_pct:.1f}",
        "__SOCIAL_WEEK_H__": f"{relationnel_h:.1f}",
        "__SOCIAL_WEEK_PCT__": f"{social_week_pct:.1f}",
        "__TSB_COLOR__": tsb_color,
        "__TSB_CLASS__": tsb_class,
        "__ACWR_COLOR__": acwr_color,
        "__ACWR_CLASS__": acwr_class,
        "__ACWR_ALERT_DISPLAY__": acwr_alert_display,
    }

    for key, value in repl.items():
        html = html.replace(key, value)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    kb = output_path.stat().st_size // 1024
    print(f"  ✅ Dashboard : {output_path} ({kb}KB)")
