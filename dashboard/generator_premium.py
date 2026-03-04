"""
generator_premium.py — PerformOS · Premium Dark Dashboard (MacBook Pro M5)
Design: Dark Navy + Sport Agent Insights + Chart.js
"""
from __future__ import annotations

from pathlib import Path
from datetime import date, datetime, timedelta
import json
from html import escape


TYPE_DEFS = {
    "cardio":        {"label": "Cardio",        "color": "#f97316", "icon": "🏃"},
    "musculation":   {"label": "Musculation",   "color": "#8b5cf6", "icon": "🏋️"},
    "mobilite":      {"label": "Mobilité",      "color": "#06b6d4", "icon": "🧘"},
    "sport_libre":   {"label": "Sport libre",   "color": "#10b981", "icon": "🎾"},
    "travail":       {"label": "Travail",        "color": "#3b82f6", "icon": "💼"},
    "apprentissage": {"label": "Apprentissage", "color": "#eab308", "icon": "📚"},
    "relationnel":   {"label": "Relationnel",   "color": "#ec4899", "icon": "💬"},
    "autre":         {"label": "Autre",          "color": "#6b7280", "icon": "🧩"},
}

SEVERITY_COLORS = {"critical": "#ef4444", "warning": "#f97316", "info": "#3b82f6", "success": "#10b981"}
SEVERITY_BG = {
    "critical": "rgba(239,68,68,0.12)", "warning": "rgba(249,115,22,0.12)",
    "info": "rgba(59,130,246,0.12)",   "success": "rgba(16,185,129,0.12)",
}

SPORT_ICONS = {
    "Running": "🏃", "Strength Training": "🏋️", "Swimming": "🏊",
    "Cycling": "🚴", "Tennis": "🎾", "Tennis v2": "🎾", "Tennis V2": "🎾",
    "Snowboarding": "🏂", "Resort Snowboarding": "🏂", "Cross Training": "⚡",
    "Cross_country_skiing": "⛷️", "Walking": "🚶", "Yoga": "🧘",
    "SnowSports": "⛷️", "Track Running": "🏃", "Treadmill Running": "🏃",
    "DownhillSkiing": "🎿", "Skating": "⛸️", "Other": "🏅", "Wakeboard": "🏄",
}

SPORT_COLORS = {
    "Running": "#f97316", "Strength Training": "#8b5cf6", "Swimming": "#06b6d4",
    "Cycling": "#10b981", "Tennis": "#84cc16", "Tennis v2": "#84cc16",
    "Snowboarding": "#60a5fa", "Resort Snowboarding": "#60a5fa",
    "Cross Training": "#f59e0b", "Cross_country_skiing": "#a78bfa",
    "Walking": "#94a3b8", "Yoga": "#f472b6",
}


def _jse(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _latest_metric(metrics_history: list, metric: str, default: float = 0.0) -> float:
    vals = [m for m in metrics_history if m.get("metric") == metric and m.get("value") is not None]
    return float(vals[-1]["value"]) if vals else float(default)


def _infer_event_type(event: dict) -> str:
    title = (event.get("title") or "").lower()
    cat = (event.get("category") or "").lower()
    if any(k in title for k in ["muscu", "strength", "gym", "halt", "full body"]):
        return "musculation"
    if any(k in title for k in ["yoga", "mobil", "stretch"]):
        return "mobilite"
    if any(k in title for k in ["run", "course", "jog", "10km", "cardio"]):
        return "cardio"
    if any(k in title for k in ["tennis", "golf", "swim", "vélo", "sport", "snow", "ski", "wake"]):
        return "sport_libre"
    if cat == "travail":
        return "travail"
    if cat == "apprentissage":
        return "apprentissage"
    if cat == "relationnel":
        return "relationnel"
    return "autre"


def _prepare_pilot_events(pilot_events: list) -> list:
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
            "category": t,
            "type": t,
            "icon": d["icon"],
            "color": d["color"],
        })
    return rows


def _ring_svg(value: float, max_val: float, color: str, size: int = 120, stroke: int = 10) -> str:
    pct = min(1.0, max(0.0, value / max_val)) if max_val else 0
    r = (size - stroke * 2) / 2
    circ = 2 * 3.14159265 * r
    dash = pct * circ
    cx = cy = size / 2
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="{stroke}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}"'
        f' stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"'
        f' transform="rotate(-90 {cx} {cy})">'
        f'<animate attributeName="stroke-dasharray" from="0 {circ:.1f}" to="{dash:.1f} {circ:.1f}"'
        f' dur="1.2s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>'
        f'</circle></svg>'
    )


CSS = """:root{--bg:#080b14;--surface:#0e1220;--card:#141927;--card2:#1a2035;--border:rgba(255,255,255,0.07);--text:#f0f2f7;--muted:#7b8eb0;--dim:#4a5568;--accent:#6366f1;--accent2:#818cf8;--orange:#f97316;--teal:#10b981;--blue:#3b82f6;--red:#ef4444;--yellow:#eab308;--purple:#8b5cf6;--pink:#ec4899;--shadow:0 8px 32px rgba(0,0,0,0.6);--shadow-sm:0 2px 12px rgba(0,0,0,0.4);--radius:16px;--radius-sm:10px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Inter',system-ui,sans-serif;color:var(--text);min-height:100vh;-webkit-font-smoothing:antialiased;}
.app{max-width:1500px;margin:0 auto;padding:20px 24px 80px;}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid var(--border);}
.brand-logo{font-size:11px;font-weight:800;letter-spacing:.15em;text-transform:uppercase;color:var(--accent2);margin-bottom:2px;}
.brand-date{font-size:22px;font-weight:700;letter-spacing:-.02em;}
.brand-sub{font-size:13px;color:var(--muted);margin-top:1px;}
.header-badges{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
.badge{display:flex;align-items:center;gap:5px;background:var(--card);border:1px solid var(--border);border-radius:999px;padding:5px 10px;font-size:11px;color:var(--muted);}
.badge.ok{color:var(--teal);border-color:rgba(16,185,129,.3);background:rgba(16,185,129,.08);}
.badge.warn{color:var(--orange);border-color:rgba(249,115,22,.3);background:rgba(249,115,22,.08);}
.badge-dot{width:6px;height:6px;border-radius:50%;background:currentColor;}
.tabs{display:flex;gap:4px;margin-bottom:20px;background:var(--surface);padding:4px;border-radius:12px;border:1px solid var(--border);width:fit-content;}
.tab{border:none;background:transparent;border-radius:9px;padding:9px 18px;font-size:13px;font-weight:500;cursor:pointer;color:var(--muted);transition:all .2s ease;}
.tab:hover{color:var(--text);background:rgba(255,255,255,.05);}
.tab.active{background:var(--accent);color:#fff;font-weight:600;box-shadow:0 2px 8px rgba(99,102,241,.4);}
.section{display:none;}.section.active{display:block;}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow-sm);overflow:hidden;}
.card-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px 12px;border-bottom:1px solid var(--border);}
.card-title{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);}
.card-body{padding:16px;}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
.grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;}
.grid-main{display:grid;grid-template-columns:1fr 360px;gap:12px;align-items:start;}
.grid-perf{display:grid;grid-template-columns:1.2fr 1fr;gap:12px;}
.stack{display:flex;flex-direction:column;gap:12px;}
.stat-tile{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:18px;position:relative;overflow:hidden;transition:transform .15s ease;}
.stat-tile:hover{transform:translateY(-1px);box-shadow:var(--shadow);}
.stat-label{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:8px;}
.stat-value{font-size:36px;font-weight:800;letter-spacing:-.03em;line-height:1;font-variant-numeric:tabular-nums;}
.stat-unit{font-size:14px;font-weight:500;color:var(--muted);margin-left:4px;}
.stat-sub{font-size:12px;color:var(--muted);margin-top:6px;}
.stat-bar{height:3px;border-radius:2px;background:var(--border);margin-top:10px;overflow:hidden;}
.stat-bar-fill{height:100%;border-radius:2px;transition:width .8s ease;}
.stat-accent{position:absolute;top:0;right:0;width:3px;height:100%;}
.rec-card{border-radius:var(--radius-sm);padding:14px;border-left:4px solid;margin-bottom:8px;transition:transform .15s;}
.rec-card:hover{transform:translateX(2px);}
.rec-title{font-size:13px;font-weight:700;margin-bottom:4px;}
.rec-body{font-size:12px;color:var(--muted);line-height:1.5;margin-bottom:6px;}
.rec-action{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;opacity:.9;}
.chart-wrap{position:relative;}
.chart-title{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:12px;}
.activity-row{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border);}
.activity-row:last-child{border-bottom:none;}
.activity-icon{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;}
.activity-info{flex:1;min-width:0;}
.activity-name{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.activity-meta{font-size:11px;color:var(--muted);margin-top:2px;}
.activity-stat{font-size:13px;font-weight:700;color:var(--muted);text-align:right;flex-shrink:0;}
.week-nav{display:flex;align-items:center;gap:10px;}
.week-nav-btn{border:1px solid var(--border);background:var(--card2);border-radius:8px;padding:6px 10px;color:var(--muted);cursor:pointer;font-size:14px;transition:all .15s;}
.week-nav-btn:hover{color:var(--text);border-color:var(--accent);}
.week-label{font-size:13px;font-weight:600;color:var(--muted);}
.week-wrap{overflow-x:auto;margin-top:10px;}
.week-grid{display:grid;grid-template-columns:repeat(7,minmax(150px,1fr));gap:8px;min-width:1050px;}
.day-col{background:var(--surface);border:1px solid var(--border);border-radius:12px;min-height:220px;padding:8px;}
.day-col.today{border-color:rgba(99,102,241,.4);background:rgba(99,102,241,.06);}
.day-head{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--muted);margin-bottom:8px;}
.day-num{font-size:18px;font-weight:700;color:var(--text);}
.day-add-btn{border:none;background:rgba(99,102,241,.2);color:var(--accent2);border-radius:6px;font-size:11px;padding:2px 7px;cursor:pointer;}
.event{border-radius:8px;padding:7px 9px;margin-bottom:5px;border-left:3px solid;cursor:pointer;position:relative;transition:transform .12s ease;}
.event:hover{transform:translateX(2px);}
.event-title{font-size:11px;font-weight:600;line-height:1.3;}
.event-time{font-size:10px;opacity:.65;margin-top:2px;}
.event-x{position:absolute;top:4px;right:4px;border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:11px;opacity:0;transition:opacity .12s;}
.event:hover .event-x{opacity:1;}
.pred-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}
.pred-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px;text-align:center;}
.pred-dist{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);}
.pred-time{font-size:22px;font-weight:800;letter-spacing:-.02em;margin:4px 0 2px;}
.pred-pace{font-size:11px;color:var(--muted);}
.sport-row{display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid var(--border);}
.sport-row:last-child{border-bottom:none;}
.sport-bar-bg{height:4px;background:var(--border);border-radius:2px;overflow:hidden;flex:1;}
.sport-bar-fill{height:100%;border-radius:2px;}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;}
.modal-overlay.open{display:flex;}
.modal{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:24px;width:400px;box-shadow:var(--shadow);}
.modal h3{font-size:16px;font-weight:700;margin-bottom:16px;}
.form-group{margin-bottom:12px;}
.form-group label{display:block;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:6px;}
.form-group input,.form-group select,.form-group textarea{width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:9px 12px;font-size:13px;color:var(--text);font-family:inherit;}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:var(--accent);}
.btn-primary{background:var(--accent);color:#fff;border:none;border-radius:10px;padding:10px 20px;font-size:13px;font-weight:600;cursor:pointer;width:100%;transition:opacity .15s;}
.btn-primary:hover{opacity:.9;}
.btn-cancel{background:transparent;color:var(--muted);border:1px solid var(--border);border-radius:10px;padding:10px 20px;font-size:13px;cursor:pointer;margin-right:8px;}
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
.mt8{margin-top:8px;}.mt12{margin-top:12px;}.mt16{margin-top:16px;}.mb8{margin-bottom:8px;}
.flex-between{display:flex;justify-content:space-between;align-items:center;}
.text-muted{color:var(--muted);}.text-sm{font-size:12px;}
.divider{height:1px;background:var(--border);margin:12px 0;}
.tag{display:inline-flex;align-items:center;gap:4px;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:3px 8px;font-size:11px;font-weight:600;}
@media(max-width:1200px){.grid-4{grid-template-columns:repeat(2,1fr);}.grid-main{grid-template-columns:1fr;}.grid-perf{grid-template-columns:1fr;}}
@media(max-width:800px){.grid-3{grid-template-columns:1fr 1fr;}.pred-grid{grid-template-columns:repeat(2,1fr);}}
"""


def generate_html(
    training: dict,
    muscles: dict,
    metrics_history: list,
    daily_load_rows: list,
    output_path,
    api_token: str = "",
    sports_agent: dict | None = None,
) -> None:
    output_path = Path(output_path)
    today = date.today()
    today_str = today.strftime("%A %d %B %Y").capitalize()

    wakeboard = training.get("wakeboard", {})
    acwr = training.get("acwr", {})
    health = training.get("health", {})
    pilotage = training.get("pilotage", {})
    recent_activities = training.get("recent_activities", [])[:8]

    wbs = float(wakeboard.get("score", 0) or 0)
    wbs_label = wakeboard.get("label", "–")
    acwr_val = float(acwr.get("acwr", 0) or 0)
    acwr_zone = acwr.get("zone", "–")
    body_battery = float(health.get("body_battery") or _latest_metric(metrics_history, "body_battery", 0))
    rhr = float(health.get("rhr") or 0)
    sleep_h = float(health.get("sleep_h") or _latest_metric(metrics_history, "sleep_h", 0))
    steps = float(_latest_metric(metrics_history, "steps", 0))
    total_act = training.get("total_activities", 0)
    total_km = round(float(training.get("total_km", 0) or 0), 0)

    sources = training.get("sources", {}) or {}
    garmin_ok = bool(sources.get("garmin"))
    strava_ok = bool(sources.get("strava"))
    ah_ok = bool(sources.get("apple_health"))

    agent = sports_agent or {}
    agent_running = agent.get("running", {})
    agent_strength = agent.get("strength", {})
    agent_recovery = agent.get("recovery", {})
    agent_breakdown = agent.get("sport_breakdown", {})
    agent_recs = agent.get("recommendations", [])
    agent_weekly = agent.get("weekly_summary", {})

    rec_score = agent_recovery.get("score", int(wbs))
    rec_label = agent_recovery.get("label", wbs_label)
    rec_color = agent_recovery.get("color", "#6366f1")

    planner_events = _prepare_pilot_events(pilotage.get("events", []))
    planner_events_json = _jse(planner_events)

    pmc_labels, pmc_ctl, pmc_atl, pmc_tsb = [], [], [], []
    for r in daily_load_rows[-90:]:
        pmc_labels.append(str(r.get("date", "")))
        pmc_ctl.append(round(float(r.get("ctl") or 0), 2))
        pmc_atl.append(round(float(r.get("atl") or 0), 2))
        pmc_tsb.append(round(float(r.get("tsb") or 0), 2))

    recovery_data = agent_recovery.get("data", {})
    rhr_series = recovery_data.get("rhr", [])[-30:]
    battery_series = recovery_data.get("body_battery", [])[-30:]
    sleep_series = recovery_data.get("sleep", [])[-30:]

    run_monthly = agent_running.get("monthly", [])
    run_labels = [m.get("month", "") for m in run_monthly]
    run_km_vals = [m.get("km", 0) for m in run_monthly]

    sports_list = agent_breakdown.get("sports", [])[:8]
    predictions = agent_running.get("predictions", {})

    api_token_js = json.dumps(api_token, ensure_ascii=False)
    type_defs_js = _jse({k: {"icon": v["icon"], "color": v["color"]} for k, v in TYPE_DEFS.items()})

    # ─── Build HTML ───
    def color_rhr(v):
        return "#10b981" if v < 55 else "#fbbf24" if v < 65 else "#ef4444"

    def color_battery(v):
        return "#10b981" if v >= 60 else "#f97316" if v >= 30 else "#ef4444"

    def color_sleep(v):
        return "#10b981" if v >= 7.5 else "#fbbf24" if v >= 6 else "#ef4444"

    def color_acwr(v):
        return "#10b981" if 0.8 <= v <= 1.3 else "#f97316" if v <= 1.5 else "#ef4444"

    # Render recs
    recs_html = ""
    if agent_recs:
        for rec in agent_recs:
            sev = rec.get("severity", "info")
            col = SEVERITY_COLORS.get(sev, "#3b82f6")
            bg = SEVERITY_BG.get(sev, "rgba(59,130,246,0.1)")
            recs_html += (
                f'<div class="rec-card" style="background:{bg};border-color:{col};color:{col}">'
                f'<div class="rec-title">{escape(rec.get("icon",""))}&nbsp;{escape(rec.get("title",""))}</div>'
                f'<div class="rec-body">{escape(rec.get("body",""))}</div>'
                f'<div class="rec-action">→ {escape(rec.get("action",""))}</div>'
                f'</div>'
            )
    else:
        recs_html = '<p class="text-muted text-sm">Aucune recommandation urgente. Continue comme ça ! 💪</p>'

    # Render recent activities
    acts_html = ""
    for act in recent_activities:
        act_type = str(act.get("type", "Other"))
        act_name = str(act.get("name") or act_type)
        act_date_raw = str(act.get("started_at", ""))[:10]
        try:
            act_d = date.fromisoformat(act_date_raw)
            days_ago_n = (today - act_d).days
            date_label = "Auj." if days_ago_n == 0 else f"J-{days_ago_n}" if days_ago_n <= 30 else act_d.strftime("%d/%m")
        except Exception:
            date_label = act_date_raw
        dur_min = int((act.get("duration_s") or 0) / 60)
        dist_km = round((act.get("distance_m") or 0) / 1000, 1)
        icon = SPORT_ICONS.get(act_type, "🏅")
        sc = SPORT_COLORS.get(act_type, "#6b7280")
        meta = f"{dur_min}min" + (f" · {dist_km}km" if dist_km > 0 else "")
        hr_val = int(act.get("avg_hr") or 0)
        acts_html += (
            f'<div class="activity-row">'
            f'<div class="activity-icon" style="background:{sc}22">{icon}</div>'
            f'<div class="activity-info">'
            f'<div class="activity-name">{escape(act_name[:30])}</div>'
            f'<div class="activity-meta">{escape(date_label)} · {meta}</div>'
            f'</div>'
            f'<div class="activity-stat" style="color:{sc}">{hr_val if hr_val else "–"}'
            f'<br><span style="font-size:9px;opacity:.6">bpm</span></div>'
            f'</div>'
        )

    # Render weekly highlights
    highlights_html = ""
    for hl in agent_weekly.get("highlights", []):
        highlights_html += f'<div class="text-sm" style="padding:4px 0;border-bottom:1px solid var(--border);color:var(--muted)">• {escape(str(hl))}</div>\n'
    ready = agent_weekly.get("ready_to_train", True)
    ready_bg = "rgba(16,185,129,0.12)" if ready else "rgba(249,115,22,0.12)"
    ready_color = "#10b981" if ready else "#f97316"
    ready_text = "✅ Prêt à t'entraîner" if ready else "⚡ Récupération prioritaire"
    ready_html = (
        f'<div style="margin-top:12px;padding:10px;border-radius:8px;background:{ready_bg};text-align:center">'
        f'<span style="font-size:13px;font-weight:700;color:{ready_color}">{escape(ready_text)}</span>'
        f'</div>'
    )

    # Render predictions
    preds_html = ""
    race_labels_map = {"5km": "5 km", "10km": "10 km", "semi": "Semi", "marathon": "Marathon"}
    for race, pred in (predictions.items() if predictions else {}.items()):
        preds_html += (
            f'<div class="pred-card">'
            f'<div class="pred-dist">{escape(race_labels_map.get(race, race))}</div>'
            f'<div class="pred-time">{escape(str(pred.get("label","–")))}</div>'
            f'<div class="pred-pace">{escape(str(pred.get("pace_str","–")))}/km</div>'
            f'</div>'
        )
    if not preds_html:
        preds_html = '<p class="text-muted text-sm" style="grid-column:span 4;padding:8px 0">Données insuffisantes pour les prédictions</p>'

    # Render sport breakdown
    sports_rows_html = ""
    for sport in sports_list:
        sc = sport.get("color", "#6b7280")
        sports_rows_html += (
            f'<div class="sport-row">'
            f'<span style="font-size:16px">{escape(sport.get("icon","🏅"))}</span>'
            f'<div style="flex:1;min-width:0">'
            f'<div class="flex-between">'
            f'<span class="text-sm" style="font-weight:600">{escape(sport.get("type",""))}</span>'
            f'<span class="text-sm text-muted">{sport.get("sessions",0)}x · {sport.get("hours",0)}h</span>'
            f'</div>'
            f'<div class="sport-bar-bg mt8"><div class="sport-bar-fill" style="width:{sport.get("pct",0)}%;background:{sc}"></div></div>'
            f'</div>'
            f'</div>'
        )

    # Render strength sessions
    strength_html = ""
    for sess in agent_strength.get("recent_sessions", [])[:5]:
        strength_html += (
            f'<div class="activity-row">'
            f'<div class="activity-icon" style="background:rgba(139,92,246,.15)">🏋️</div>'
            f'<div class="activity-info">'
            f'<div class="activity-name">{escape(str(sess.get("name",""))[:28])}</div>'
            f'<div class="activity-meta">{escape(str(sess.get("date","")))} · {int(sess.get("duration_min",0))}min</div>'
            f'</div>'
            f'<div class="activity-stat" style="color:var(--purple)">{int(sess.get("calories",0) or 0)}'
            f'<br><span style="font-size:9px;opacity:.6">kcal</span></div>'
            f'</div>'
        )

    last_strength_days = agent_strength.get("last_session_days_ago", 0) or 0
    consistency = agent_running.get("consistency_score", 0)
    last_run_days = agent_running.get("last_run_days_ago", 999)

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>PerformOS · Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div class="app">

<div class="header">
  <div>
    <div class="brand-logo">PerformOS</div>
    <div class="brand-date">{escape(today_str)}</div>
    <div class="brand-sub">Sport Performance Intelligence · Simon Hingant</div>
  </div>
  <div class="header-badges">
    {'<span class="badge ok"><span class="badge-dot"></span>Garmin</span>' if garmin_ok else '<span class="badge warn"><span class="badge-dot"></span>Garmin offline</span>'}
    {'<span class="badge ok"><span class="badge-dot"></span>Strava</span>' if strava_ok else ''}
    {'<span class="badge ok"><span class="badge-dot"></span>Apple Health</span>' if ah_ok else ''}
    <span class="badge"><span class="badge-dot" style="background:var(--accent)"></span>{total_act} activités</span>
    <span class="badge">🔄 <span id="sync-time">{datetime.now().strftime("%H:%M")}</span></span>
  </div>
</div>

<div class="tabs">
  <button class="tab active" onclick="showTab('today',this)">Aujourd'hui</button>
  <button class="tab" onclick="showTab('sport',this)">⚡ Performance</button>
  <button class="tab" onclick="showTab('recovery',this)">🫀 Récupération</button>
  <button class="tab" onclick="showTab('plan',this)">📅 Planning</button>
</div>

<!-- ═══ TODAY ═══ -->
<div id="tab-today" class="section active">
  <div class="grid-4 mb8" style="margin-bottom:12px">

    <div class="stat-tile" style="text-align:center;padding:24px 16px">
      <div class="stat-label" style="margin-bottom:12px">Readiness</div>
      {_ring_svg(rec_score, 100, rec_color, size=110)}
      <div style="margin-top:12px">
        <div class="stat-value" style="font-size:28px;color:{rec_color}">{rec_score}<span class="stat-unit">/100</span></div>
        <div class="stat-sub">{escape(rec_label)}</div>
      </div>
      <div class="stat-accent" style="background:{rec_color}"></div>
    </div>

    <div class="stat-tile">
      <div class="stat-label">⚡ Body Battery</div>
      <div class="stat-value" style="color:{color_battery(body_battery)}">{int(body_battery)}</div>
      <div class="stat-sub">sur 100 · Garmin live</div>
      <div class="stat-bar mt8"><div class="stat-bar-fill" style="width:{min(100,body_battery)}%;background:{color_battery(body_battery)}"></div></div>
      <div class="stat-accent" style="background:{color_battery(body_battery)}"></div>
    </div>

    <div class="stat-tile">
      <div class="stat-label">❤️ FC Repos</div>
      <div class="stat-value" style="color:{color_rhr(rhr)}">{int(rhr)}<span class="stat-unit">bpm</span></div>
      <div class="stat-sub">{"Excellent" if rhr < 52 else "Normal" if rhr < 62 else "Élevé"} · Garmin</div>
      <div class="stat-bar mt8"><div class="stat-bar-fill" style="width:{min(100,max(0,(80-rhr)/40*100)):.0f}%;background:{color_rhr(rhr)}"></div></div>
      <div class="stat-accent" style="background:{color_rhr(rhr)}"></div>
    </div>

    <div class="stat-tile">
      <div class="stat-label">😴 Sommeil</div>
      <div class="stat-value" style="color:{color_sleep(sleep_h)}">{round(sleep_h,1)}<span class="stat-unit">h</span></div>
      <div class="stat-sub">{"Optimal" if sleep_h >= 7.5 else "Suffisant" if sleep_h >= 6 else "Insuffisant"}</div>
      <div class="stat-bar mt8"><div class="stat-bar-fill" style="width:{min(100,sleep_h/9*100):.0f}%;background:{color_sleep(sleep_h)}"></div></div>
      <div class="stat-accent" style="background:{color_sleep(sleep_h)}"></div>
    </div>
  </div>

  <div class="grid-main">
    <div class="stack">
      <div class="card">
        <div class="card-header">
          <span class="card-title">🤖 Analyse IA · Recommandations</span>
          <span class="tag">{len(agent_recs)} insights</span>
        </div>
        <div class="card-body">{recs_html}</div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header"><span class="card-title">📈 ACWR · Charge</span></div>
          <div class="card-body">
            <div style="text-align:center;padding:12px 0">
              <div class="stat-value" style="font-size:52px;color:{color_acwr(acwr_val)}">{round(acwr_val,2)}</div>
              <div style="font-size:14px;font-weight:600;color:{color_acwr(acwr_val)};margin-top:4px">Zone {escape(acwr_zone)}</div>
              <div class="stat-sub">Optimal : 0.8 – 1.3</div>
            </div>
            <div class="stat-bar"><div class="stat-bar-fill" style="width:{min(100,acwr_val/2*100):.0f}%;background:{color_acwr(acwr_val)}"></div></div>
          </div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">👟 Activité</span></div>
          <div class="card-body">
            <div style="text-align:center;padding:8px 0">
              <div class="stat-value" style="font-size:36px;color:{"#10b981" if steps>=8000 else "#fbbf24"}">{int(steps):,}</div>
              <div class="stat-sub">pas · cible 8 000</div>
              <div class="stat-bar mt8"><div class="stat-bar-fill" style="width:{min(100,steps/8000*100):.0f}%;background:var(--teal)"></div></div>
            </div>
            <div class="divider"></div>
            <div class="flex-between"><span class="text-sm text-muted">Total activités</span><span class="text-sm" style="font-weight:700">{total_act}</span></div>
            <div class="flex-between mt8"><span class="text-sm text-muted">Kilomètres</span><span class="text-sm" style="font-weight:700">{int(total_km)} km</span></div>
          </div>
        </div>
      </div>
    </div>

    <div class="stack">
      <div class="card">
        <div class="card-header"><span class="card-title">🏅 Dernières séances</span></div>
        <div class="card-body" style="padding:8px 16px">{acts_html}</div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">📊 Bilan semaine</span></div>
        <div class="card-body">
          <div class="text-sm" style="color:var(--accent2);font-weight:700;margin-bottom:8px">{escape(agent_weekly.get("week",""))}</div>
          {highlights_html}
          {ready_html}
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ PERFORMANCE ═══ -->
<div id="tab-sport" class="section">
  <div class="stack">
    <div class="card">
      <div class="card-header">
        <span class="card-title">🏃 Running · 12 mois</span>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <span class="tag">🏁 {agent_running.get("total_km",0)} km</span>
          <span class="tag">📊 {agent_running.get("sessions",0)} sorties</span>
          <span class="tag">⚡ {escape(str(agent_running.get("recent_pace_str","–")))}/km</span>
          <span class="tag">🏆 Best: {escape(str(agent_running.get("best_pace_str","–")))}/km</span>
        </div>
      </div>
      <div class="card-body">
        <div class="grid-perf" style="gap:20px">
          <div>
            <div class="chart-title">Volume mensuel (km)</div>
            <div class="chart-wrap"><canvas id="chartRunKm" height="180"></canvas></div>
          </div>
          <div>
            <div class="chart-title">Prédictions de course</div>
            <div class="pred-grid" style="margin-top:4px">{preds_html}</div>
            <div class="divider"></div>
            <div class="flex-between"><span class="text-sm text-muted">Régularité</span><span class="text-sm" style="font-weight:700;color:{"#10b981" if consistency>=70 else "#fbbf24" if consistency>=40 else "#ef4444"}">{consistency}/100</span></div>
            <div class="stat-bar mt8"><div class="stat-bar-fill" style="width:{consistency}%;background:{"#10b981" if consistency>=70 else "#fbbf24"}"></div></div>
            <div class="flex-between mt8"><span class="text-sm text-muted">Dernière sortie</span><span class="text-sm" style="font-weight:700">Il y a {last_run_days}j</span></div>
            <div class="flex-between mt8"><span class="text-sm text-muted">Tendance allure</span><span style="font-size:18px">{escape(str(agent_running.get("pace_trend","→")))}</span></div>
          </div>
        </div>
      </div>
    </div>

    <div class="grid-perf">
      <div class="card">
        <div class="card-header">
          <span class="card-title">🎯 Répartition sports · 12 mois</span>
          <span class="tag">{agent_breakdown.get("total_sessions",0)} séances</span>
        </div>
        <div class="card-body">
          <div style="max-width:180px;margin:0 auto 16px"><canvas id="chartSportDonut" height="180"></canvas></div>
          {sports_rows_html}
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <span class="card-title">🏋️ Musculation</span>
          <div style="display:flex;gap:8px">
            <span class="tag">{agent_strength.get("sessions",0)} séances</span>
            <span class="tag">{agent_strength.get("avg_per_week",0)}x/sem</span>
          </div>
        </div>
        <div class="card-body">
          <div class="flex-between" style="margin-bottom:12px">
            <div><div class="stat-label">Dernière séance</div>
            <div class="stat-value" style="font-size:28px;color:{"#10b981" if last_strength_days<=4 else "#f97316"}">{last_strength_days}j</div></div>
            <div><div class="stat-label">Gap moyen</div>
            <div class="stat-value" style="font-size:28px">{agent_strength.get("avg_gap_days","–")}<span class="stat-unit">j</span></div></div>
            <div><div class="stat-label">Récup.</div><div style="font-size:28px">{"✅" if last_strength_days >= 2 else "⚠️"}</div></div>
          </div>
          <div class="divider"></div>
          {strength_html}
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ RÉCUPÉRATION ═══ -->
<div id="tab-recovery" class="section">
  <div class="stack">
    <div class="card">
      <div class="card-header">
        <span class="card-title">📈 Performance Management Chart · 90 jours</span>
        <div style="display:flex;gap:12px">
          <span class="tag" style="color:#6366f1">━ CTL Forme</span>
          <span class="tag" style="color:#f97316">━ ATL Fatigue</span>
          <span class="tag" style="color:#10b981">— TSB Fraîcheur</span>
        </div>
      </div>
      <div class="card-body"><div class="chart-wrap"><canvas id="chartPMC" height="160"></canvas></div></div>
    </div>
    <div class="grid-3">
      <div class="card">
        <div class="card-header"><span class="card-title">❤️ FC Repos · 30j</span></div>
        <div class="card-body">
          <div class="flex-between mb8">
            <div><div class="stat-value" style="font-size:32px">{int(rhr)}<span class="stat-unit">bpm</span></div><div class="stat-sub">Aujourd'hui</div></div>
            <div style="text-align:right"><div class="text-sm text-muted">Moy 30j</div><div style="font-size:16px;font-weight:700">{round(float(agent_recovery.get("averages",{}).get("rhr") or rhr),0):.0f} bpm</div></div>
          </div>
          <canvas id="chartRHR" height="80"></canvas>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">⚡ Body Battery · 30j</span></div>
        <div class="card-body">
          <div class="flex-between mb8">
            <div><div class="stat-value" style="font-size:32px;color:{color_battery(body_battery)}">{int(body_battery)}<span class="stat-unit">/100</span></div><div class="stat-sub">Aujourd'hui</div></div>
            <div style="text-align:right"><div class="text-sm text-muted">Moy 30j</div><div style="font-size:16px;font-weight:700">{round(float(agent_recovery.get("averages",{}).get("body_battery") or body_battery),0):.0f}</div></div>
          </div>
          <canvas id="chartBattery" height="80"></canvas>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">😴 Sommeil · 30j</span></div>
        <div class="card-body">
          <div class="flex-between mb8">
            <div><div class="stat-value" style="font-size:32px">{round(sleep_h,1)}<span class="stat-unit">h</span></div><div class="stat-sub">Hier soir</div></div>
            <div style="text-align:right"><div class="text-sm text-muted">Moy 30j</div><div style="font-size:16px;font-weight:700">{round(float(agent_recovery.get("averages",{}).get("sleep_h") or sleep_h),1)} h</div></div>
          </div>
          <canvas id="chartSleep" height="80"></canvas>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ PLANNING ═══ -->
<div id="tab-plan" class="section">
  <div class="card">
    <div class="card-header">
      <div class="week-nav">
        <button class="week-nav-btn" onclick="prevWeek()">‹</button>
        <span class="week-label" id="weekLabel"></span>
        <button class="week-nav-btn" onclick="nextWeek()">›</button>
        <button class="week-nav-btn" onclick="goToday()" style="font-size:11px;padding:6px 12px">Auj.</button>
      </div>
      <button onclick="openModal()" style="background:var(--accent);color:#fff;border:none;border-radius:10px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer">+ Ajouter</button>
    </div>
    <div class="card-body">
      <div class="week-wrap"><div class="week-grid" id="weekGrid"></div></div>
    </div>
  </div>
</div>

</div>

<div class="modal-overlay" id="modalOverlay">
  <div class="modal">
    <h3>➕ Nouvelle activité</h3>
    <div class="form-group"><label>Titre</label><input type="text" id="formTitle" placeholder="Ex: Run 10km tempo"></div>
    <div class="form-group"><label>Type</label>
      <select id="formType">
        <option value="cardio">🏃 Cardio</option><option value="musculation">🏋️ Musculation</option>
        <option value="mobilite">🧘 Mobilité</option><option value="sport_libre">🎾 Sport libre</option>
        <option value="travail">💼 Travail</option><option value="apprentissage">📚 Apprentissage</option>
        <option value="relationnel">💬 Relationnel</option><option value="autre">🧩 Autre</option>
      </select>
    </div>
    <div class="form-group"><label>Date</label><input type="date" id="formDate"></div>
    <div class="form-group"><label>Heure</label><input type="time" id="formTime" value="09:00"></div>
    <div class="form-group"><label>Durée (min)</label><input type="number" id="formDuration" value="60" min="5" max="480"></div>
    <div class="form-group"><label>Notes</label><textarea id="formNotes" rows="2" placeholder="Optionnel"></textarea></div>
    <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
      <button class="btn-cancel" onclick="closeModal()">Annuler</button>
      <button class="btn-primary" onclick="submitTask()">Ajouter</button>
    </div>
  </div>
</div>

<script>
const API_BASE = 'http://127.0.0.1:8765';
const API_TOKEN = {api_token_js};
const TODAY = new Date().toISOString().slice(0,10);
let currentWeekOffset = 0;
let allEvents = {planner_events_json};

function showTab(name, btn) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (btn) btn.classList.add('active');
}}

Chart.defaults.color = '#7b8eb0';
Chart.defaults.borderColor = 'rgba(255,255,255,0.07)';
Chart.defaults.font.family = "-apple-system,BlinkMacSystemFont,'SF Pro Text',Inter,system-ui,sans-serif";
Chart.defaults.font.size = 11;

(function() {{
  const labels = {_jse(pmc_labels)};
  const ctlData = {_jse(pmc_ctl)};
  const atlData = {_jse(pmc_atl)};
  const tsbData = {_jse(pmc_tsb)};
  if (!labels.length) return;
  new Chart(document.getElementById('chartPMC').getContext('2d'), {{
    type:'line',
    data:{{ labels, datasets:[
      {{label:'CTL Forme', data:ctlData, borderColor:'#6366f1', backgroundColor:'rgba(99,102,241,0.08)', borderWidth:2.5, tension:0.4, fill:true, pointRadius:0}},
      {{label:'ATL Fatigue', data:atlData, borderColor:'#f97316', backgroundColor:'rgba(249,115,22,0.06)', borderWidth:2, tension:0.4, fill:true, pointRadius:0}},
      {{label:'TSB Fraîcheur', data:tsbData, borderColor:'#10b981', backgroundColor:'transparent', borderWidth:1.5, tension:0.4, fill:false, pointRadius:0, borderDash:[4,3]}}
    ]}},
    options:{{ responsive:true, interaction:{{mode:'index',intersect:false}},
      plugins:{{legend:{{position:'top',labels:{{boxWidth:12,padding:16}}}}}},
      scales:{{x:{{ticks:{{maxTicksLimit:8}},grid:{{color:'rgba(255,255,255,0.04)'}}}},y:{{ticks:{{maxTicksLimit:6}},grid:{{color:'rgba(255,255,255,0.04)'}}}}}}
    }}
  }});
}})();

(function() {{
  const labels = {_jse(run_labels)};
  const km = {_jse(run_km_vals)};
  if (!labels.length) return;
  new Chart(document.getElementById('chartRunKm').getContext('2d'), {{
    type:'bar',
    data:{{labels,datasets:[{{label:'km',data:km,backgroundColor:'rgba(249,115,22,0.75)',borderRadius:6,borderSkipped:false}}]}},
    options:{{responsive:true,plugins:{{legend:{{display:false}}}},
      scales:{{x:{{ticks:{{maxTicksLimit:8}},grid:{{display:false}}}},y:{{ticks:{{maxTicksLimit:5}},grid:{{color:'rgba(255,255,255,0.04)'}}}}}}
    }}
  }});
}})();

(function() {{
  const sports = {_jse([{"label": s.get("type","")[:12], "sessions": s.get("sessions",0), "color": s.get("color","#6b7280")} for s in sports_list[:6]])};
  if (!sports.length) return;
  new Chart(document.getElementById('chartSportDonut').getContext('2d'), {{
    type:'doughnut',
    data:{{labels:sports.map(s=>s.label),datasets:[{{data:sports.map(s=>s.sessions),backgroundColor:sports.map(s=>s.color),borderWidth:0,hoverOffset:4}}]}},
    options:{{responsive:true,cutout:'70%',plugins:{{legend:{{display:false}}}}}}
  }});
}})();

function miniLine(id, labels, data, color) {{
  const el = document.getElementById(id);
  if (!el || !data.length) return;
  new Chart(el.getContext('2d'), {{
    type:'line',
    data:{{labels,datasets:[{{data,borderColor:color,backgroundColor:color+'22',borderWidth:2,tension:0.4,fill:true,pointRadius:0}}]}},
    options:{{responsive:true,plugins:{{legend:{{display:false}},tooltip:{{enabled:false}}}},scales:{{x:{{display:false}},y:{{display:false}}}}}}
  }});
}}
miniLine('chartRHR', {_jse([r["date"] for r in rhr_series])}, {_jse([r["value"] for r in rhr_series])}, '#ef4444');
miniLine('chartBattery', {_jse([r["date"] for r in battery_series])}, {_jse([r["value"] for r in battery_series])}, '#10b981');
miniLine('chartSleep', {_jse([r["date"] for r in sleep_series])}, {_jse([r["value"] for r in sleep_series])}, '#6366f1');

const DAYS_FR = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];
const MONTHS_FR = ['jan','fév','mar','avr','mai','jun','jul','aoû','sep','oct','nov','déc'];
const TYPE_DEFS_JS = {type_defs_js};

function getWeekDates(offset) {{
  const now = new Date();
  const monday = new Date(now);
  monday.setDate(now.getDate() - (now.getDay()||7) + 1 + offset*7);
  return Array.from({{length:7}}, (_,i) => {{ const d = new Date(monday); d.setDate(monday.getDate()+i); return d; }});
}}

function renderWeek() {{
  const dates = getWeekDates(currentWeekOffset);
  const f = dates[0], l = dates[6];
  document.getElementById('weekLabel').textContent =
    DAYS_FR[0]+' '+f.getDate()+' '+MONTHS_FR[f.getMonth()]+' – '+DAYS_FR[6]+' '+l.getDate()+' '+MONTHS_FR[l.getMonth()];
  const grid = document.getElementById('weekGrid');
  grid.innerHTML = '';
  dates.forEach(d => {{
    const iso = d.toISOString().slice(0,10);
    const isToday = iso === TODAY;
    const col = document.createElement('div');
    col.className = 'day-col' + (isToday?' today':'');
    col.dataset.date = iso;
    col.addEventListener('dragover', e => {{ e.preventDefault(); col.style.background='rgba(99,102,241,0.15)'; }});
    col.addEventListener('dragleave', () => col.style.background='');
    col.addEventListener('drop', e => {{ e.preventDefault(); col.style.background=''; dropEvent(e,iso); }});
    const head = document.createElement('div');
    head.className = 'day-head';
    head.innerHTML = `<span>${{DAYS_FR[d.getDay()==0?6:d.getDay()-1]}}</span>
      <span class="day-num" style="${{isToday?'color:var(--accent)':''}}">${{d.getDate()}}</span>`;
    const addBtn = document.createElement('button');
    addBtn.className = 'day-add-btn';
    addBtn.textContent='+';
    addBtn.onclick = () => openModalDate(iso);
    head.appendChild(addBtn);
    col.appendChild(head);
    allEvents.filter(ev => ev.start_at && ev.start_at.slice(0,10)===iso).forEach(ev => col.appendChild(buildEventEl(ev)));
    grid.appendChild(col);
  }});
}}

function buildEventEl(ev) {{
  const div = document.createElement('div');
  div.className='event'; div.dataset.id=ev.id; div.draggable=true;
  div.style.borderColor=ev.color; div.style.background=ev.color+'18';
  const time = ev.start_at ? ev.start_at.slice(11,16) : '';
  div.innerHTML = `<button class="event-x" onclick="deleteEvent('${{ev.id}}',event)">×</button>
    <div class="event-title">${{ev.icon}} ${{escHtml(ev.title)}}</div>
    ${{time ? `<div class="event-time">${{time}}</div>` : ''}}`;
  div.addEventListener('dragstart', e => {{ e.dataTransfer.setData('eventId',ev.id); div.classList.add('dragging'); }});
  div.addEventListener('dragend', () => div.classList.remove('dragging'));
  return div;
}}

function escHtml(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
function prevWeek() {{ currentWeekOffset--; renderWeek(); }}
function nextWeek() {{ currentWeekOffset++; renderWeek(); }}
function goToday() {{ currentWeekOffset=0; renderWeek(); }}

async function dropEvent(e, newDate) {{
  const id = e.dataTransfer.getData('eventId');
  const ev = allEvents.find(x => x.id==id);
  if (!ev || !ev.start_at) return;
  const startOld = new Date(ev.start_at), endOld = new Date(ev.end_at||ev.start_at);
  const dur = endOld - startOld;
  const newStart = new Date(newDate+'T'+(ev.start_at.slice(11,19)||'09:00:00'));
  const newEnd = new Date(newStart.getTime()+dur);
  ev.start_at = newStart.toISOString().slice(0,19);
  ev.end_at = newEnd.toISOString().slice(0,19);
  renderWeek();
  if (id && !String(id).startsWith('apple_')) {{
    try {{ await apiFetch('PATCH',`/api/planner/tasks/${{id}}`,{{start_at:ev.start_at,end_at:ev.end_at}}); }} catch(e) {{}}
  }}
}}

let _modalDate = null;
function openModal() {{ _modalDate=null; document.getElementById('formDate').value=TODAY; document.getElementById('modalOverlay').classList.add('open'); }}
function openModalDate(d) {{ _modalDate=d; document.getElementById('formDate').value=d; document.getElementById('modalOverlay').classList.add('open'); }}
function closeModal() {{ document.getElementById('modalOverlay').classList.remove('open'); }}

async function submitTask() {{
  const title = document.getElementById('formTitle').value.trim()||'Activité';
  const type = document.getElementById('formType').value;
  const taskDate = document.getElementById('formDate').value;
  const taskTime = document.getElementById('formTime').value||'09:00';
  const duration = parseInt(document.getElementById('formDuration').value)||60;
  const notes = document.getElementById('formNotes').value;
  try {{
    const res = await apiFetch('POST','/api/planner/tasks',{{title,type,task_date:taskDate,task_time:taskTime+':00',duration_min:duration,notes,sync_apple:true}});
    if (res.events) {{ allEvents=res.events.map(prepareEvent); renderWeek(); }}
    closeModal();
  }} catch(e) {{ alert('Erreur: '+e.message); }}
}}

async function deleteEvent(id, e) {{
  e.stopPropagation();
  if (!confirm('Supprimer ?')) return;
  allEvents = allEvents.filter(ev => ev.id!=id);
  renderWeek();
  if (id && !String(id).startsWith('apple_')) {{
    try {{ await apiFetch('DELETE',`/api/planner/tasks/${{id}}`); }} catch(e) {{}}
  }}
}}

function prepareEvent(ev) {{
  const t = ev.type||'autre';
  const d = TYPE_DEFS_JS[t]||TYPE_DEFS_JS['autre'];
  return {{...ev, icon:ev.icon||d.icon, color:ev.color||d.color}};
}}

async function apiFetch(method, path, body) {{
  const headers = {{'Content-Type':'application/json'}};
  if (API_TOKEN) headers['X-PerformOS-Token'] = API_TOKEN;
  const res = await fetch(API_BASE+path,{{method,headers,body:body?JSON.stringify(body):undefined}});
  if (!res.ok) throw new Error('HTTP '+res.status);
  return res.json();
}}

async function loadEvents() {{
  try {{
    const res = await apiFetch('GET','/api/planner/events');
    if (res.events) {{ allEvents=res.events.map(prepareEvent); renderWeek(); }}
  }} catch(e) {{ renderWeek(); }}
}}

document.addEventListener('DOMContentLoaded', () => {{
  renderWeek();
  loadEvents();
  setInterval(() => {{ const el=document.getElementById('sync-time'); if(el) el.textContent=new Date().toTimeString().slice(0,5); }}, 60000);
}});
</script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
