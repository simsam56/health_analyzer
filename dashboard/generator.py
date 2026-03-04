"""
generator.py — PerformOS v3 Dashboard
Design inspiré de Whoop / Oura Ring / Garmin Connect
Dark, mobile-first, navigation multi-section, animations
"""
from pathlib import Path
from datetime import date, datetime
import json
import math


# ─── Palettes ────────────────────────────────────────────────────
C = {
    "bg":      "#0a0a0f",
    "card":    "#12121a",
    "card2":   "#1a1a26",
    "border":  "#2a2a3a",
    "text":    "#e8e8f0",
    "muted":   "#9fa4bf",
    "accent":  "#4aa8ff",
    "green":   "#30d158",
    "orange":  "#ff9f0a",
    "red":     "#ff453a",
    "purple":  "#a78bfa",
    "teal":    "#32ade6",
    "pink":    "#ff375f",
    "yellow":  "#ffd60a",
}

MUSCLE_COLORS = {
    "Pecs":    "#ff6b6b",
    "Dos":     "#4ecdc4",
    "Épaules": "#45b7d1",
    "Biceps":  "#f9c74f",
    "Triceps": "#90be6d",
    "Jambes":  "#f8961e",
    "Core":    "#bf5af2",
}

CATEGORY_COLORS = {
    "sante": "#30d158",
    "travail": "#4aa8ff",
    "relationnel": "#ff9f0a",
    "apprentissage": "#a78bfa",
    "autre": "#9fa4bf",
}


# ─── Composants SVG ──────────────────────────────────────────────
def ring_svg(value: float, max_val: float, color: str, size: int = 120,
             stroke: int = 12, label: str = "", sublabel: str = "") -> str:
    pct  = min(max(value / max_val, 0), 1) if max_val else 0
    r    = (size - stroke) / 2
    circ = 2 * math.pi * r
    dash = pct * circ
    cx = cy = size / 2
    val_str = f"{value:.0f}" if value == int(value) else f"{value:.1f}"
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{C['card2']}" stroke-width="{stroke}"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}"
    stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"
    transform="rotate(-90 {cx} {cy})"
    style="transition:stroke-dasharray 1s ease"/>
  <text x="{cx}" y="{cy - 4}" text-anchor="middle" fill="{C['text']}" font-size="20" font-weight="700" font-family="Space Grotesk,Avenir Next,sans-serif">{val_str}</text>
  <text x="{cx}" y="{cy + 14}" text-anchor="middle" fill="{C['muted']}" font-size="10" font-family="Space Grotesk,Avenir Next,sans-serif">{label}</text>
  {f'<text x="{cx}" y="{cy + 26}" text-anchor="middle" fill="{C["muted"]}" font-size="9" font-family="Space Grotesk,Avenir Next,sans-serif">{sublabel}</text>' if sublabel else ''}
</svg>"""


def spark_svg(values: list[float], color: str, w: int = 160, h: int = 40) -> str:
    """Mini sparkline chart."""
    if not values or all(v == 0 for v in values):
        return f'<svg width="{w}" height="{h}"></svg>'
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    pts = []
    for i, v in enumerate(values):
        x = i / max(len(values) - 1, 1) * w
        y = h - (v - mn) / rng * (h - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    path = " L ".join(pts)
    # Fill gradient
    fill_pts = f"0,{h} " + " ".join(pts) + f" {w},{h}"
    return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <linearGradient id="sg{abs(hash(color))%9999}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0.0"/>
    </linearGradient>
  </defs>
  <polygon points="{fill_pts}" fill="url(#sg{abs(hash(color))%9999})"/>
  <polyline points="{' '.join(pts)}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


def bar_chart_svg(labels: list[str], values: list[float], targets: list[float],
                  colors: list[str], w: int = 320, h: int = 160) -> str:
    if not values:
        return ""
    n = len(values)
    bar_w = (w - 40) / n
    max_val = max(max(values), max(targets)) * 1.1 or 1
    svg_bars = []
    for i, (lbl, val, tgt, col) in enumerate(zip(labels, values, targets, colors)):
        x = 20 + i * bar_w + bar_w * 0.1
        bw = bar_w * 0.75
        bh = (val / max_val) * (h - 30)
        th = (tgt / max_val) * (h - 30)
        by = h - 20 - bh
        pct = min(val / tgt, 1) if tgt > 0 else 0
        svg_bars.append(f"""
    <rect x="{x:.1f}" y="{h-20-th:.1f}" width="{bw:.1f}" height="{th:.1f}" fill="{col}" opacity="0.15" rx="3"/>
    <rect x="{x:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{col}" opacity="0.85" rx="3"/>
    <text x="{x+bw/2:.1f}" y="{by-4:.1f}" text-anchor="middle" fill="{col}" font-size="9" font-family="Space Grotesk,Avenir Next,sans-serif">{val:.0f}</text>
    <text x="{x+bw/2:.1f}" y="{h-6:.1f}" text-anchor="middle" fill="{C['muted']}" font-size="8" font-family="Space Grotesk,Avenir Next,sans-serif">{lbl[:4]}</text>
""")
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(svg_bars)}</svg>'


def pmc_chart_svg(daily_load: list[dict], w: int = 340, h: int = 120) -> str:
    """PMC (Performance Management Chart) : CTL, ATL, TSB."""
    if not daily_load:
        return ""
    # Last 90 days
    data = daily_load[-90:] if len(daily_load) > 90 else daily_load
    dates = [d.get("date", "") for d in data]
    ctl   = [d.get("ctl", 0) or 0 for d in data]
    atl   = [d.get("atl", 0) or 0 for d in data]
    tsb   = [d.get("tsb", 0) or 0 for d in data]

    all_vals = ctl + atl + tsb
    mn, mx = min(all_vals), max(all_vals)
    rng = mx - mn or 1
    n = len(data)
    if n < 2:
        return ""

    def to_pts(series):
        pts = []
        for i, v in enumerate(series):
            x = 10 + i / (n - 1) * (w - 20)
            y = h - 10 - (v - mn) / rng * (h - 20)
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)

    ctl_pts = to_pts(ctl)
    atl_pts = to_pts(atl)
    tsb_pts = to_pts(tsb)

    return f"""<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <polyline points="{ctl_pts}" fill="none" stroke="{C['teal']}" stroke-width="2" stroke-linecap="round"/>
  <polyline points="{atl_pts}" fill="none" stroke="{C['orange']}" stroke-width="2" stroke-linecap="round"/>
  <polyline points="{tsb_pts}" fill="none" stroke="{C['purple']}" stroke-width="1.5" stroke-dasharray="4 2"/>
  <text x="8" y="12" fill="{C['teal']}" font-size="9" font-family="Space Grotesk,Avenir Next,sans-serif">CTL</text>
  <text x="30" y="12" fill="{C['orange']}" font-size="9" font-family="Space Grotesk,Avenir Next,sans-serif">ATL</text>
  <text x="52" y="12" fill="{C['purple']}" font-size="9" font-family="Space Grotesk,Avenir Next,sans-serif">TSB</text>
</svg>"""


# ─── Helpers ─────────────────────────────────────────────────────
def color_for_score(score: float) -> str:
    if score >= 75:   return C["green"]
    if score >= 50:   return C["orange"]
    return C["red"]


def color_for_acwr(acwr: float) -> str:
    if 0.8 <= acwr <= 1.3: return C["green"]
    if 0.6 <= acwr <= 1.5: return C["orange"]
    return C["red"]


def safe(d: dict, *keys, default=0):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d or default


def normalize_muscle_name(name: str) -> str:
    return "Épaules" if name == "Epaules" else name


def source_range(data_quality: dict, source: str) -> str:
    ranges = data_quality.get("activity_by_source", []) if isinstance(data_quality, dict) else []
    for row in ranges:
        if row.get("source") == source:
            first_date = row.get("first_date")
            last_date = row.get("last_date")
            if first_date and last_date:
                return f"{first_date} → {last_date}"
    return "Données indisponibles"


def category_label(cat: str) -> str:
    labels = {
        "sante": "Santé",
        "travail": "Travail",
        "relationnel": "Relationnel",
        "apprentissage": "Apprentissage",
        "autre": "Autre",
    }
    return labels.get(cat, "Autre")


def metric_val(metrics_history: list[dict], metric: str, days: int = 7) -> float:
    """Dernière valeur connue d'une métrique dans l'historique."""
    relevant = [m for m in metrics_history if m.get("metric") == metric and m.get("value")]
    if not relevant:
        return 0.0
    return float(relevant[-1]["value"])


def last_n(metrics_history: list[dict], metric: str, n: int = 30) -> list[float]:
    relevant = sorted(
        [m for m in metrics_history if m.get("metric") == metric and m.get("value")],
        key=lambda x: x.get("date", "")
    )
    return [float(m["value"]) for m in relevant[-n:]]


# ─── Génération HTML principale ──────────────────────────────────
def generate_html(
    training: dict,
    muscles: dict,
    metrics_history: list[dict],
    daily_load_rows: list[dict],
    output_path: str | Path,
) -> None:
    today = date.today().strftime("%d/%m/%Y")
    now   = datetime.now().strftime("%H:%M")

    # ── Données training ─────────────────────────────────────────
    wbs      = training.get("wakeboard", {})
    acwr_d   = training.get("acwr", {})
    pmc      = training.get("pmc", {})
    running  = training.get("running", {})
    data_quality = training.get("data_quality", {})
    agenda_events = training.get("agenda_events", [])
    calendar_sync = training.get("calendar_sync", {})
    pilotage = training.get("pilotage", {})

    wbs_score = float(wbs.get("score", 0) or 0)
    wbs_label = wbs.get("label", "—")
    wbs_color = color_for_score(wbs_score)

    acwr_val   = float(acwr_d.get("acwr", 0) or 0)
    acwr_zone  = acwr_d.get("zone", "—")
    acwr_color = color_for_acwr(acwr_val)

    ctl = float(pmc.get("ctl", 0) or 0)
    atl = float(pmc.get("atl", 0) or 0)
    tsb = float(pmc.get("tsb", 0) or 0)

    # ── Métriques santé ──────────────────────────────────────────
    hrv_val    = metric_val(metrics_history, "hrv_sdnn")
    rhr_val    = metric_val(metrics_history, "rhr")
    sleep_val  = metric_val(metrics_history, "sleep_h")
    steps_val  = metric_val(metrics_history, "steps")
    active_cal = metric_val(metrics_history, "active_cal")
    flights    = metric_val(metrics_history, "flights")
    batt_val   = metric_val(metrics_history, "body_battery")
    stress_val = metric_val(metrics_history, "stress_avg")

    hrv_hist   = last_n(metrics_history, "hrv_sdnn", 30)
    rhr_hist   = last_n(metrics_history, "rhr", 30)
    sleep_hist = last_n(metrics_history, "sleep_h", 30)
    steps_hist = last_n(metrics_history, "steps", 14)

    # ── Musculation ───────────────────────────────────────────────
    muscle_score = muscles.get("muscle_score", 0)
    muscle_color = color_for_score(muscle_score)
    imbalances   = muscles.get("imbalances", [])
    cumulative_raw = muscles.get("cumulative", {})
    cumulative = {normalize_muscle_name(k): v for k, v in cumulative_raw.items()}
    targets_raw = muscles.get("targets", {})
    targets = {normalize_muscle_name(k): v.get("hyper", 10) for k, v in targets_raw.items()} if targets_raw else {
        "Pecs": 12, "Dos": 14, "Épaules": 12,
        "Biceps": 10, "Triceps": 10, "Jambes": 16, "Core": 12,
    }

    muscle_groups_order = ["Pecs", "Dos", "Épaules", "Biceps", "Triceps", "Jambes", "Core"]
    muscle_vals   = [cumulative.get(g, {}).get("sets_per_week", 0) for g in muscle_groups_order]
    muscle_tgts   = [targets.get(g, 10) for g in muscle_groups_order]
    muscle_colors = [MUSCLE_COLORS.get(g, C["accent"]) for g in muscle_groups_order]

    # ── Running ───────────────────────────────────────────────────
    km_week     = float(running.get("km_per_week", 0) or 0)
    avg_pace    = running.get("avg_pace_str", "—")
    recent_runs = running.get("recent_activities", [])
    pred_10k = (
        (running.get("estimated_10k") or {}).get("label")
        or running.get("predictions", {}).get("10km", "—")
    )

    # ── Pilotage hebdo ───────────────────────────────────────────
    pilot_events = pilotage.get("events", [])
    pilot_summary = pilotage.get("summary", {})
    pilot_series = pilotage.get("series", {})
    pilot_events_json = json.dumps(pilot_events, ensure_ascii=False).replace("</", "<\\/")
    week_start = pilotage.get("week_start", date.today().isoformat())

    sante_h = float(pilot_summary.get("sante_h", 0) or 0)
    travail_h = float(pilot_summary.get("travail_h", 0) or 0)
    relationnel_h = float(pilot_summary.get("relationnel_h", 0) or 0)
    apprentissage_h = float(pilot_summary.get("apprentissage_h", 0) or 0)
    autre_h = float(pilot_summary.get("autre_h", 0) or 0)
    total_planner_h = float(pilot_summary.get("total_h", 0) or 0)

    weekly_training_vals = [float(x.get("value", 0) or 0) for x in pilot_series.get("training_hours_weekly", [])][-260:]
    weekly_steps_vals = [float(x.get("value", 0) or 0) for x in pilot_series.get("steps_weekly", [])][-260:]
    training_long_spark = spark_svg(weekly_training_vals, C["accent"], 340, 70)
    steps_long_spark = spark_svg(weekly_steps_vals, C["green"], 340, 70)

    sport_mix = pilot_series.get("sport_mix_hours", [])
    total_mix = sum(float(x.get("hours", 0) or 0) for x in sport_mix) or 1.0
    sport_mix_rows = []
    for row in sport_mix[:10]:
        t = row.get("type", "Other")
        h = float(row.get("hours", 0) or 0)
        pct = h / total_mix * 100
        sport_mix_rows.append(
            f'<div class="metric-row"><span class="metric-label">{t}</span>'
            f'<span class="metric-val">{h:.1f}h <span class="muted" style="font-size:12px">({pct:.0f}%)</span></span></div>'
        )
    sport_mix_html = "".join(sport_mix_rows) if sport_mix_rows else '<p class="muted">Données sport indisponibles</p>'

    # ── SVGs ──────────────────────────────────────────────────────
    ring_readiness = ring_svg(wbs_score, 100, wbs_color, size=140, stroke=14,
                               label="Readiness", sublabel=wbs_label)
    ring_muscle    = ring_svg(muscle_score, 100, muscle_color, size=90, stroke=10,
                               label="Muscle")
    ring_sleep     = ring_svg(sleep_val, 9, C["purple"], size=90, stroke=10,
                               label="Sommeil", sublabel="hrs")
    ring_hrv       = ring_svg(hrv_val, 100, C["teal"], size=90, stroke=10,
                               label="HRV", sublabel="SDNN")

    spark_hrv      = spark_svg(hrv_hist, C["teal"], 160, 36)
    spark_rhr      = spark_svg(rhr_hist, C["red"], 160, 36)
    spark_sleep    = spark_svg(sleep_hist, C["purple"], 160, 36)
    spark_steps    = spark_svg(steps_hist, C["green"], 160, 36)

    muscle_bars    = bar_chart_svg(muscle_groups_order, muscle_vals, muscle_tgts,
                                   muscle_colors, w=340, h=130)
    pmc_chart      = pmc_chart_svg(daily_load_rows, w=340, h=110)

    # ── Imbalances HTML ───────────────────────────────────────────
    imbalance_items = []
    for im in imbalances[:5]:
        status = im.get("status") or im.get("level", "ok")
        col    = {"critique": C["red"], "faible": C["orange"],
                  "ok": C["green"], "optimal": C["teal"], "excessif": C["orange"]}.get(status, C["muted"])
        icon   = {"critique": "!", "faible": "~", "ok": "OK", "optimal": "A+", "excessif": "MAX"}.get(status, "?")
        spw = im.get("sets_per_week", im.get("current", 0))
        imbalance_items.append(
            f'<div class="im-row"><span class="im-icon" style="color:{col}">{icon}</span>'
            f'<span class="im-muscle">{im.get("muscle","")}</span>'
            f'<span class="im-detail" style="color:{col}">{float(spw):.1f}/sem '
            f'(cible {im.get("target",0)})</span></div>'
        )
    imbalances_html = "\n".join(imbalance_items) if imbalance_items else '<p class="muted">Données insuffisantes</p>'

    # ── Activités récentes HTML ───────────────────────────────────
    recent_acts = training.get("recent_activities", [])
    acts_rows = []
    for act in recent_acts[:8]:
        t  = act.get("type", "?")[:20]
        dt = act.get("started_at", "")[:10]
        dur = int(act.get("duration_s", 0) or 0)
        dur_str = f"{dur//3600}h{(dur%3600)//60:02d}" if dur >= 3600 else f"{dur//60}min"
        dist = act.get("distance_m")
        dist_str = f"{dist/1000:.1f}km" if dist else ""
        hr = act.get("avg_hr")
        hr_str = f"{int(hr)}bpm" if hr else ""
        icon_map = {
            "Running": "Run", "Strength Training": "Gym",
            "Cycling": "Velo", "Swimming": "Swim",
            "Tennis": "Ten", "Skiing": "Ski",
        }
        icon = icon_map.get(t, t[:3])
        acts_rows.append(
            f'<div class="act-row"><span class="act-icon">{icon}</span>'
            f'<span class="act-name">{t}</span>'
            f'<span class="act-date muted">{dt}</span>'
            f'<span class="act-meta">{dur_str} {dist_str} {hr_str}</span></div>'
        )
    acts_html = "\n".join(acts_rows) if acts_rows else '<p class="muted">Aucune activité récente</p>'

    # ── Data quality ───────────────────────────────────────────────
    dq_score = float(data_quality.get("score", 0) or 0)
    dq_duplicates = int(data_quality.get("duplicates_rows", 0) or 0)
    dq_name_missing = float(data_quality.get("exercise_name_missing_pct", 0) or 0)
    dq_weight_missing = float(data_quality.get("exercise_weight_missing_pct", 0) or 0)
    freshness = data_quality.get("freshness", [])[:6] if isinstance(data_quality, dict) else []
    freshness_html = "".join([
        f'<div class="metric-row"><span class="metric-label">{row.get("metric","")}</span>'
        f'<span class="metric-val">{row.get("days_old","?")}j</span></div>'
        for row in freshness
    ]) or '<p class="muted">Aucune métrique disponible</p>'

    source_ah = source_range(data_quality, "apple_health")
    source_strava = source_range(data_quality, "strava_fit")
    source_garmin = source_range(data_quality, "garmin_connect")

    # ── Agenda HTML ────────────────────────────────────────────────
    agenda_rows = []
    for ev in agenda_events[:12]:
        title = (ev.get("title") or "Événement").strip()
        cal = ev.get("calendar_name") or "Calendrier"
        start = (ev.get("start_at") or "")[:16].replace("T", " ")
        end = (ev.get("end_at") or "")[:16].replace("T", " ")
        when = start if not end else f"{start} → {end}"
        location = (ev.get("location") or "").strip()
        agenda_rows.append(
            f'<div class="act-row"><span class="act-icon">CAL</span>'
            f'<span class="act-name">{title}</span>'
            f'<span class="act-date muted">{cal}</span>'
            f'<span class="act-meta">{when}{(" · " + location) if location else ""}</span></div>'
        )
    agenda_html = "\\n".join(agenda_rows) if agenda_rows else '<p class="muted">Aucun événement à venir</p>'
    cal_status = "Connecté" if calendar_sync.get("enabled") else f"Indispo ({calendar_sync.get('error','n/a')})"
    cal_status_color = C["green"] if calendar_sync.get("enabled") else C["orange"]

    # ── Recommandations auto ─────────────────────────────────────
    recos = []
    if acwr_val > 1.4:
        recos.append("Charge élevée: prévoir 2-3 jours de récupération active.")
    elif acwr_val < 0.8:
        recos.append("Charge faible: ajouter progressivement du volume (+10% max/semaine).")
    else:
        recos.append("Charge en zone correcte: maintenir la progression.")

    if wbs_score < 55:
        recos.append("Readiness basse: privilégier sommeil + mobilité avant intensité.")
    elif wbs_score > 75:
        recos.append("Readiness haute: positionner une séance qualitative cette semaine.")

    major_imb = [im for im in imbalances if (im.get("status") or im.get("level")) in ("critique", "faible")]
    if major_imb:
        target_m = ", ".join(sorted({im.get("muscle", "") for im in major_imb if im.get("muscle")}))
        if target_m:
            recos.append(f"Priorité renforcement: {target_m}.")

    recos_html = "".join([f'<div class="rec-item">{r}</div>' for r in recos[:5]])

    # ── Long-term HRV Chart ───────────────────────────────────────
    hrv_long = last_n(metrics_history, "hrv_sdnn", 90)
    hrv_long_spark = spark_svg(hrv_long, C["teal"], 340, 60)

    # ── Données audio ─────────────────────────────────────────────
    vo2_val = metric_val(metrics_history, "vo2max")
    weight  = metric_val(metrics_history, "weight_kg")

    # ── Body Battery gauge ────────────────────────────────────────
    ring_battery = ring_svg(batt_val if batt_val else 0, 100,
                            C["yellow"] if batt_val < 50 else C["green"],
                            size=90, stroke=10, label="Body Battery")

    # ─────────────────────────────────────────────────────────────
    # HTML COMPLET
    # ─────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>PerformOS v3 — Simon</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: {C['bg']}; --card: {C['card']}; --card2: {C['card2']};
    --border: {C['border']}; --text: {C['text']}; --muted: {C['muted']};
    --accent: {C['accent']}; --green: {C['green']}; --orange: {C['orange']};
    --red: {C['red']}; --purple: {C['purple']}; --teal: {C['teal']};
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ background: var(--bg); color: var(--text); font-family: "Space Grotesk", "Avenir Next", "Helvetica Neue", sans-serif; min-height: 100vh; }}
  body {{
    padding-bottom: 80px;
    background:
      radial-gradient(circle at 5% 0%, rgba(74,168,255,0.18), transparent 32%),
      radial-gradient(circle at 95% 10%, rgba(48,209,88,0.12), transparent 30%),
      linear-gradient(180deg, #090b14 0%, #0a0a0f 100%);
  }}

  /* Header */
  .header {{ padding: 20px 16px 12px; background: linear-gradient(180deg, #0d0d18 0%, {C['bg']} 100%); display: flex; justify-content: space-between; align-items: flex-end; }}
  .header-title {{ font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }}
  .header-sub {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}
  .header-date {{ font-size: 12px; color: var(--muted); text-align: right; }}
  .badge {{ display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
  .badge-green {{ background: rgba(48,209,88,.15); color: var(--green); }}
  .badge-orange {{ background: rgba(255,159,10,.15); color: var(--orange); }}
  .badge-red {{ background: rgba(255,69,58,.15); color: var(--red); }}

  /* Navigation tabs */
  .nav {{ position: fixed; bottom: 0; left: 0; right: 0; background: rgba(10,10,15,.95); backdrop-filter: blur(20px); border-top: 1px solid var(--border); display: flex; z-index: 100; padding: 8px 0 20px; overflow-x: auto; }}
  .nav-btn {{ flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 6px 4px; border: none; background: none; color: var(--muted); font-size: 10px; cursor: pointer; transition: color .2s; }}
  .nav-btn.active {{ color: var(--accent); }}
  .nav-icon {{ font-size: 20px; }}

  /* Sections */
  .section {{ display: none; padding: 0 12px; animation: fadeIn .3s ease; }}
  .section.active {{ display: block; }}
  @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}

  /* Cards */
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 16px; margin-bottom: 12px; }}
  .card-title {{ font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; }}
  .card2 {{ background: var(--card2); }}

  /* Hero readiness */
  .hero {{ display: flex; align-items: center; gap: 20px; padding: 20px 16px; background: var(--card); border-radius: 20px; margin: 0 12px 12px; border: 1px solid var(--border); }}
  .hero-rings {{ display: flex; flex-direction: column; align-items: center; }}
  .hero-info {{ flex: 1; }}
  .hero-score {{ font-size: 48px; font-weight: 800; letter-spacing: -2px; line-height: 1; }}
  .hero-label {{ font-size: 14px; color: var(--muted); margin-top: 4px; }}
  .hero-details {{ margin-top: 12px; display: flex; gap: 12px; }}
  .hero-detail {{ text-align: center; }}
  .hero-detail-val {{ font-size: 18px; font-weight: 700; }}
  .hero-detail-lbl {{ font-size: 10px; color: var(--muted); }}

  /* Mini rings row */
  .rings-row {{ display: flex; gap: 8px; justify-content: space-around; }}

  /* Metric rows */
  .metric-row {{ display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--border); }}
  .metric-row:last-child {{ border-bottom: none; }}
  .metric-label {{ font-size: 14px; color: var(--text); }}
  .metric-val {{ font-size: 16px; font-weight: 600; }}
  .metric-sub {{ font-size: 11px; color: var(--muted); }}
  .metric-spark {{ display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }}

  /* Activity list */
  .act-row {{ display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--border); }}
  .act-row:last-child {{ border-bottom: none; }}
  .act-icon {{ width: 36px; height: 36px; background: var(--card2); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: var(--accent); flex-shrink: 0; }}
  .act-name {{ flex: 1; font-size: 13px; font-weight: 500; }}
  .act-date {{ font-size: 11px; }}
  .act-meta {{ font-size: 11px; color: var(--teal); white-space: nowrap; }}

  /* Imbalances */
  .im-row {{ display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); }}
  .im-row:last-child {{ border-bottom: none; }}
  .im-icon {{ width: 24px; text-align: center; font-size: 12px; font-weight: 800; }}
  .im-muscle {{ flex: 1; font-size: 13px; }}
  .im-detail {{ font-size: 12px; }}

  /* PMC section */
  .pmc-legend {{ display: flex; gap: 16px; margin-bottom: 8px; }}
  .pmc-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 4px; }}
  .pmc-label {{ font-size: 11px; color: var(--muted); }}

  /* Stats grid */
  .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .stat-card {{ background: var(--card2); border-radius: 12px; padding: 12px; }}
  .stat-val {{ font-size: 22px; font-weight: 700; }}
  .stat-lbl {{ font-size: 11px; color: var(--muted); margin-top: 2px; }}

  /* Utilities */
  .muted {{ color: var(--muted); }}
  .row {{ display: flex; gap: 8px; }}
  .col {{ flex: 1; }}
  .center {{ text-align: center; }}
  .mt8 {{ margin-top: 8px; }}
  .mt16 {{ margin-top: 16px; }}
  .sep {{ height: 1px; background: var(--border); margin: 8px 0; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 10px; font-weight: 600; }}
  .rec-item {{ padding: 10px 12px; border: 1px solid var(--border); background: var(--card2); border-radius: 10px; margin-bottom: 8px; font-size: 13px; line-height: 1.45; }}

  /* Pilotage weekly planner */
  .planner-toolbar {{ display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:10px; }}
  .planner-btn {{ background: var(--card2); border: 1px solid var(--border); color: var(--text); border-radius: 10px; padding: 8px 10px; font-size: 12px; cursor: pointer; }}
  .planner-week-label {{ font-size: 13px; color: var(--muted); }}
  .week-scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
  .week-grid {{ display:grid; grid-template-columns:repeat(7, minmax(170px, 1fr)); gap:8px; min-width:1240px; }}
  .day-col {{ background: var(--card2); border: 1px solid var(--border); border-radius: 12px; padding: 10px; min-height: 220px; }}
  .day-head {{ display:flex; align-items:center; justify-content:space-between; font-size:12px; color:var(--muted); margin-bottom:8px; }}
  .evt {{ border-left: 3px solid var(--accent); padding: 6px 8px; margin-bottom: 6px; border-radius: 8px; background: rgba(255,255,255,.02); }}
  .evt-t {{ font-size: 12px; font-weight: 600; line-height: 1.3; }}
  .evt-s {{ font-size: 11px; color: var(--muted); margin-top: 2px; }}
  .evt-empty {{ font-size: 11px; color: var(--muted); }}

  /* Scrollable areas */
  .scroll-x {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
  .no-scroll {{ overflow: visible; }}
  svg {{ max-width: 100%; }}
  @media (min-width: 960px) {{
    body {{ max-width: 1100px; margin: 0 auto; }}
  }}
</style>
</head>
<body>

<!-- ═══ HEADER ═════════════════════════════════════════════════ -->
<div class="header">
  <div>
    <div class="header-title">PerformOS</div>
    <div class="header-sub">Simon Hingant · Lorient</div>
  </div>
  <div class="header-date">
    <div>{today}</div>
    <div class="muted">{now}</div>
  </div>
</div>

<!-- ═══ NAVIGATION ═════════════════════════════════════════════ -->
<nav class="nav">
  <button class="nav-btn active" onclick="showSection('pilotage')" id="btn-pilotage">
    <span class="nav-icon">&#128197;</span>
    <span>Pilotage</span>
  </button>
  <button class="nav-btn" onclick="showSection('today')" id="btn-today">
    <span class="nav-icon">&#9711;</span>
    <span>Santé</span>
  </button>
  <button class="nav-btn" onclick="showSection('training')" id="btn-training">
    <span class="nav-icon">&#9654;</span>
    <span>Charge</span>
  </button>
  <button class="nav-btn" onclick="showSection('muscles')" id="btn-muscles">
    <span class="nav-icon">&#9651;</span>
    <span>Muscu</span>
  </button>
  <button class="nav-btn" onclick="showSection('health')" id="btn-health">
    <span class="nav-icon">&#9829;</span>
    <span>Santé</span>
  </button>
  <button class="nav-btn" onclick="showSection('history')" id="btn-history">
    <span class="nav-icon">&#9783;</span>
    <span>Historique</span>
  </button>
  <button class="nav-btn" onclick="showSection('agenda')" id="btn-agenda">
    <span class="nav-icon">&#128197;</span>
    <span>Reco</span>
  </button>
</nav>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- SECTION : PILOTAGE HEBDO                                    -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="section active" id="s-pilotage">

  <div class="card" style="margin-top:12px">
    <div class="card-title">Planning semaine (Apple Calendar + tâches)</div>
    <div class="planner-toolbar">
      <button class="planner-btn" onclick="shiftWeek(-1)">Semaine -1</button>
      <div class="planner-week-label" id="plannerWeekLabel">{week_start}</div>
      <button class="planner-btn" onclick="shiftWeek(1)">Semaine +1</button>
    </div>
    <div class="week-scroll">
      <div class="week-grid" id="weekGrid"></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Répartition hebdo (heures)</div>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-val" id="sum-sante" style="color:{CATEGORY_COLORS['sante']}">{sante_h:.1f}</div><div class="stat-lbl">Santé</div></div>
      <div class="stat-card"><div class="stat-val" id="sum-travail" style="color:{CATEGORY_COLORS['travail']}">{travail_h:.1f}</div><div class="stat-lbl">Travail</div></div>
      <div class="stat-card"><div class="stat-val" id="sum-relationnel" style="color:{CATEGORY_COLORS['relationnel']}">{relationnel_h:.1f}</div><div class="stat-lbl">Relationnel</div></div>
      <div class="stat-card"><div class="stat-val" id="sum-apprentissage" style="color:{CATEGORY_COLORS['apprentissage']}">{apprentissage_h:.1f}</div><div class="stat-lbl">Apprentissage</div></div>
      <div class="stat-card"><div class="stat-val" id="sum-autre" style="color:{CATEGORY_COLORS['autre']}">{autre_h:.1f}</div><div class="stat-lbl">Autre</div></div>
      <div class="stat-card"><div class="stat-val" id="sum-total">{total_planner_h:.1f}</div><div class="stat-lbl">Total semaine</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Séries longues (2017 → 2026)</div>
    <div class="metric-row">
      <span class="metric-label">Heures d'entraînement / semaine</span>
      <span class="metric-val" style="color:{C['accent']}">{(weekly_training_vals[-1] if weekly_training_vals else 0):.1f}h</span>
    </div>
    <div class="scroll-x">{training_long_spark}</div>
    <div class="sep"></div>
    <div class="metric-row">
      <span class="metric-label">Pas / semaine</span>
      <span class="metric-val" style="color:{C['green']}">{(weekly_steps_vals[-1] if weekly_steps_vals else 0):.0f}</span>
    </div>
    <div class="scroll-x">{steps_long_spark}</div>
  </div>

  <div class="card">
    <div class="card-title">Répartition sports (temps cumulé)</div>
    {sport_mix_html}
  </div>

  <div class="card">
    <div class="card-title">Ajout tâche (CLI rapide)</div>
    <div style="font-size:12px;color:var(--muted);line-height:1.6">
      Exemple:<br>
      <code>python3 main.py --add-task "10km tempo" --task-category sante --task-date 2026-12-11 --task-time 14:00 --task-duration-min 70 --task-sync-apple</code>
    </div>
  </div>

</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- SECTION : AUJOURD'HUI                                       -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="section" id="s-today">

  <!-- Hero Readiness -->
  <div class="hero" style="margin-top:12px">
    <div class="hero-rings">
      {ring_readiness}
    </div>
    <div class="hero-info">
      <div class="hero-score" style="color:{wbs_color}">{wbs_score:.0f}</div>
      <div class="hero-label">{wbs_label}</div>
      <div class="hero-details">
        <div class="hero-detail">
          <div class="hero-detail-val" style="color:{acwr_color}">{acwr_val:.2f}</div>
          <div class="hero-detail-lbl">ACWR</div>
        </div>
        <div class="hero-detail">
          <div class="hero-detail-val" style="color:{C['teal']}">{hrv_val:.0f}</div>
          <div class="hero-detail-lbl">HRV</div>
        </div>
        <div class="hero-detail">
          <div class="hero-detail-val" style="color:{C['purple']}">{sleep_val:.1f}h</div>
          <div class="hero-detail-lbl">Sommeil</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Mini rings row -->
  <div class="card">
    <div class="card-title">Biometrics</div>
    <div class="rings-row">
      {ring_hrv}
      {ring_sleep}
      {ring_muscle}
      {ring_battery}
    </div>
  </div>

  <!-- Daily stats -->
  <div class="card">
    <div class="card-title">Aujourd'hui</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-val" style="color:{C['green']}">{steps_val:,.0f}</div>
        <div class="stat-lbl">Pas</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['orange']}">{active_cal:.0f}</div>
        <div class="stat-lbl">Cal actives</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['teal']}">{flights:.0f}</div>
        <div class="stat-lbl">Etages</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['red']}">{rhr_val:.0f}</div>
        <div class="stat-lbl">FC Repos</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Data Quality</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-val" style="color:{color_for_score(dq_score)}">{dq_score:.0f}</div>
        <div class="stat-lbl">Score qualité /100</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['orange']}">{dq_duplicates}</div>
        <div class="stat-lbl">Lignes doublons</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['red']}">{dq_name_missing:.1f}%</div>
        <div class="stat-lbl">Exercice manquant</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['red']}">{dq_weight_missing:.1f}%</div>
        <div class="stat-lbl">Poids manquant</div>
      </div>
    </div>
  </div>

  <!-- Activités récentes -->
  <div class="card">
    <div class="card-title">Activités récentes</div>
    {acts_html}
  </div>

</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- SECTION : CHARGE D'ENTRAÎNEMENT                             -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="section" id="s-training">

  <!-- PMC -->
  <div class="card" style="margin-top:12px">
    <div class="card-title">Performance Management Chart — 90j</div>
    <div class="pmc-legend">
      <span><span class="pmc-dot" style="background:{C['teal']}"></span><span class="pmc-label">CTL (forme)</span></span>
      <span><span class="pmc-dot" style="background:{C['orange']}"></span><span class="pmc-label">ATL (fatigue)</span></span>
      <span><span class="pmc-dot" style="background:{C['purple']}"></span><span class="pmc-label">TSB (fraicheur)</span></span>
    </div>
    <div class="scroll-x">{pmc_chart}</div>
    <div class="stats-grid mt8">
      <div class="stat-card">
        <div class="stat-val" style="color:{C['teal']}">{ctl:.1f}</div>
        <div class="stat-lbl">CTL (fitness)</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['orange']}">{atl:.1f}</div>
        <div class="stat-lbl">ATL (fatigue)</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['purple']}">{tsb:+.1f}</div>
        <div class="stat-lbl">TSB (fraicheur)</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{acwr_color}">{acwr_val:.2f}</div>
        <div class="stat-lbl">ACWR ({acwr_zone})</div>
      </div>
    </div>
  </div>

  <!-- Running stats -->
  <div class="card">
    <div class="card-title">Running</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-val" style="color:{C['green']}">{km_week:.1f}</div>
        <div class="stat-lbl">km/semaine</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['teal']}">{avg_pace}</div>
        <div class="stat-lbl">Allure moy.</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['accent']}">{pred_10k}</div>
        <div class="stat-lbl">Estimation 10km</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['purple']}">{wbs_score:.0f}/100</div>
        <div class="stat-lbl">Readiness</div>
      </div>
    </div>
  </div>

  <!-- Activités -->
  <div class="card">
    <div class="card-title">Historique activités</div>
    {acts_html}
  </div>

</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- SECTION : MUSCULATION                                        -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="section" id="s-muscles">

  <div class="card" style="margin-top:12px">
    <div class="card-title">Score musculaire</div>
    <div style="display:flex;align-items:center;gap:16px">
      {ring_svg(muscle_score, 100, muscle_color, size=100, stroke=12, label="Score")}
      <div>
        <div style="font-size:36px;font-weight:800;color:{muscle_color}">{muscle_score:.0f}<span style="font-size:16px;color:var(--muted)">/100</span></div>
        <div class="muted" style="font-size:12px;margin-top:4px">Volume vs objectifs hypertrophie</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Volume par groupe — 4 semaines</div>
    <div class="scroll-x">{muscle_bars}</div>
    <div style="font-size:10px;color:var(--muted);margin-top:8px">Barres grises = objectif. Valeurs en séries/semaine.</div>
  </div>

  <div class="card">
    <div class="card-title">Déséquilibres</div>
    {imbalances_html}
  </div>

  <!-- Détail par groupe -->
  <div class="card">
    <div class="card-title">Détail groupes musculaires</div>
    {''.join([
        f'<div class="metric-row"><span class="metric-label" style="color:{MUSCLE_COLORS.get(g, C["accent"])}">{g}</span>'
        f'<span class="metric-val">{cumulative.get(g, {}).get("sets_per_week", 0):.1f} <span class="muted" style="font-size:12px">/ {targets.get(g,10)} séries/sem</span></span></div>'
        for g in muscle_groups_order
    ])}
  </div>

</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- SECTION : SANTÉ                                             -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="section" id="s-health">

  <div class="card" style="margin-top:12px">
    <div class="card-title">HRV — 30 jours</div>
    <div class="metric-row">
      <div>
        <div class="metric-val" style="color:{C['teal']}">{hrv_val:.0f} ms</div>
        <div class="metric-sub">SDNN nocturne</div>
      </div>
      <div>{spark_hrv}</div>
    </div>
    <div class="sep"></div>
    <div class="metric-row">
      <div>
        <div class="metric-val" style="color:{C['red']}">{rhr_val:.0f} bpm</div>
        <div class="metric-sub">FC Repos</div>
      </div>
      <div>{spark_rhr}</div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Sommeil — 30 jours</div>
    <div class="metric-row">
      <div>
        <div class="metric-val" style="color:{C['purple']}">{sleep_val:.1f}h</div>
        <div class="metric-sub">Durée moyenne</div>
      </div>
      <div>{spark_sleep}</div>
    </div>
    {'<div class="sep"></div><div class="metric-row"><div><div class="metric-val" style="color:'+C["yellow"]+'">' + f'{batt_val:.0f}%' + '</div><div class="metric-sub">Body Battery</div></div></div>' if batt_val else ''}
  </div>

  <div class="card">
    <div class="card-title">Activité quotidienne — 14j</div>
    <div class="metric-row">
      <div>
        <div class="metric-val" style="color:{C['green']}">{steps_val:,.0f}</div>
        <div class="metric-sub">Pas (dernier relevé)</div>
      </div>
      <div>{spark_steps}</div>
    </div>
    <div class="sep"></div>
    <div class="stats-grid mt8">
      <div class="stat-card">
        <div class="stat-val" style="color:{C['orange']}">{active_cal:.0f}</div>
        <div class="stat-lbl">Cal actives</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['teal']}">{flights:.0f}</div>
        <div class="stat-lbl">Etages</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Freshness métriques</div>
    {freshness_html}
  </div>

  <div class="card">
    <div class="card-title">Métriques long terme</div>
    <div class="metric-row">
      <span class="metric-label">VO2Max</span>
      <span class="metric-val" style="color:{C['accent']}">{vo2_val:.1f} ml/kg/min</span>
    </div>
    <div class="metric-row">
      <span class="metric-label">Poids</span>
      <span class="metric-val">{weight:.1f} kg</span>
    </div>
    {'<div class="metric-row"><span class="metric-label">Stress moyen</span><span class="metric-val" style="color:' + C["orange"] + '">' + f'{stress_val:.0f}/100' + '</span></div>' if stress_val else ''}
  </div>

</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- SECTION : HISTORIQUE LONG TERME                             -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="section" id="s-history">

  <div class="card" style="margin-top:12px">
    <div class="card-title">HRV long terme — 90 jours</div>
    <div class="scroll-x">{hrv_long_spark}</div>
    <div class="muted" style="font-size:11px;margin-top:6px">Tendance SDNN nocturne (Garmin 265S)</div>
  </div>

  <div class="card">
    <div class="card-title">Depuis 2017 — Vue globale</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-val" style="color:{C['accent']}">{len([m for m in metrics_history if m.get('metric')=='hrv_sdnn'])}</div>
        <div class="stat-lbl">Nuits HRV</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['green']}">{training.get('total_activities', 0)}</div>
        <div class="stat-lbl">Activités totales</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['orange']}">{training.get('total_km', 0):.0f}</div>
        <div class="stat-lbl">km cumulés</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:{C['purple']}">{training.get('strength_sessions', 0)}</div>
        <div class="stat-lbl">Sessions muscu</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Sources de données</div>
    <div class="metric-row">
      <span class="metric-label">Apple Health</span>
      <span class="metric-val muted" style="font-size:13px">{source_ah}</span>
    </div>
    <div class="metric-row">
      <span class="metric-label">Strava FIT</span>
      <span class="metric-val muted" style="font-size:13px">{source_strava}</span>
    </div>
    <div class="metric-row">
      <span class="metric-label">Garmin Connect</span>
      <span class="metric-val muted" style="font-size:13px">{source_garmin}</span>
    </div>
    <div class="metric-row">
      <span class="metric-label">Apple Calendar</span>
      <span class="metric-val" style="font-size:13px;color:{cal_status_color}">{cal_status}</span>
    </div>
    <div style="margin-top:12px;padding:10px;background:var(--card2);border-radius:10px;font-size:11px;color:var(--muted);line-height:1.6">
      Les plages sont calculées automatiquement depuis la base.<br>
      Utilisez <code>python3 main.py --garmin --days 60</code> pour rafraîchir Garmin.
    </div>
  </div>

</div>

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- SECTION : AGENDA                                           -->
<!-- ═══════════════════════════════════════════════════════════ -->
<div class="section" id="s-agenda">

  <div class="card" style="margin-top:12px">
    <div class="card-title">Calendrier Apple — Prochains événements</div>
    <div class="metric-row">
      <span class="metric-label">Statut sync</span>
      <span class="metric-val" style="color:{cal_status_color}">{cal_status}</span>
    </div>
    <div class="sep"></div>
    {agenda_html}
  </div>

  <div class="card">
    <div class="card-title">Recommandations auto</div>
    {recos_html}
  </div>

  <div class="card">
    <div class="card-title">Plan entraînement (3 semaines)</div>
    <div class="rec-item">Semaine 1: base aérobie + renforcement ciblé dos/jambes/core.</div>
    <div class="rec-item">Semaine 2: montée progressive (+5 à +10%) avec 1 séance qualitative.</div>
    <div class="rec-item">Semaine 3: consolidation puis récupération active selon ACWR et Readiness.</div>
  </div>

</div>

<!-- ═══ SCRIPTS ════════════════════════════════════════════════ -->
<script>
function showSection(id) {{
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('s-' + id).classList.add('active');
  document.getElementById('btn-' + id).classList.add('active');
  window.scrollTo(0, 0);
}}

const PILOT_EVENTS = {pilot_events_json};
const CAT_COLORS = {json.dumps(CATEGORY_COLORS)};
const CAT_KEYS = ['sante', 'travail', 'relationnel', 'apprentissage', 'autre'];
const WEEK_START_ISO = "{week_start}";
let weekOffset = 0;

function parseIso(s) {{
  return s ? new Date(s.replace(' ', 'T')) : null;
}}

function startOfWeek(baseDate) {{
  const d = new Date(baseDate);
  const day = (d.getDay() + 6) % 7; // Monday=0
  d.setDate(d.getDate() - day);
  d.setHours(0,0,0,0);
  return d;
}}

function addDays(d, n) {{
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}}

function isoDate(d) {{
  return d.toISOString().slice(0,10);
}}

function hmDiff(start, end) {{
  if (!start || !end) return 0;
  return Math.max(0, (end - start) / 3600000);
}}

function categoryLabel(cat) {{
  const labels = {{
    sante: 'Santé', travail: 'Travail', relationnel: 'Relationnel',
    apprentissage: 'Apprentissage', autre: 'Autre'
  }};
  return labels[cat] || 'Autre';
}}

function renderPlannerWeek() {{
  const base = startOfWeek(parseIso(WEEK_START_ISO) || new Date());
  const weekStart = addDays(base, weekOffset * 7);
  const weekEnd = addDays(weekStart, 7);

  const label = `${{isoDate(weekStart)}} → ${{isoDate(addDays(weekEnd, -1))}}`;
  const lblEl = document.getElementById('plannerWeekLabel');
  if (lblEl) lblEl.textContent = label;

  const days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
  const byDay = Array.from({{length:7}}, () => []);
  const sums = {{ sante:0, travail:0, relationnel:0, apprentissage:0, autre:0, total:0 }};

  PILOT_EVENTS.forEach(ev => {{
    const st = parseIso(ev.start_at);
    const en = parseIso(ev.end_at) || st;
    if (!st) return;
    if (st < weekStart || st >= weekEnd) return;
    const idx = (st.getDay() + 6) % 7;
    const cat = CAT_KEYS.includes(ev.category) ? ev.category : 'autre';
    byDay[idx].push({{...ev, _start: st, _end: en, _cat: cat}});
    const h = hmDiff(st, en);
    sums[cat] += h;
    sums.total += h;
  }});

  for (const k of CAT_KEYS) {{
    const el = document.getElementById(`sum-${{k}}`);
    if (el) el.textContent = sums[k].toFixed(1);
  }}
  const sumTot = document.getElementById('sum-total');
  if (sumTot) sumTot.textContent = sums.total.toFixed(1);

  const grid = document.getElementById('weekGrid');
  if (!grid) return;
  grid.innerHTML = '';

  for (let i = 0; i < 7; i++) {{
    const d = addDays(weekStart, i);
    const dateLbl = isoDate(d);
    const evts = byDay[i].sort((a,b) => a._start - b._start);
    const rows = evts.length ? evts.map(e => {{
      const hh = String(e._start.getHours()).padStart(2,'0');
      const mm = String(e._start.getMinutes()).padStart(2,'0');
      const src = e.calendar_name ? ` · ${{e.calendar_name}}` : '';
      const color = CAT_COLORS[e._cat] || CAT_COLORS.autre;
      return `<div class="evt" style="border-left-color:${{color}}">
        <div class="evt-t">${{e.title || 'Événement'}}</div>
        <div class="evt-s">${{hh}}:${{mm}} · ${{categoryLabel(e._cat)}}${{src}}</div>
      </div>`;
    }}).join('') : '<div class="evt-empty">Aucun événement</div>';

    const col = document.createElement('div');
    col.className = 'day-col';
    col.innerHTML = `<div class="day-head"><span>${{days[i]}}</span><span>${{dateLbl}}</span></div>${{rows}}`;
    grid.appendChild(col);
  }}
}}

function shiftWeek(delta) {{
  weekOffset += delta;
  renderPlannerWeek();
}}

document.addEventListener('DOMContentLoaded', function() {{
  document.querySelectorAll('circle[stroke-dasharray]').forEach(c => {{
    const final = c.getAttribute('stroke-dasharray');
    c.setAttribute('stroke-dasharray', '0 1000');
    setTimeout(() => c.setAttribute('stroke-dasharray', final), 100);
  }});
  renderPlannerWeek();
}});
</script>
</body>
</html>"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    kb = output_path.stat().st_size // 1024
    print(f"  ✅ Dashboard : {output_path} ({kb}KB)")
