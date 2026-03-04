"""
generator.py — PerformOS cockpit (v4)
UI centered on weekly planning + health progression.
"""
from __future__ import annotations

from pathlib import Path
from datetime import date, datetime, timedelta
import json
from html import escape


TYPE_DEFS = {
    "cardio": {"label": "Cardio", "category": "sante", "color": "#2da44e", "icon": "🏃"},
    "musculation": {"label": "Musculation", "category": "sante", "color": "#f97316", "icon": "🏋️"},
    "mobilite": {"label": "Mobilité", "category": "sante", "color": "#8b5cf6", "icon": "🧘"},
    "sport_libre": {"label": "Sport libre", "category": "sante", "color": "#14b8a6", "icon": "🎾"},
    "travail": {"label": "Travail", "category": "travail", "color": "#3b82f6", "icon": "💼"},
    "apprentissage": {"label": "Apprentissage", "category": "apprentissage", "color": "#eab308", "icon": "📚"},
    "relationnel": {"label": "Relationnel", "category": "relationnel", "color": "#ec4899", "icon": "💬"},
    "autre": {"label": "Autre", "category": "autre", "color": "#9ca3af", "icon": "🧩"},
}

CATEGORY_LABELS = {
    "sante": "Santé",
    "travail": "Travail",
    "relationnel": "Relationnel",
    "apprentissage": "Apprentissage",
    "autre": "Autre",
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
    if any(k in title for k in ["yoga", "mobil", "stretch", "souplesse"]):
        return "mobilite"
    if any(k in title for k in ["run", "course", "jog", "10km", "cardio"]):
        return "cardio"
    if any(k in title for k in ["tennis", "golf", "swim", "natation", "vélo", "velo", "sport"]):
        return "sport_libre"

    if cat == "travail":
        return "travail"
    if cat == "apprentissage":
        return "apprentissage"
    if cat == "relationnel":
        return "relationnel"
    if cat == "sante":
        return "cardio"
    return "autre"


def _prepare_pilot_events(pilot_events: list[dict]) -> list[dict]:
    rows = []
    for e in pilot_events:
        t = _infer_event_type(e)
        d = TYPE_DEFS.get(t, TYPE_DEFS["autre"])
        rows.append({
            "id": str(e.get("id") or ""),
            "title": e.get("title") or "Événement",
            "start_at": e.get("start_at"),
            "end_at": e.get("end_at"),
            "source": e.get("source") or "local",
            "calendar_name": e.get("calendar_name") or "",
            "category": d["category"],
            "type": t,
            "icon": d["icon"],
            "color": d["color"],
        })
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
) -> None:
    del daily_load_rows  # kept for signature compatibility

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
    pred_10k = (running.get("estimated_10k") or {}).get("label") or running.get("predictions", {}).get("10km", "-")

    hrv = float(health.get("hrv") or _latest_metric(metrics_history, "hrv_sdnn", 0))
    sleep_h = float(health.get("sleep_h") or _latest_metric(metrics_history, "sleep_h", 0))
    vo2max = float(health.get("vo2max") or _latest_metric(metrics_history, "vo2max", 0))
    steps = float(_latest_metric(metrics_history, "steps", 0))
    body_battery = float(health.get("body_battery") or _latest_metric(metrics_history, "body_battery", 0))
    rhr = float(health.get("rhr") or 0)
    hrv_days_old = health.get("hrv_days_old")
    sleep_days_old = health.get("sleep_days_old")
    rhr_days_old = health.get("rhr_days_old")
    freshness_vals = [
        float(health.get("hrv_freshness", 0) or 0),
        float(health.get("sleep_freshness", 0) or 0),
        float(health.get("rhr_freshness", 0) or 0),
    ]
    freshness_score = round((sum(freshness_vals) / len(freshness_vals)) * 100.0, 1) if freshness_vals else 0.0
    freshness_label = "Excellente" if freshness_score >= 80 else "Moyenne" if freshness_score >= 55 else "Faible"
    vo2_for_score = float(vo2max or 0)
    vo2_norm = min(100.0, max(0.0, (vo2_for_score - 25.0) * 2.5)) if vo2_for_score else 0.0
    readiness_global = round(max(0.0, min(100.0, (wbs * 0.5) + (body_battery * 0.3) + (vo2_norm * 0.2))), 1)

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
    train_labels, train_values = _series_labels_values(progress.get("training_hours_weekly", []), limit=260)
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
            '<div class="mix-row">'
            f'<span>{t}</span><span>{h:.1f}h ({pct:.0f}%)</span>'
            "</div>"
        )
    if not sport_mix_html:
        sport_mix_html = '<div class="muted">Pas assez de données sport.</div>'

    recent_html = ""
    for act in recent_activities:
        at_raw = str(act.get("type") or "Activité")
        at = escape(at_raw)
        icon = ICONS_BY_ACTIVITY.get(at_raw, "🏃")
        dt = escape(((act.get("started_at") or "")[:16].replace("T", " ")))
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

    cal_enabled = bool(calendar_sync.get("enabled"))
    cal_status = "Connecté" if cal_enabled else f"Indispo ({calendar_sync.get('error', 'n/a')})"
    pending_sync = int(calendar_sync.get("pending_tasks", 0) or 0)
    pending_sync_label = (
        f"{pending_sync} tâche(s) locale(s) à pousser vers Apple Calendar"
        if pending_sync > 0 else
        "Aucune tâche locale en attente de synchronisation"
    )

    # Recommendations
    recommendations = []
    if acwr_val > 1.4:
        recommendations.append("Charge élevée: allège 2-3 jours (récup active, mobilité).")
    elif acwr_val < 0.8:
        recommendations.append("Charge basse: remonte progressivement le volume (+10% max/semaine).")
    else:
        recommendations.append("Charge équilibrée: maintiens le rythme actuel.")

    if wbs < 55:
        recommendations.append("Readiness basse: priorise sommeil, hydratation, intensité modérée.")
    elif wbs > 75:
        recommendations.append("Readiness haute: fenêtre favorable pour une séance qualitative.")

    imbalances = muscles.get("imbalances", [])
    weak = [im.get("muscle") for im in imbalances if (im.get("status") or im.get("level")) in ("faible", "critique")]
    weak = sorted({w for w in weak if w})
    if weak:
        recommendations.append("Priorité renforcement cette semaine: " + ", ".join(weak) + ".")
    if freshness_score < 55:
        recommendations.append("Données santé peu fraîches: relance une sync Garmin/Apple pour fiabiliser les décisions.")
    if pending_sync > 0:
        recommendations.append(f"Synchronisation Apple incomplète: {pending_sync} tâche(s) à pousser depuis le cockpit.")
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
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {
  --bg: #f6f7fb;
  --card: #ffffff;
  --text: #1f2937;
  --muted: #6b7280;
  --line: #e5e7eb;
  --accent: #111827;
  --shadow: 0 8px 30px rgba(17,24,39,.06);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background:
    radial-gradient(circle at 0% -20%, #e9f0ff 0, transparent 35%),
    radial-gradient(circle at 100% 0%, #fff2e6 0, transparent 28%),
    var(--bg);
  font-family: Inter, -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
  color: var(--text);
}
.app {
  max-width: 1320px;
  margin: 0 auto;
  padding: 18px 16px 100px;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.brand h1 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.02em;
}
.brand p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.badges { display: flex; gap: 8px; flex-wrap: wrap; }
.badge {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--muted);
}
.badge.ok { color: #15803d; border-color: #bbf7d0; background: #f0fdf4; }
.badge.warn { color: #92400e; border-color: #fde68a; background: #fffbeb; }
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.tab {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  color: #334155;
}
.tab.active {
  background: #111827;
  border-color: #111827;
  color: #fff;
}
.section { display: none; }
.section.active { display: block; }
.grid-planning {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(340px, 1fr);
  gap: 12px;
  align-items: start;
}
.stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stack-sticky {
  position: sticky;
  top: 12px;
}
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow);
  padding: 14px;
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
  background: #fff;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 12px;
  cursor: pointer;
}
.week-label { font-size: 13px; color: var(--muted); font-weight: 600; }
.week-wrap { overflow-x: auto; }
.week-grid {
  min-width: 1150px;
  display: grid;
  grid-template-columns: repeat(7, minmax(170px, 1fr));
  gap: 8px;
}
.day-col {
  background: #fcfcfe;
  border: 1px solid var(--line);
  border-radius: 12px;
  min-height: 280px;
  padding: 8px;
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
  background: #eef2ff;
  color: #4f46e5;
  border-radius: 6px;
  font-size: 11px;
  padding: 2px 6px;
  cursor: pointer;
}
.event {
  border-left: 4px solid #9ca3af;
  background: #fff;
  border: 1px solid #edf0f5;
  border-left-width: 4px;
  border-radius: 10px;
  padding: 7px;
  margin-bottom: 6px;
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
.event-x {
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  font-size: 12px;
}
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.stat {
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #eef2f7;
  padding: 10px;
}
.stat .v { font-size: 22px; font-weight: 700; }
.stat .l { font-size: 12px; color: var(--muted); margin-top: 2px; }
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
  border-radius: 12px;
  background: #fafcff;
}
.sync-box {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
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
  border-radius: 12px;
  padding: 10px;
  background: #fff;
}
.quick-row {
  display: grid;
  grid-template-columns: 1fr 130px;
  gap: 8px;
  margin-bottom: 8px;
}
.quick-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 92px;
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
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  margin-bottom: 10px;
}
.decision-col {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #f8fafc;
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
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e8eef5;
  padding: 6px;
  margin-bottom: 6px;
  line-height: 1.35;
}
.idea-list {
  max-height: 260px;
  overflow: auto;
  border-top: 1px solid #eef2f7;
  padding-top: 8px;
}
.idea-item {
  border: 1px solid #e9eef4;
  border-radius: 10px;
  background: #fff;
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
  border: 1px solid #dbe5ef;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  color: #475569;
  background: #f8fafc;
}
.idea-actions {
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.btn-mini {
  border: 1px solid #dbe5ef;
  border-radius: 8px;
  background: #fff;
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
  height: 12px;
  border-radius: 999px;
  background: #e5e7eb;
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
  border-radius: 12px;
  background: #fff;
  padding: 12px;
}
.kpi .v { font-size: 26px; font-weight: 700; }
.kpi .l { font-size: 12px; color: var(--muted); margin-top: 3px; }
.reco-item {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
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
.progress-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.range-switch {
  display: inline-flex;
  gap: 4px;
  margin-bottom: 10px;
}
.range-btn {
  border: 1px solid var(--line);
  background: #fff;
  color: #334155;
  border-radius: 8px;
  padding: 6px 9px;
  font-size: 11px;
  cursor: pointer;
}
.range-btn.active {
  background: #111827;
  border-color: #111827;
  color: #fff;
}
.chart-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  padding: 12px;
}
.chart-title {
  font-size: 13px;
  color: #334155;
  margin-bottom: 8px;
  font-weight: 600;
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
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.form-grid .full { grid-column: 1 / -1; }
label { font-size: 12px; color: var(--muted); display: block; margin-bottom: 4px; }
input, select {
  width: 100%;
  border: 1px solid #dbe2ea;
  border-radius: 10px;
  padding: 9px 10px;
  font-size: 13px;
  background: #fff;
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
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 14px 34px rgba(15, 23, 42, .12);
  padding: 10px 12px;
  font-size: 12px;
  animation: toastIn .18s ease;
}
.toast.ok { border-color: #bbf7d0; background: #f0fdf4; color: #166534; }
.toast.warn { border-color: #fde68a; background: #fffbeb; color: #92400e; }
.toast.err { border-color: #fecaca; background: #fef2f2; color: #991b1b; }
@keyframes toastIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
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
  .stack-sticky { position: static; }
  .health-grid { grid-template-columns: repeat(2, 1fr); }
  .progress-grid { grid-template-columns: 1fr; }
  .split-grid { grid-template-columns: 1fr; }
}
@media (max-width: 680px) {
  .quick-row, .quick-row-2, .decision-grid { grid-template-columns: 1fr; }
  .health-grid { grid-template-columns: 1fr 1fr; }
  .top { align-items: flex-start; flex-direction: column; gap: 8px; }
}
</style>
</head>
<body>
<div class="app">
  <div class="top">
    <div class="brand">
      <h1>PerformOS</h1>
      <p>Cockpit vie & entraînement · __TODAY__ · __NOW__</p>
    </div>
    <div class="badges">
      <span class="badge __CAL_BADGE_CLASS__">Apple Calendar: __CAL_STATUS__</span>
      <span class="badge">Readiness: __WBS__/100 (__WBS_LABEL__)</span>
      <span class="badge">ACWR: __ACWR__ (__ACWR_ZONE__)</span>
    </div>
  </div>

  <div class="tabs">
    <button class="tab active" data-tab="planning">Pilotage</button>
    <button class="tab" data-tab="sante">Santé</button>
    <button class="tab" data-tab="progression">Progression</button>
  </div>

  <section class="section active" id="sec-planning">
    <div class="grid-planning">
      <div class="card">
        <h3>Planning hebdomadaire</h3>
        <div class="toolbar">
          <button class="btn" id="prevWeek">← Semaine précédente</button>
          <div class="week-label" id="weekLabel">__WEEK_START__</div>
          <button class="btn" id="nextWeek">Semaine suivante →</button>
        </div>
        <div class="week-wrap">
          <div class="week-grid" id="weekGrid"></div>
        </div>
      </div>

      <div class="stack stack-sticky">
        <div class="card">
          <h3>Cockpit semaine</h3>
          <div class="stats">
            <div class="stat"><div class="v" id="sum-sante">__SUM_SANTE__</div><div class="l">Santé</div></div>
            <div class="stat"><div class="v" id="sum-travail">__SUM_TRAVAIL__</div><div class="l">Travail</div></div>
            <div class="stat"><div class="v" id="sum-relationnel">__SUM_REL__</div><div class="l">Relationnel</div></div>
            <div class="stat"><div class="v" id="sum-apprentissage">__SUM_APP__</div><div class="l">Apprentissage</div></div>
            <div class="stat"><div class="v" id="sum-autre">__SUM_AUTRE__</div><div class="l">Autre</div></div>
            <div class="stat"><div class="v" id="sum-total">__SUM_TOTAL__</div><div class="l">Total (h)</div></div>
          </div>
          <div class="hbar" id="categoryBars"></div>

          <div class="goal">
            <div class="goal-top"><span>Objectif sport semaine</span><span><strong id="goalDone">__GOAL_DONE__h</strong> / <span id="goalTarget">__GOAL_TARGET__h</span></span></div>
            <div class="goal-bar"><div class="goal-fill" id="goalFill" style="width: __GOAL_PCT__%"></div></div>
            <div class="muted" style="font-size:12px;margin-top:6px;">Reste: <span id="goalLeft">__GOAL_LEFT__</span>h</div>
          </div>

          <div class="sync-box">
            <div class="sync-head">
              <div class="sync-title">Sync Apple Calendar</div>
              <span class="badge __CAL_BADGE_CLASS__">__CAL_STATUS__</span>
            </div>
            <div class="sync-meta" id="pendingSyncLabel">__PENDING_SYNC_LABEL__</div>
            <div class="sync-actions">
              <button class="btn-soft" id="pushPendingBtn">Pousser tâches locales</button>
            </div>
          </div>

          <div style="margin-top:12px;">
            <h3 style="margin-bottom:8px;">5 dernières activités</h3>
            __RECENT_HTML__
          </div>
        </div>

        <div class="card">
          <div class="idea-board-head">
            <h3 style="margin:0;">Inbox idées & décisions</h3>
            <select id="ideaFilter" style="max-width:160px;">
              <option value="all">Toutes</option>
              <option value="inbox">Inbox</option>
              <option value="planned">Planifiées</option>
              <option value="done">Terminées</option>
            </select>
          </div>

          <div class="quick-ideas">
            <div class="quick-row">
              <input id="ideaText" type="text" placeholder="Ex: Lancer offre IA PME avec page LinkedIn + 2 RDV test" />
              <button class="btn-primary" id="addIdeaBtn">Ajouter idée</button>
            </div>
            <div class="quick-row-2">
              <select id="ideaType">
                <option value="travail">Travail</option>
                <option value="cardio">Cardio</option>
                <option value="musculation">Musculation</option>
                <option value="mobilite">Mobilité</option>
                <option value="sport_libre">Sport libre</option>
                <option value="apprentissage">Apprentissage</option>
                <option value="relationnel">Relationnel</option>
                <option value="autre">Autre</option>
              </select>
              <select id="ideaMethod">
                <option value="eisenhower">Eisenhower</option>
                <option value="abcde">ABCDE</option>
                <option value="moscow">MoSCoW</option>
                <option value="one_three_five">1-3-5</option>
                <option value="pomodoro">Pomodoro</option>
                <option value="time_blocking">Blocage du temps</option>
              </select>
              <select id="ideaImpact">
                <option value="5">Impact 5/5</option>
                <option value="4">Impact 4/5</option>
                <option value="3" selected>Impact 3/5</option>
                <option value="2">Impact 2/5</option>
                <option value="1">Impact 1/5</option>
              </select>
              <select id="ideaEffort">
                <option value="1">Effort 1/5</option>
                <option value="2">Effort 2/5</option>
                <option value="3" selected>Effort 3/5</option>
                <option value="4">Effort 4/5</option>
                <option value="5">Effort 5/5</option>
              </select>
            </div>
            <div class="sync-actions" style="margin-top:10px;">
              <button class="btn-mini primary" id="quickPomodoroBtn">+ Focus Pomodoro 25 min</button>
            </div>
          </div>

          <div style="margin-top:10px;">
            <div class="decision-grid" id="decisionGrid"></div>
            <div class="idea-list" id="ideaList"></div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="section" id="sec-sante">
    <div class="card" style="margin-bottom:12px;">
      <h3>Synthèse santé</h3>
      <div class="health-grid">
        <div class="kpi"><div class="v">__READINESS_GLOBAL__</div><div class="l">Condition globale /100</div></div>
        <div class="kpi"><div class="v">__WBS__</div><div class="l">Readiness /100</div></div>
        <div class="kpi"><div class="v">__BODY_BATTERY__%</div><div class="l">Body Battery</div></div>
        <div class="kpi"><div class="v">__HRV__</div><div class="l">HRV (ms)</div></div>
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

  <section class="section" id="sec-progression">
    <div class="range-switch">
      <button class="range-btn active" data-range="1m">1M</button>
      <button class="range-btn" data-range="3m">3M</button>
      <button class="range-btn" data-range="1y">1A</button>
      <button class="range-btn" data-range="all">Tout</button>
    </div>
    <div class="progress-grid">
      <div class="chart-card"><div class="chart-title">Heures sport / semaine</div><canvas id="chartHours" height="140"></canvas></div>
      <div class="chart-card"><div class="chart-title">Distance running / semaine (km)</div><canvas id="chartRunKm" height="140"></canvas></div>
      <div class="chart-card"><div class="chart-title">Estimation 10km (minutes)</div><canvas id="chart10k" height="140"></canvas></div>
      <div class="chart-card"><div class="chart-title">VO2max</div><canvas id="chartVo2" height="140"></canvas></div>
    </div>

    <div class="card" style="margin-top:12px;">
      <h3>Répartition sport (temps cumulé)</h3>
      __SPORT_MIX_HTML__
    </div>
  </section>
</div>

<button class="fab" id="openAdd">+ Ajouter activité</button>
<div class="toast-wrap" id="toastWrap"></div>

<div class="modal-bg" id="modalBg">
  <div class="modal">
    <h3 id="modalTitle">Ajouter activité</h3>
    <div class="form-grid">
      <div class="full">
        <label>Titre</label>
        <input id="fTitle" type="text" placeholder="Ex: 10km tempo" />
      </div>
      <div>
        <label>Type</label>
        <select id="fType">
          <option value="cardio">Cardio</option>
          <option value="musculation">Musculation</option>
          <option value="mobilite">Mobilité</option>
          <option value="sport_libre">Sport libre</option>
          <option value="travail">Travail</option>
          <option value="apprentissage">Apprentissage</option>
          <option value="relationnel">Relationnel</option>
          <option value="autre">Autre</option>
        </select>
      </div>
      <div>
        <label>Durée (min)</label>
        <input id="fDuration" type="number" min="5" step="5" value="60" />
      </div>
      <div>
        <label>Jour</label>
        <input id="fDate" type="date" />
      </div>
      <div>
        <label>Heure</label>
        <input id="fTime" type="time" value="09:00" />
      </div>
      <div class="full checkline">
        <input id="fSyncApple" type="checkbox" checked />
        <span>Synchroniser avec Apple Calendar</span>
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn-danger" id="deleteBtn" style="display:none;">Supprimer</button>
      <div style="display:flex; gap:8px; margin-left:auto;">
        <button class="btn" id="cancelBtn">Annuler</button>
        <button class="btn-primary" id="saveBtn">Enregistrer</button>
      </div>
    </div>
    <div class="muted" style="font-size:11px; margin-top:8px;">Mode serveur: persistance SQLite + sync Apple bidirectionnelle. Mode fichier local: fallback localStorage.</div>
  </div>
</div>

<script>
const TYPE_DEFS = __TYPE_DEFS__;
const CATEGORY_LABELS = __CATEGORY_LABELS__;
const BASE_EVENTS = __PLANNER_EVENTS__;
const STORAGE_KEY = 'performos_planner_v1';
const IDEAS_KEY = 'performos_idea_inbox_v2';
const WEEK_START_ISO = '__WEEK_START__';
const GOAL_TARGET = __GOAL_TARGET_NUM__;
const API_TOKEN = __API_TOKEN_JS__;
const CAL_SYNC_ENABLED = __CAL_SYNC_ENABLED__;
let API_ENABLED = location.protocol.startsWith('http');
const API_BASE = '/api/planner';
const METHOD_LABELS = {
  eisenhower: 'Eisenhower',
  abcde: 'ABCDE',
  moscow: 'MoSCoW',
  one_three_five: '1-3-5',
  pomodoro: 'Pomodoro',
  time_blocking: 'Time Blocking',
};

const PROG = {
  hours: { labels: __HOURS_LABELS__, values: __HOURS_VALUES__ },
  runKm: { labels: __RUN_LABELS__, values: __RUN_VALUES__ },
  tenk: { labels: __TENK_LABELS__, values: __TENK_VALUES__ },
  vo2: { labels: __VO2_LABELS__, values: __VO2_VALUES__ },
};
const RANGE_LIMITS = { '1m': 4, '3m': 13, '1y': 52, 'all': 0 };

let weekOffset = 0;
let editingId = null;
let currentEvents = [];
let activeRange = '1y';
const chartInstances = {};

function showToast(message, kind) {
  const wrap = document.getElementById('toastWrap');
  if (!wrap) return;
  const el = document.createElement('div');
  el.className = 'toast ' + (kind || 'ok');
  el.textContent = message;
  wrap.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(-4px)';
    setTimeout(() => el.remove(), 220);
  }, 3200);
}

function notifySyncResult(payload) {
  if (!payload || typeof payload !== 'object') return;
  const created = payload.created || {};
  const result = payload.result || {};
  const err = created.apple_sync_error || result.sync_error || result.error || payload.error;
  if (err) {
    if (String(err).includes('calendar_permission_denied')) {
      showToast('Apple Calendar refusé par macOS: autorise iTerm/Terminal dans Confidentialité > Calendriers.', 'warn');
    } else {
      showToast('Sync Apple partielle: ' + err, 'warn');
    }
  }
}

function parseIso(s) {
  if (!s) return null;
  const x = new Date(String(s).replace(' ', 'T'));
  return Number.isNaN(x.getTime()) ? null : x;
}

function toIsoNoMs(d) {
  return d.toISOString().slice(0, 19);
}

function addMin(d, m) {
  return new Date(d.getTime() + m * 60000);
}

function startOfWeek(baseDate) {
  const d = new Date(baseDate);
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  d.setHours(0, 0, 0, 0);
  return d;
}

function addDays(d, n) {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function hm(d) {
  return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}

function inferTypeFromEvent(ev) {
  if (ev.type && TYPE_DEFS[ev.type]) return ev.type;
  const text = ((ev.title || '') + ' ' + (ev.category || '')).toLowerCase();
  if (text.includes('muscu') || text.includes('strength') || text.includes('full body')) return 'musculation';
  if (text.includes('yoga') || text.includes('mobil')) return 'mobilite';
  if (text.includes('run') || text.includes('course') || text.includes('cardio') || text.includes('10km')) return 'cardio';
  if (text.includes('tennis') || text.includes('golf') || text.includes('swim') || text.includes('sport')) return 'sport_libre';
  if (ev.category === 'travail') return 'travail';
  if (ev.category === 'apprentissage') return 'apprentissage';
  if (ev.category === 'relationnel') return 'relationnel';
  if (ev.category === 'sante') return 'cardio';
  return 'autre';
}

function escapeHtml(v) {
  return String(v || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function apiHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (API_TOKEN) h['X-PerformOS-Token'] = API_TOKEN;
  return h;
}

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch (_) {
    return {};
  }
}

function saveState(s) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

function loadIdeas() {
  try {
    const rows = JSON.parse(localStorage.getItem(IDEAS_KEY) || '[]');
    if (!Array.isArray(rows)) return [];
    return rows
      .map((x) => ({
        id: String(x.id || ''),
        title: String(x.title || '').trim(),
        type: String(x.type || 'autre'),
        method: String(x.method || 'eisenhower'),
        impact: Number(x.impact || 3),
        effort: Number(x.effort || 3),
        status: String(x.status || 'inbox'),
        created_at: String(x.created_at || ''),
      }))
      .filter((x) => x.title);
  } catch (_) {
    return [];
  }
}

function saveIdeas(rows) {
  localStorage.setItem(IDEAS_KEY, JSON.stringify(rows || []));
}

function newIdeaId() {
  if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
  return 'idea-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
}

function ideaScore(it) {
  const imp = Math.max(1, Math.min(5, Number(it.impact || 3)));
  const eff = Math.max(1, Math.min(5, Number(it.effort || 3)));
  const methodBoost = it.method === 'eisenhower' ? 1.2 : it.method === 'abcde' ? 1.1 : 1.0;
  return (imp * methodBoost) - (eff * 0.6);
}

function ideaLane(it) {
  const score = ideaScore(it);
  if (score >= 3.2) return 'now';
  if (score >= 2.1) return 'next';
  return 'later';
}

function methodDefaultDuration(method) {
  if (method === 'pomodoro') return 25;
  if (method === 'one_three_five') return 45;
  if (method === 'time_blocking') return 90;
  return 60;
}

function addIdeaFromForm() {
  const textEl = document.getElementById('ideaText');
  const title = String((textEl && textEl.value) || '').trim();
  if (!title) {
    showToast('Ajoute un titre d’idée.', 'warn');
    return;
  }
  const type = String((document.getElementById('ideaType') || {}).value || 'autre');
  const method = String((document.getElementById('ideaMethod') || {}).value || 'eisenhower');
  const impact = Number((document.getElementById('ideaImpact') || {}).value || 3);
  const effort = Number((document.getElementById('ideaEffort') || {}).value || 3);

  const rows = loadIdeas();
  rows.unshift({
    id: newIdeaId(),
    title,
    type,
    method,
    impact,
    effort,
    status: 'inbox',
    created_at: new Date().toISOString(),
  });
  saveIdeas(rows);
  if (textEl) textEl.value = '';
  renderIdeas();
  showToast('Idée ajoutée à l’inbox.', 'ok');
}

function updateIdeaStatus(id, status) {
  const rows = loadIdeas().map((x) => x.id === id ? Object.assign({}, x, { status }) : x);
  saveIdeas(rows);
  renderIdeas();
}

function deleteIdeaById(id) {
  const rows = loadIdeas().filter((x) => x.id !== id);
  saveIdeas(rows);
  renderIdeas();
}

function planIdea(id) {
  const rows = loadIdeas();
  const it = rows.find((x) => x.id === id);
  if (!it) return;
  const now = new Date();
  openModal(null, {
    title: it.title,
    type: it.type,
    date: isoDate(now),
    time: '09:00',
    duration: methodDefaultDuration(it.method),
    syncApple: true,
  });
  updateIdeaStatus(id, 'planned');
}

async function quickPomodoroFromIdea(id) {
  const rows = loadIdeas();
  const it = rows.find((x) => x.id === id);
  if (!it) return;
  const now = new Date();
  const start = new Date(now);
  start.setMinutes(Math.ceil(start.getMinutes() / 5) * 5, 0, 0);
  const end = addMin(start, 25);
  const payload = {
    title: '🎯 Focus 25m · ' + it.title,
    type: it.type || 'travail',
    category: (TYPE_DEFS[it.type] || TYPE_DEFS.autre).category,
    icon: (TYPE_DEFS[it.type] || TYPE_DEFS.autre).icon,
    color: (TYPE_DEFS[it.type] || TYPE_DEFS.autre).color,
    start_at: toIsoNoMs(start),
    end_at: toIsoNoMs(end),
    source: 'local_ui',
    task_date: isoDate(start),
    task_time: hm(start) + ':00',
    duration_min: 25,
    sync_apple: true,
  };
  await createEvent(payload);
  updateIdeaStatus(id, 'planned');
  await renderWeek();
  showToast('Bloc Pomodoro ajouté au planning.', 'ok');
}

function renderIdeas() {
  const rows = loadIdeas().sort((a, b) => {
    const sa = ideaScore(a);
    const sb = ideaScore(b);
    if (sb !== sa) return sb - sa;
    return String(b.created_at || '').localeCompare(String(a.created_at || ''));
  });

  const filter = (document.getElementById('ideaFilter') || {}).value || 'all';
  const filtered = rows.filter((x) => filter === 'all' ? true : x.status === filter);

  const laneRows = rows.filter((x) => x.status !== 'done');
  const buckets = { now: [], next: [], later: [] };
  laneRows.forEach((x) => buckets[ideaLane(x)].push(x));

  const decisionGrid = document.getElementById('decisionGrid');
  if (decisionGrid) {
    const laneHtml = (key, label) => {
      const items = buckets[key].slice(0, 3).map((x) => (
        '<div class="decision-item">' + escapeHtml(x.title) + '</div>'
      )).join('') || '<div class="muted" style="font-size:11px;">—</div>';
      return (
        '<div class="decision-col">'
        + '<div class="decision-title">' + label + '</div>'
        + items
        + '</div>'
      );
    };
    decisionGrid.innerHTML =
      laneHtml('now', 'Now (agir)') +
      laneHtml('next', 'Next (planifier)') +
      laneHtml('later', 'Later (parking)');
  }

  const list = document.getElementById('ideaList');
  if (!list) return;
  if (!filtered.length) {
    list.innerHTML = '<div class="muted" style="font-size:12px;">Aucune idée pour ce filtre.</div>';
    return;
  }

  list.innerHTML = filtered.map((x) => {
    const lane = ideaLane(x);
    const score = ideaScore(x).toFixed(1);
    const laneLabel = lane === 'now' ? 'Now' : lane === 'next' ? 'Next' : 'Later';
    const method = METHOD_LABELS[x.method] || x.method;
    return (
      '<div class="idea-item ' + (x.status === 'done' ? 'done' : '') + '">'
      + '<div class="idea-top"><div class="idea-title">' + escapeHtml(x.title) + '</div>'
      + '<div class="pill">Score ' + score + '</div></div>'
      + '<div class="idea-meta">'
      + '<span class="pill">' + escapeHtml((TYPE_DEFS[x.type] || TYPE_DEFS.autre).label) + '</span>'
      + '<span class="pill">' + escapeHtml(method) + '</span>'
      + '<span class="pill">Impact ' + Number(x.impact || 3) + '/5</span>'
      + '<span class="pill">Effort ' + Number(x.effort || 3) + '/5</span>'
      + '<span class="pill">' + laneLabel + '</span>'
      + '</div>'
      + '<div class="idea-actions">'
      + '<button class="btn-mini primary" data-idea-plan="' + x.id + '">Planifier</button>'
      + '<button class="btn-mini" data-idea-pomo="' + x.id + '">+25m</button>'
      + '<button class="btn-mini success" data-idea-done="' + x.id + '">Fait</button>'
      + '<button class="btn-mini" data-idea-del="' + x.id + '">Supprimer</button>'
      + '</div>'
      + '</div>'
    );
  }).join('');

  list.querySelectorAll('[data-idea-plan]').forEach((btn) => {
    btn.addEventListener('click', () => planIdea(btn.getAttribute('data-idea-plan') || ''));
  });
  list.querySelectorAll('[data-idea-pomo]').forEach((btn) => {
    btn.addEventListener('click', () => quickPomodoroFromIdea(btn.getAttribute('data-idea-pomo') || ''));
  });
  list.querySelectorAll('[data-idea-done]').forEach((btn) => {
    btn.addEventListener('click', () => updateIdeaStatus(btn.getAttribute('data-idea-done') || '', 'done'));
  });
  list.querySelectorAll('[data-idea-del]').forEach((btn) => {
    btn.addEventListener('click', () => deleteIdeaById(btn.getAttribute('data-idea-del') || ''));
  });
}

function uidForBase(ev, idx) {
  return 'b:' + (ev.id || idx);
}

function mergedEvents() {
  const state = loadState();
  const overrides = state.overrides || {};
  const custom = state.custom || [];

  const base = BASE_EVENTS.map((ev, idx) => {
    const uid = uidForBase(ev, idx);
    const ov = overrides[uid] || {};
    if (ov.deleted) return null;
    const merged = Object.assign({}, ev, ov);
    merged._uid = uid;
    return merged;
  }).filter(Boolean);

  const extra = custom.map(ev => {
    const x = Object.assign({}, ev);
    x._uid = x._uid || ('c:' + Date.now() + ':' + Math.random().toString(36).slice(2, 7));
    return x;
  });

  return base.concat(extra);
}

async function fetchApiEvents(startIso, endIso) {
  const url = API_BASE + '/events?start=' + encodeURIComponent(startIso) + '&end=' + encodeURIComponent(endIso);
  const r = await fetch(url, { method: 'GET' });
  if (!r.ok) throw new Error('planner_api_unavailable');
  const payload = await r.json();
  const evts = (payload.events || []).map((ev, idx) => {
    const uid = String(ev.id || ev.task_id || ('api:' + idx));
    const x = Object.assign({}, ev);
    x._uid = uid;
    return x;
  });
  return evts;
}

function findCurrentEvent(uid) {
  return currentEvents.find(e => e._uid === uid);
}

function eventDurationMin(ev) {
  const s = parseIso(ev.start_at);
  const e = parseIso(ev.end_at);
  if (!s || !e) return 60;
  return Math.max(5, Math.round((e - s) / 60000));
}

function setEvent(uid, payload) {
  const state = loadState();
  state.overrides = state.overrides || {};
  state.custom = state.custom || [];

  if (uid.startsWith('c:')) {
    state.custom = state.custom.map(ev => ev._uid === uid ? Object.assign({}, ev, payload) : ev);
  } else {
    state.overrides[uid] = Object.assign({}, state.overrides[uid] || {}, payload);
  }
  saveState(state);
}

function deleteEvent(uid) {
  const state = loadState();
  state.overrides = state.overrides || {};
  state.custom = state.custom || [];
  if (uid.startsWith('c:')) {
    state.custom = state.custom.filter(ev => ev._uid !== uid);
  } else {
    state.overrides[uid] = Object.assign({}, state.overrides[uid] || {}, { deleted: true });
  }
  saveState(state);
}

function createCustomEvent(ev) {
  const state = loadState();
  state.custom = state.custom || [];
  ev._uid = 'c:' + Date.now() + ':' + Math.random().toString(36).slice(2, 7);
  state.custom.push(ev);
  saveState(state);
}

async function updateEvent(uid, payload) {
  const ev = findCurrentEvent(uid);
  if (!ev) return;

  if (API_ENABLED) {
    try {
      let route = null;
      if (ev.task_id) route = API_BASE + '/tasks/' + ev.task_id;
      else if (ev.id && String(ev.id).startsWith('task:')) route = API_BASE + '/tasks/' + String(ev.id).split(':')[1];
      else if (ev.calendar_uid) route = API_BASE + '/apple/' + encodeURIComponent(ev.calendar_uid);
      else if (ev.id && String(ev.id).startsWith('apple:')) route = API_BASE + '/apple/' + encodeURIComponent(String(ev.id).slice(6));

      if (route) {
        const body = Object.assign({}, payload, { sync_apple: true });
        const r = await fetch(route, {
          method: 'PATCH',
          headers: apiHeaders(),
          body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error('update_failed');
        const out = await r.json();
        notifySyncResult(out);
        return;
      }
    } catch (_) {
      API_ENABLED = false;
    }
  }

  // fallback local
  setEvent(uid, payload);
}

async function removeEvent(uid) {
  const ev = findCurrentEvent(uid);
  if (!ev) return;

  if (API_ENABLED) {
    try {
      let route = null;
      if (ev.task_id) route = API_BASE + '/tasks/' + ev.task_id;
      else if (ev.id && String(ev.id).startsWith('task:')) route = API_BASE + '/tasks/' + String(ev.id).split(':')[1];
      else if (ev.calendar_uid) route = API_BASE + '/apple/' + encodeURIComponent(ev.calendar_uid);
      else if (ev.id && String(ev.id).startsWith('apple:')) route = API_BASE + '/apple/' + encodeURIComponent(String(ev.id).slice(6));

      if (route) {
        const r = await fetch(route, {
          method: 'DELETE',
          headers: apiHeaders(),
        });
        if (!r.ok) throw new Error('delete_failed');
        const out = await r.json();
        notifySyncResult(out);
        return;
      }
    } catch (_) {
      API_ENABLED = false;
    }
  }

  deleteEvent(uid);
}

async function createEvent(payload) {
  if (API_ENABLED) {
    try {
      const r = await fetch(API_BASE + '/tasks', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error('create_failed');
      const out = await r.json();
      notifySyncResult(out);
      return;
    } catch (_) {
      API_ENABLED = false;
    }
  }
  createCustomEvent(payload);
}

async function pushPendingApple() {
  if (!API_ENABLED) {
    showToast('Mode fichier local: impossible de pousser vers Apple sans serveur.', 'warn');
    return;
  }
  try {
    const r = await fetch(API_BASE + '/calendar/push', {
      method: 'POST',
      headers: apiHeaders(),
      body: JSON.stringify({}),
    });
    if (!r.ok) throw new Error('push_failed');
    const out = await r.json();
    const res = out.result || {};
    if (res.synced > 0) showToast('Apple sync: ' + res.synced + ' tâche(s) poussée(s).', 'ok');
    else if (res.failed > 0) showToast('Apple sync: aucune tâche poussée (' + (res.error || 'erreur') + ').', 'warn');
    else showToast('Aucune tâche locale en attente.', 'ok');
    await renderWeek();
  } catch (_) {
    showToast('Échec du push Apple Calendar.', 'err');
  }
}

async function moveEventToDate(uid, newDateIso) {
  const ev = findCurrentEvent(uid) || mergedEvents().find(x => x._uid === uid);
  if (!ev) return;
  const s = parseIso(ev.start_at);
  const e = parseIso(ev.end_at);
  if (!s || !e) return;
  const dur = e - s;

  const movedStart = new Date(newDateIso + 'T' + hm(s) + ':00');
  const movedEnd = new Date(movedStart.getTime() + dur);
  await updateEvent(uid, { start_at: toIsoNoMs(movedStart), end_at: toIsoNoMs(movedEnd) });
  await renderWeek();
}

function openModal(ev, draft) {
  editingId = ev ? ev._uid : null;
  const title = document.getElementById('modalTitle');
  const delBtn = document.getElementById('deleteBtn');

  if (ev) {
    title.textContent = 'Modifier activité';
    delBtn.style.display = 'inline-block';
    document.getElementById('fTitle').value = ev.title || '';
    document.getElementById('fType').value = inferTypeFromEvent(ev);
    const s = parseIso(ev.start_at) || new Date();
    document.getElementById('fDate').value = isoDate(s);
    document.getElementById('fTime').value = hm(s);
    document.getElementById('fDuration').value = eventDurationMin(ev);
    document.getElementById('fSyncApple').checked = true;
  } else {
    title.textContent = 'Ajouter activité';
    delBtn.style.display = 'none';
    const now = new Date();
    document.getElementById('fTitle').value = String((draft && draft.title) || '');
    document.getElementById('fType').value = String((draft && draft.type) || 'cardio');
    document.getElementById('fDate').value = String((draft && draft.date) || isoDate(now));
    document.getElementById('fTime').value = String((draft && draft.time) || '09:00');
    document.getElementById('fDuration').value = Number((draft && draft.duration) || 60);
    document.getElementById('fSyncApple').checked = draft && typeof draft.syncApple === 'boolean' ? !!draft.syncApple : true;
  }

  document.getElementById('modalBg').style.display = 'flex';
}

function closeModal() {
  editingId = null;
  document.getElementById('modalBg').style.display = 'none';
}

async function submitModal() {
  const title = (document.getElementById('fTitle').value || '').trim() || TYPE_DEFS[document.getElementById('fType').value].label;
  const type = document.getElementById('fType').value;
  const dateIso = document.getElementById('fDate').value;
  const timeIso = document.getElementById('fTime').value || '09:00';
  const duration = Math.max(5, Number(document.getElementById('fDuration').value || 60));
  const syncApple = !!document.getElementById('fSyncApple').checked;

  if (!dateIso) return;

  const start = new Date(dateIso + 'T' + timeIso + ':00');
  const end = addMin(start, duration);
  const def = TYPE_DEFS[type] || TYPE_DEFS.autre;

  const payload = {
    title,
    type,
    category: def.category,
    icon: def.icon,
    color: def.color,
    start_at: toIsoNoMs(start),
    end_at: toIsoNoMs(end),
    source: 'local_ui',
    calendar_name: '',
  };

  if (editingId) await updateEvent(editingId, payload);
  else await createEvent(Object.assign({}, payload, {
    task_date: dateIso,
    task_time: timeIso + ':00',
    duration_min: duration,
    sync_apple: syncApple,
  }));

  closeModal();
  await renderWeek();
}

async function removeModalEvent() {
  if (!editingId) return;
  await removeEvent(editingId);
  closeModal();
  await renderWeek();
}

function categoryDurations(events) {
  const out = { sante: 0, travail: 0, relationnel: 0, apprentissage: 0, autre: 0 };
  events.forEach(ev => {
    const s = parseIso(ev.start_at);
    const e = parseIso(ev.end_at);
    if (!s || !e) return;
    const h = Math.max(0, (e - s) / 3600000);
    const t = inferTypeFromEvent(ev);
    const cat = (TYPE_DEFS[t] || TYPE_DEFS.autre).category;
    out[cat] += h;
  });
  return out;
}

function renderCategoryBars(durations) {
  const wrap = document.getElementById('categoryBars');
  const keys = ['sante', 'travail', 'relationnel', 'apprentissage', 'autre'];
  const total = keys.reduce((a, k) => a + durations[k], 0) || 1;
  let html = '';
  keys.forEach(k => {
    const v = durations[k] || 0;
    const pct = Math.max(2, (v / total) * 100);
    let color = '#9ca3af';
    if (k === 'sante') color = '#2da44e';
    if (k === 'travail') color = '#3b82f6';
    if (k === 'relationnel') color = '#ec4899';
    if (k === 'apprentissage') color = '#eab308';
    html += '<div class="hrow">'
      + '<span>' + (CATEGORY_LABELS[k] || k) + '</span>'
      + '<div class="track"><div class="fill" style="width:' + pct.toFixed(1) + '%;background:' + color + ';"></div></div>'
      + '<span>' + v.toFixed(1) + 'h</span>'
      + '</div>';
  });
  wrap.innerHTML = html;
}

async function renderWeek() {
  const baseStart = startOfWeek(parseIso(WEEK_START_ISO) || new Date());
  const start = addDays(baseStart, weekOffset * 7);
  const end = addDays(start, 7);

  document.getElementById('weekLabel').textContent = isoDate(start) + ' → ' + isoDate(addDays(end, -1));

  let allEvents = [];
  if (API_ENABLED) {
    try {
      const startIso = isoDate(start) + 'T00:00:00';
      const endIso = isoDate(addDays(end, 1)) + 'T00:00:00';
      allEvents = await fetchApiEvents(startIso, endIso);
    } catch (_) {
      API_ENABLED = false;
      allEvents = mergedEvents();
    }
  } else {
    allEvents = mergedEvents();
  }

  const events = allEvents.filter(ev => {
    const s = parseIso(ev.start_at);
    return s && s >= start && s < end;
  });
  currentEvents = events.slice();

  const pendingAll = allEvents.filter(ev => {
    const id = String(ev.id || '');
    return id.startsWith('task:') && !ev.calendar_uid;
  }).length;
  const pendingLabel = document.getElementById('pendingSyncLabel');
  const pushBtn = document.getElementById('pushPendingBtn');
  if (pendingLabel) {
    pendingLabel.textContent = pendingAll > 0
      ? (pendingAll + ' tâche(s) locale(s) à pousser vers Apple Calendar')
      : 'Aucune tâche locale en attente de synchronisation';
  }
  if (pushBtn) {
    pushBtn.disabled = pendingAll <= 0;
    pushBtn.style.opacity = pendingAll <= 0 ? '.6' : '1';
  }

  const durations = categoryDurations(events);
  const total = durations.sante + durations.travail + durations.relationnel + durations.apprentissage + durations.autre;

  document.getElementById('sum-sante').textContent = durations.sante.toFixed(1);
  document.getElementById('sum-travail').textContent = durations.travail.toFixed(1);
  document.getElementById('sum-relationnel').textContent = durations.relationnel.toFixed(1);
  document.getElementById('sum-apprentissage').textContent = durations.apprentissage.toFixed(1);
  document.getElementById('sum-autre').textContent = durations.autre.toFixed(1);
  document.getElementById('sum-total').textContent = total.toFixed(1);
  renderCategoryBars(durations);

  const goalDone = durations.sante;
  const goalLeft = Math.max(0, GOAL_TARGET - goalDone);
  const goalPct = Math.min(100, GOAL_TARGET ? (goalDone / GOAL_TARGET) * 100 : 0);
  document.getElementById('goalDone').textContent = goalDone.toFixed(1) + 'h';
  document.getElementById('goalLeft').textContent = goalLeft.toFixed(1);
  document.getElementById('goalFill').style.width = goalPct.toFixed(1) + '%';

  const days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
  const grid = document.getElementById('weekGrid');
  grid.innerHTML = '';

  for (let i = 0; i < 7; i++) {
    const d = addDays(start, i);
    const dateIso = isoDate(d);

    const col = document.createElement('div');
    col.className = 'day-col';
    col.dataset.date = dateIso;

    const head = document.createElement('div');
    head.className = 'day-head';
    head.innerHTML = '<span>' + days[i] + ' · ' + dateIso + '</span>'
      + '<button class="day-add" data-date="' + dateIso + '">+ Ajouter</button>';
    col.appendChild(head);

    col.addEventListener('dragover', ev => ev.preventDefault());
    col.addEventListener('drop', ev => {
      ev.preventDefault();
      const uid = ev.dataTransfer.getData('text/plain');
      if (uid) moveEventToDate(uid, dateIso);
    });

    const evts = events
      .filter(ev => {
        const s = parseIso(ev.start_at);
        return s && isoDate(s) === dateIso;
      })
      .sort((a, b) => parseIso(a.start_at) - parseIso(b.start_at));

    if (!evts.length) {
      const empty = document.createElement('div');
      empty.className = 'muted';
      empty.style.fontSize = '12px';
      empty.textContent = 'Aucune activité';
      col.appendChild(empty);
    }

    evts.forEach(ev => {
      const t = inferTypeFromEvent(ev);
      const def = TYPE_DEFS[t] || TYPE_DEFS.autre;
      const s = parseIso(ev.start_at);
      const e = parseIso(ev.end_at);
      const dur = Math.max(5, Math.round((e - s) / 60000));

      const card = document.createElement('div');
      card.className = 'event';
      card.draggable = true;
      card.style.borderLeftColor = def.color;
      card.innerHTML = '<div class="event-title">' + def.icon + ' ' + escapeHtml(ev.title || def.label) + '</div>'
        + '<div class="event-meta"><span>' + hm(s) + ' · ' + dur + ' min</span>'
        + '<button class="event-x" title="Supprimer">✕</button></div>';

      card.addEventListener('dragstart', () => {
        card.classList.add('dragging');
      });
      card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
      });
      card.addEventListener('dragstart', evDrag => {
        evDrag.dataTransfer.setData('text/plain', ev._uid);
      });
      card.addEventListener('click', evClick => {
        if (evClick.target.classList.contains('event-x')) return;
        openModal(ev);
      });
      card.querySelector('.event-x').addEventListener('click', evDel => {
        evDel.stopPropagation();
        if (confirm('Supprimer cette activité ?')) {
          removeEvent(ev._uid).then(renderWeek);
        }
      });

      col.appendChild(card);
    });

    grid.appendChild(col);
  }

  grid.querySelectorAll('.day-add').forEach(btn => {
    btn.addEventListener('click', () => {
      openModal(null);
      document.getElementById('fDate').value = btn.dataset.date;
    });
  });

  renderIdeas();
}

function activateTab(tabId) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector('.tab[data-tab="' + tabId + '"]').classList.add('active');
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('sec-' + tabId).classList.add('active');
  window.scrollTo(0, 0);
}

function filterSeries(dataObj) {
  const limit = RANGE_LIMITS[activeRange] || 0;
  if (!limit) return dataObj;
  const labels = dataObj.labels.slice(-limit);
  const values = dataObj.values.slice(-limit);
  return { labels, values };
}

function chartLine(canvasId, labels, values, color, yReverse) {
  const el = document.getElementById(canvasId);
  if (!el) return;
  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
  }
  chartInstances[canvasId] = new Chart(el, {
    type: 'line',
    data: { labels, datasets: [{ data: values, borderColor: color, backgroundColor: color + '22', fill: true, tension: .25, pointRadius: 0 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { maxTicksLimit: 8, color: '#64748b' }, grid: { display: false } },
        y: { reverse: !!yReverse, ticks: { color: '#64748b' }, grid: { color: '#eef2f7' } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function initCharts() {
  const h = filterSeries(PROG.hours);
  const r = filterSeries(PROG.runKm);
  const t = filterSeries(PROG.tenk);
  const v = filterSeries(PROG.vo2);
  chartLine('chartHours', h.labels, h.values, '#3b82f6', false);
  chartLine('chartRunKm', r.labels, r.values, '#10b981', false);
  chartLine('chart10k', t.labels, t.values, '#f97316', true);
  chartLine('chartVo2', v.labels, v.values, '#8b5cf6', false);
}

function setRange(range) {
  activeRange = range;
  document.querySelectorAll('.range-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.range === range);
  });
  initCharts();
}

window.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => activateTab(t.dataset.tab));
  });

  document.getElementById('prevWeek').addEventListener('click', () => { weekOffset -= 1; renderWeek(); });
  document.getElementById('nextWeek').addEventListener('click', () => { weekOffset += 1; renderWeek(); });

  document.getElementById('openAdd').addEventListener('click', () => openModal(null));
  document.getElementById('cancelBtn').addEventListener('click', closeModal);
  document.getElementById('saveBtn').addEventListener('click', () => { submitModal(); });
  document.getElementById('deleteBtn').addEventListener('click', () => { removeModalEvent(); });
  document.getElementById('modalBg').addEventListener('click', (e) => {
    if (e.target.id === 'modalBg') closeModal();
  });

  document.getElementById('goalTarget').textContent = GOAL_TARGET.toFixed(1) + 'h';
  if (!CAL_SYNC_ENABLED) {
    showToast('Apple Calendar non connecté dans ce contexte.', 'warn');
  }
  const pushBtn = document.getElementById('pushPendingBtn');
  if (pushBtn) {
    pushBtn.addEventListener('click', pushPendingApple);
  }
  const addIdeaBtn = document.getElementById('addIdeaBtn');
  if (addIdeaBtn) addIdeaBtn.addEventListener('click', addIdeaFromForm);
  const ideaText = document.getElementById('ideaText');
  if (ideaText) {
    ideaText.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') {
        ev.preventDefault();
        addIdeaFromForm();
      }
    });
  }
  const ideaFilter = document.getElementById('ideaFilter');
  if (ideaFilter) ideaFilter.addEventListener('change', renderIdeas);
  const quickPomodoroBtn = document.getElementById('quickPomodoroBtn');
  if (quickPomodoroBtn) {
    quickPomodoroBtn.addEventListener('click', () => {
      openModal(null, {
        title: '🎯 Focus 25m',
        type: 'travail',
        duration: 25,
        time: '09:00',
        syncApple: true,
      });
    });
  }
  document.querySelectorAll('.range-btn').forEach(btn => {
    btn.addEventListener('click', () => setRange(btn.dataset.range));
  });
  renderWeek();
  initCharts();
});
</script>
</body>
</html>
"""

    repl = {
        "__TODAY__": today,
        "__NOW__": now,
        "__CAL_STATUS__": cal_status,
        "__CAL_BADGE_CLASS__": "ok" if cal_enabled else "warn",
        "__PENDING_SYNC_LABEL__": pending_sync_label,
        "__CAL_SYNC_ENABLED__": "true" if cal_enabled else "false",
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
        "__API_TOKEN_JS__": json.dumps(api_token, ensure_ascii=False),
    }

    for key, value in repl.items():
        html = html.replace(key, value)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    kb = output_path.stat().st_size // 1024
    print(f"  ✅ Dashboard : {output_path} ({kb}KB)")
