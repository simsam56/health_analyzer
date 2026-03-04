"""
training_load.py — Charge d'entraînement, forme, fatigue

Calcule :
  - TSS (Training Stress Score) proxy par activité
  - ATL (Acute Training Load) — fatigue 7j
  - CTL (Chronic Training Load) — forme 42j
  - TSB (Training Stress Balance) — état de forme
  - ACWR (Acute:Chronic Workload Ratio) — risque blessure
  - Wakeboard Readiness Score composite
  - Prédictions de course (Riegel)
  - Score de forme quotidien (0-100)
"""
import sqlite3
import math
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict
from statistics import median

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "athlete.db"

# ─────────────────────────────────────────────────────────────────
# CONSTANTES PMC
# ─────────────────────────────────────────────────────────────────
CTL_DAYS = 42    # Chronic Training Load (fitness)
ATL_DAYS = 7     # Acute Training Load (fatigue)

# Fraîcheur maximale (jours) au-delà de laquelle la métrique est pénalisée
FRESHNESS_DAYS = {
    "hrv_sdnn": 14,
    "rhr": 10,
    "sleep_h": 10,
    "vo2max": 90,
    "weight_kg": 45,
}

# Multiplicateurs fatigue neuromusculaire (musculation)
NEURAL_FATIGUE_MULTIPLIERS = {
    "jambe":    1.5,
    "full":     1.2,
    "wakeboard":1.2,
    "dos":      1.1,
    "upper":    1.0,
    "pecs":     1.0,
    "mixed":    1.1,
}

# Zones ACWR (Acute:Chronic Workload Ratio)
ACWR_ZONES = {
    "repos":    (0.0,  0.5),
    "léger":    (0.5,  0.8),
    "optimal":  (0.8,  1.3),
    "élevé":    (1.3,  1.5),
    "danger":   (1.5, 10.0),
}

# Exposant empirique de Riegel (1981) pour extrapolation performance endurance
RIEGEL_EXPONENT = 1.06


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _estimate_hr_rest(conn: sqlite3.Connection) -> float:
    """
    FC repos de référence (RHR): moyenne des 30 dernières valeurs.
    Fallback prudent à 58 bpm.
    """
    row = conn.execute(
        """
        SELECT AVG(value)
        FROM (
          SELECT value
          FROM health_metrics
          WHERE metric='rhr' AND value IS NOT NULL
          ORDER BY date DESC
          LIMIT 30
        )
        """
    ).fetchone()
    try:
        r = float(row[0]) if row and row[0] is not None else 58.0
    except Exception:
        r = 58.0
    return _clamp(r, 40.0, 90.0)


def _estimate_hr_max(conn: sqlite3.Connection) -> float:
    """
    FC max de référence:
    - max_hr observée (percentile haut implicite via MAX)
    - fallback 190 bpm si indisponible.
    """
    row = conn.execute(
        """
        SELECT MAX(max_hr)
        FROM activities
        WHERE max_hr IS NOT NULL AND max_hr > 0
        """
    ).fetchone()
    try:
        m = float(row[0]) if row and row[0] is not None else 190.0
    except Exception:
        m = 190.0
    return _clamp(m, 165.0, 210.0)


# ─────────────────────────────────────────────────────────────────
# CALCUL TSS PROXY
# ─────────────────────────────────────────────────────────────────
def tss_from_activity(
    row: dict,
    hr_rest: float = 58.0,
    hr_max: float = 190.0,
) -> float:
    """
    Charge interne (proxy TSS) depuis les données disponibles.
    Priorité:
      1) training_load si disponible
      2) TRIMP type Bannister (FC réserve + durée)
      3) modèle musculation (densité de séries + durée)
      4) fallback calories / durée
    """
    # 1. Training Load source
    if row.get("training_load") and row["training_load"] > 0:
        return round(_clamp(float(row["training_load"]), 0.0, 300.0), 1)

    act_type  = (row.get("type") or "").lower()
    act_name  = (row.get("name") or "").lower()
    duration  = row.get("duration_s") or 0
    avg_hr    = row.get("avg_hr") or 0
    calories  = row.get("calories") or 0
    strength_sets = int(row.get("strength_sets") or 0)

    if duration <= 0:
        return 0.0

    dur_h = duration / 3600
    dur_min = duration / 60

    # 2. Cardio basé FC: TRIMP (Bannister-like)
    if avg_hr > 0 and hr_max > hr_rest + 20:
        hr_ratio = (float(avg_hr) - hr_rest) / (hr_max - hr_rest)
        hr_ratio = _clamp(hr_ratio, 0.0, 1.0)
        # Coefficient masculin historique (0.64, 1.92) faute d'info sexe.
        trimp = dur_min * hr_ratio * 0.64 * math.exp(1.92 * hr_ratio)
        if trimp > 0:
            return round(_clamp(trimp, 0.0, 300.0), 1)

    # 3. Musculation: densité de séries + fatigue neuromusculaire
    if ("strength" in act_type or "training" in act_type or "muscu" in act_name):
        mult = 1.0
        for key, val in NEURAL_FATIGUE_MULTIPLIERS.items():
            if key in act_name:
                mult = val
                break
        base = dur_h * 40.0
        if strength_sets > 0:
            set_density = strength_sets / max(dur_h, 0.25)  # sets/h
            density_factor = _clamp(0.75 + set_density / 32.0, 0.75, 1.45)
        else:
            density_factor = 1.0
        tss = base * mult * density_factor
        return round(_clamp(tss, 0.0, 220.0), 1)

    # 4. Calories (fallback)
    if calories > 0:
        return round(_clamp(float(calories) / 8.0, 0.0, 160.0), 1)

    # 5. Durée seule
    if "running" in act_type or "cycling" in act_type:
        return round(_clamp(dur_h * 50.0, 0.0, 150.0), 1)

    return round(_clamp(dur_h * 32.0, 0.0, 110.0), 1)


# ─────────────────────────────────────────────────────────────────
# PMC (PERFORMANCE MANAGEMENT CHART)
# ─────────────────────────────────────────────────────────────────
def build_daily_tss(conn: sqlite3.Connection) -> dict[str, float]:
    """Agrège le TSS par jour depuis toutes les activités."""
    hr_rest = _estimate_hr_rest(conn)
    hr_max = _estimate_hr_max(conn)
    rows = conn.execute("""
        SELECT
          date(a.started_at) AS day,
          a.type,
          a.name,
          a.training_load,
          a.avg_hr,
          a.duration_s,
          a.calories,
          a.distance_m,
          COALESCE(ss.total_sets, 0) AS strength_sets
        FROM activities a
        LEFT JOIN strength_sessions ss ON ss.activity_id = a.id
        WHERE a.started_at IS NOT NULL
        ORDER BY day
    """).fetchall()

    daily_tss: dict[str, float] = defaultdict(float)

    for row in rows:
        d = {
            "type": row[1], "name": row[2], "training_load": row[3],
            "avg_hr": row[4], "duration_s": row[5], "calories": row[6],
            "distance_m": row[7], "strength_sets": row[8],
        }
        tss = tss_from_activity(d, hr_rest=hr_rest, hr_max=hr_max)
        daily_tss[row[0]] += tss

    return dict(daily_tss)


def compute_pmc(
    daily_tss: dict[str, float],
    end_date: date | None = None,
    start_date: date | None = None,
) -> list[dict]:
    """
    Calcule CTL, ATL, TSB pour chaque jour.

    Retourne une liste de dicts :
    [{"date": "2024-01-01", "tss": 50, "ctl": 45, "atl": 52, "tsb": -7}, ...]
    """
    if not daily_tss:
        return []

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        # Démarrer 90j avant la première donnée pour initialiser CTL
        first_day = min(date.fromisoformat(d) for d in daily_tss)
        start_date = first_day - timedelta(days=90)

    # Facteurs de lissage (EMA discret d'une décroissance exponentielle continue)
    k_ctl = 1 - math.exp(-1 / CTL_DAYS)
    k_atl = 1 - math.exp(-1 / ATL_DAYS)

    ctl = 0.0
    atl = 0.0
    pmc = []

    current = start_date
    while current <= end_date:
        ds   = current.strftime("%Y-%m-%d")
        tss  = daily_tss.get(ds, 0.0)

        ctl = ctl + k_ctl * (tss - ctl)
        atl = atl + k_atl * (tss - atl)
        tsb = ctl - atl

        pmc.append({
            "date": ds,
            "tss":  round(tss, 1),
            "ctl":  round(ctl, 1),
            "atl":  round(atl, 1),
            "tsb":  round(tsb, 1),
        })

        current += timedelta(days=1)

    return pmc


def compute_acwr(
    daily_tss: dict[str, float],
    end_date: date | None = None,
) -> dict:
    """
    Calcule l'ACWR (Acute:Chronic Workload Ratio).
    Acute  = moyenne 7j
    Chronic = moyenne 28j (rolling)

    Retourne : {"acwr": float, "acute": float, "chronic": float, "zone": str}
    """
    if end_date is None:
        end_date = date.today()

    def avg_days(n: int) -> float:
        total = sum(
            daily_tss.get((end_date - timedelta(days=i)).strftime("%Y-%m-%d"), 0)
            for i in range(n)
        )
        return total / n

    acute_roll   = avg_days(7)
    chronic_roll = avg_days(28)
    acwr_roll = acute_roll / chronic_roll if chronic_roll > 0.5 else 0.0

    # Variante EWMA (plus sensible aux changements récents)
    k_acute = 1 - math.exp(-1 / 7)
    k_chronic = 1 - math.exp(-1 / 28)
    ewma_acute = 0.0
    ewma_chronic = 0.0
    for i in range(120, -1, -1):
        ds = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
        load = float(daily_tss.get(ds, 0.0) or 0.0)
        ewma_acute = ewma_acute + k_acute * (load - ewma_acute)
        ewma_chronic = ewma_chronic + k_chronic * (load - ewma_chronic)
    acwr_ewma = ewma_acute / ewma_chronic if ewma_chronic > 0.5 else 0.0

    # Valeur retenue = EWMA, fallback rolling
    acwr = acwr_ewma if acwr_ewma > 0 else acwr_roll

    zone = "repos"
    for z, (lo, hi) in ACWR_ZONES.items():
        if lo <= acwr < hi:
            zone = z
            break

    return {
        "acwr":    round(acwr, 2),
        "acwr_roll": round(acwr_roll, 2),
        "acwr_ewma": round(acwr_ewma, 2),
        "acute":   round(acute_roll, 1),
        "chronic": round(chronic_roll, 1),
        "acute_ewma": round(ewma_acute, 1),
        "chronic_ewma": round(ewma_chronic, 1),
        "method": "ewma",
        "zone":    zone,
    }


# ─────────────────────────────────────────────────────────────────
# MÉTRIQUES SANTÉ (HRV, FC REPOS, SOMMEIL)
# ─────────────────────────────────────────────────────────────────
def get_health_metrics(
    conn: sqlite3.Connection,
    days_back: int = 90,
    end_date: date | None = None,
) -> dict:
    """
    Récupère les dernières métriques santé disponibles.
    Utilise une fenêtre glissante croissante si pas de données récentes.
    """
    if end_date is None:
        end_date = date.today()

    def _days_old(dt_iso: str | None) -> int | None:
        if not dt_iso:
            return None
        try:
            return (end_date - date.fromisoformat(dt_iso[:10])).days
        except Exception:
            return None

    def latest_metric(metric: str, windows=[7, 14, 30, 60, 90, 180, 365]) -> tuple[float | None, str | None, int | None]:
        for w in windows:
            cutoff = (end_date - timedelta(days=w)).strftime("%Y-%m-%d")
            row = conn.execute("""
                SELECT AVG(value), MAX(date)
                FROM health_metrics
                WHERE metric=? AND date>=? AND date<=?
            """, (metric, cutoff, str(end_date))).fetchone()
            if row and row[0] is not None:
                dt = row[1]
                return round(float(row[0]), 2), dt, _days_old(dt)
        # Fallback : 5 dernières valeurs sans limite de date
        row = conn.execute("""
            SELECT AVG(value), MAX(date)
            FROM (SELECT value, date FROM health_metrics
                  WHERE metric=? ORDER BY date DESC LIMIT 5)
        """, (metric,)).fetchone()
        if row and row[0] is not None:
            dt = row[1]
            return round(float(row[0]), 2), dt, _days_old(dt)
        return None, None, None

    def freshness_factor(metric: str, days_old: int | None) -> float:
        """Retourne un facteur 0.0-1.0 selon la fraîcheur de la métrique."""
        if days_old is None:
            return 0.0
        max_days = FRESHNESS_DAYS.get(metric, 30)
        if days_old <= 0:
            return 1.0
        if days_old <= max_days:
            return 1.0
        # Dégradation progressive jusqu'à 4x la fenêtre
        fade_span = max_days * 3
        if days_old >= max_days + fade_span:
            return 0.0
        return max(0.0, 1.0 - (days_old - max_days) / fade_span)

    hrv_val,     hrv_date,     hrv_days     = latest_metric("hrv_sdnn")
    rhr_val,     rhr_date,     rhr_days     = latest_metric("rhr")
    vo2max_val,  vo2max_date,  vo2max_days  = latest_metric("vo2max")
    sleep_val,   sleep_date,   sleep_days   = latest_metric("sleep_h")
    weight_val,  weight_date,  weight_days  = latest_metric("weight_kg")
    bb_val,      bb_date,      bb_days      = latest_metric("body_battery")

    # Baseline HRV (percentile 50 des 6 derniers mois)
    hrv_baseline = conn.execute("""
        SELECT AVG(value) FROM (
            SELECT value FROM health_metrics
            WHERE metric='hrv_sdnn'
            ORDER BY date DESC LIMIT 60
        )
    """).fetchone()
    hrv_baseline = float(hrv_baseline[0]) if hrv_baseline and hrv_baseline[0] else hrv_val

    rhr_baseline = conn.execute("""
        SELECT AVG(value) FROM (
            SELECT value FROM health_metrics
            WHERE metric='rhr'
            ORDER BY date DESC LIMIT 30
        )
    """).fetchone()
    rhr_baseline = float(rhr_baseline[0]) if rhr_baseline and rhr_baseline[0] else rhr_val

    return {
        "hrv":          hrv_val,
        "hrv_date":     hrv_date,
        "hrv_days_old": hrv_days,
        "hrv_baseline": hrv_baseline,
        "hrv_freshness": freshness_factor("hrv_sdnn", hrv_days),
        "rhr":          rhr_val,
        "rhr_baseline": rhr_baseline,
        "rhr_date":     rhr_date,
        "rhr_days_old": rhr_days,
        "rhr_freshness": freshness_factor("rhr", rhr_days),
        "vo2max":       vo2max_val,
        "vo2max_date":  vo2max_date,
        "vo2max_days_old": vo2max_days,
        "vo2max_freshness": freshness_factor("vo2max", vo2max_days),
        "sleep_h":      sleep_val,
        "sleep_date":   sleep_date,
        "sleep_days_old": sleep_days,
        "sleep_freshness": freshness_factor("sleep_h", sleep_days),
        "weight_kg":    weight_val,
        "weight_date":  weight_date,
        "weight_days_old": weight_days,
        "weight_freshness": freshness_factor("weight_kg", weight_days),
        "body_battery": bb_val,
        "body_battery_date": bb_date,
        "body_battery_days_old": bb_days,
        "body_battery_freshness": freshness_factor("rhr", bb_days),
    }


# ─────────────────────────────────────────────────────────────────
# WAKEBOARD READINESS SCORE
# ─────────────────────────────────────────────────────────────────
def compute_wakeboard_score(
    hrv_val:     float | None,
    hrv_baseline:float | None,
    sleep_h:     float | None,
    acwr_val:    float,
    rhr_val:     float | None = None,
    rhr_baseline: float | None = None,
    body_battery: float | None = None,
    freshness:   dict | None = None,
) -> dict:
    """
    Wakeboard Readiness Score : 0-100

    Composantes :
      - HRV (30%)
      - Sommeil (25%)
      - ACWR (20%)
      - RHR vs baseline (15%)
      - Body Battery (10%)

    Retourne le score et les composantes.
    """
    scores = {}

    freshness = freshness or {}
    hrv_fresh = float(freshness.get("hrv", 1.0))
    sleep_fresh = float(freshness.get("sleep", 1.0))
    rhr_fresh = float(freshness.get("rhr", 1.0))
    bb_fresh = float(freshness.get("body_battery", 1.0))

    # ── HRV (40%) ────────────────────────────────────────────────
    if hrv_val and hrv_baseline and hrv_baseline > 0:
        ratio = hrv_val / hrv_baseline
        s_hrv = max(0, min(100, (ratio - 0.5) / 0.5 * 100))
    else:
        s_hrv = 50.0  # neutre si pas de données
    # Si la donnée est trop ancienne, on rapproche vers un score neutre
    s_hrv = s_hrv * hrv_fresh + 50.0 * (1.0 - hrv_fresh)

    scores["hrv"] = round(s_hrv, 1)

    # ── Sommeil (30%) ────────────────────────────────────────────
    if sleep_h and sleep_h > 0:
        if sleep_h >= 7.5 and sleep_h <= 9.0:
            s_sleep = 100
        elif sleep_h >= 6.5:
            s_sleep = 60 + 40 * (sleep_h - 6.5) / 1.0
        elif sleep_h >= 5.0:
            s_sleep = 20 + 40 * (sleep_h - 5.0) / 1.5
        else:
            s_sleep = 0
        s_sleep = max(0, min(100, s_sleep))
    else:
        s_sleep = 60.0  # neutre (pas de données)
    s_sleep = s_sleep * sleep_fresh + 60.0 * (1.0 - sleep_fresh)

    scores["sleep"] = round(s_sleep, 1)

    # ── RHR (15%) : plus bas que baseline = mieux ───────────────
    if rhr_val and rhr_baseline and rhr_baseline > 0:
        delta = (float(rhr_val) - float(rhr_baseline)) / float(rhr_baseline)
        if delta <= -0.05:
            s_rhr = 95
        elif delta >= 0.15:
            s_rhr = 20
        else:
            s_rhr = 95 - ((delta + 0.05) / 0.20) * 75
    else:
        s_rhr = 60.0
    s_rhr = _clamp(s_rhr, 0, 100)
    s_rhr = s_rhr * rhr_fresh + 60.0 * (1.0 - rhr_fresh)
    scores["rhr"] = round(s_rhr, 1)

    # ── Body Battery (10%) ───────────────────────────────────────
    if body_battery is not None:
        s_bb = _clamp(float(body_battery), 0.0, 100.0)
    else:
        s_bb = 55.0
    s_bb = s_bb * bb_fresh + 55.0 * (1.0 - bb_fresh)
    scores["body_battery"] = round(s_bb, 1)

    # ── ACWR (20%) ───────────────────────────────────────────────
    if acwr_val <= 0:
        s_acwr = 40  # repos
    elif 0.8 <= acwr_val <= 1.3:
        s_acwr = 100  # zone optimale
    elif acwr_val < 0.8:
        s_acwr = 40 + 60 * (acwr_val / 0.8)
    elif acwr_val <= 1.5:
        s_acwr = 100 - 60 * (acwr_val - 1.3) / 0.2
    else:
        s_acwr = max(0, 40 - 40 * (acwr_val - 1.5))

    s_acwr = max(0, min(100, s_acwr))
    scores["acwr"] = round(s_acwr, 1)

    # ── Score composite ──────────────────────────────────────────
    total = (
        scores["hrv"]         * 0.30 +
        scores["sleep"]       * 0.25 +
        scores["acwr"]        * 0.20 +
        scores["rhr"]         * 0.15 +
        scores["body_battery"] * 0.10
    )
    total = round(total, 1)
    confidence = (
        hrv_fresh * 0.30 +
        sleep_fresh * 0.25 +
        1.0 * 0.20 +  # ACWR calculé sur la charge interne
        rhr_fresh * 0.15 +
        bb_fresh * 0.10
    )

    # Label
    if total >= 85:
        label, color = "Excellent", "#30d158"
    elif total >= 70:
        label, color = "Bon", "#34c759"
    elif total >= 55:
        label, color = "Moyen", "#ff9f0a"
    elif total >= 40:
        label, color = "Faible", "#ff6b35"
    else:
        label, color = "Repos conseillé", "#ff3b30"

    return {
        "score":      total,
        "label":      label,
        "color":      color,
        "components": scores,
        "confidence": round(_clamp(confidence, 0.0, 1.0), 2),
        "freshness": {
            "hrv": round(hrv_fresh, 2),
            "sleep": round(sleep_fresh, 2),
            "rhr": round(rhr_fresh, 2),
            "body_battery": round(bb_fresh, 2),
        },
    }


# ─────────────────────────────────────────────────────────────────
# ANALYSE RUNNING
# ─────────────────────────────────────────────────────────────────
def analyze_running(
    conn: sqlite3.Connection,
    weeks: int = 12,
    end_date: date | None = None,
) -> dict:
    """Analyse les performances de course."""
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    rows = conn.execute("""
        SELECT started_at, duration_s, distance_m, avg_hr, avg_pace_mpm
        FROM activities
        WHERE type='Running'
          AND distance_m > 0
          AND duration_s > 0
          AND date(started_at) >= ?
        ORDER BY started_at DESC
    """, (str(start_date),)).fetchall()

    if not rows:
        return {}

    # Calcul allure si manquante
    paces = []
    for r in rows:
        if r[4]:
            paces.append(r[4])
        elif r[2] > 0 and r[1] > 0:
            paces.append((r[1] / 60) / (r[2] / 1000))

    avg_pace = sum(paces) / len(paces) if paces else None
    best_pace = min(paces) if paces else None

    # Volume mensuel
    total_km = sum((r[2] or 0) for r in rows) / 1000
    km_per_week = total_km / weeks

    # Prédictions Riegel robustes (chaque séance 3k-21.1k)
    def _fmt_time(mins: float) -> str:
        sec = int(round(mins * 60))
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h}h{m:02d}m{s:02d}s" if h > 0 else f"{m}m{s:02d}s"

    riegel_10k_candidates: list[float] = []
    for r in rows:
        dist_m = float(r[2] or 0)
        dur_s = float(r[1] or 0)
        if dist_m < 3000 or dist_m > 21100 or dur_s <= 0:
            continue
        t1 = dur_s / 60.0
        t10 = t1 * ((10000.0 / dist_m) ** RIEGEL_EXPONENT)
        # garde-fous d'allure réaliste
        if 25 <= t10 <= 120:
            riegel_10k_candidates.append(t10)

    pred_10k_base = None
    if riegel_10k_candidates:
        riegel_10k_candidates.sort()
        top_n = max(3, min(len(riegel_10k_candidates), len(riegel_10k_candidates) // 3 or 1))
        pred_10k_base = float(median(riegel_10k_candidates[:top_n]))
    pred_confidence = min(
        1.0,
        max(
            0.25,
            (len(riegel_10k_candidates) / 6.0) * 0.7 + (len(rows) / 10.0) * 0.3,
        ),
    )

    predictions = {}
    if pred_10k_base:
        predictions["10km"] = _fmt_time(pred_10k_base)
        predictions["5km"] = _fmt_time(pred_10k_base * ((5.0 / 10.0) ** RIEGEL_EXPONENT))
        predictions["Semi"] = _fmt_time(pred_10k_base * ((21.1 / 10.0) ** RIEGEL_EXPONENT))
        predictions["Marathon"] = _fmt_time(pred_10k_base * ((42.2 / 10.0) ** RIEGEL_EXPONENT))

    # Format pace string
    def fmt_pace(p):
        if not p:
            return "—"
        m = int(p)
        s = int((p - m) * 60)
        return f"{m}'{s:02d}\""

    recent_acts = [{
        "started_at": r[0], "duration_s": r[1],
        "distance_m": r[2], "avg_hr": r[3], "type": "Running"
    } for r in rows[:5]]

    return {
        "sessions":         len(rows),
        "total_km":         round(total_km, 1),
        "km_per_week":      round(km_per_week, 1),
        "avg_pace":         avg_pace,
        "avg_pace_str":     fmt_pace(avg_pace),
        "best_pace":        best_pace,
        "predictions":      predictions,
        "pred_10k_base_min": round(pred_10k_base, 2) if pred_10k_base else None,
        "pred_10k_candidates_n": len(riegel_10k_candidates),
        "pred_10k_confidence": round(pred_confidence, 2),
        "recent_activities": recent_acts,
    }


def estimate_10k_time(
    base_10k_min: float | None = None,
    avg_pace_mpk: float | None = None,
    ctl: float = 0.0,
    acwr: float = 0.0,
    readiness_score: float = 60.0,
) -> dict:
    """
    Estimation simple 10 km (MVP):
    - base sur allure moyenne récente
    - ajustée par forme (CTL), charge (ACWR) et readiness.
    """
    if base_10k_min:
        total_min = float(base_10k_min)
    elif avg_pace_mpk:
        total_min = float(avg_pace_mpk) * 10.0
    else:
        return {"minutes": None, "label": "—"}

    # Ajustement forme (CTL)
    factor = 1.0
    if ctl >= 40:
        factor *= 0.97
    elif ctl <= 15:
        factor *= 1.03

    # Ajustement charge
    if acwr > 1.4:
        factor *= 1.03
    elif 0.8 <= acwr <= 1.2:
        factor *= 0.99

    # Ajustement readiness
    if readiness_score >= 75:
        factor *= 0.98
    elif readiness_score < 55:
        factor *= 1.02

    total_min *= factor
    total_sec = int(round(total_min * 60))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    label = f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"
    return {
        "minutes": round(total_min, 2),
        "label": label,
        "pace_mpk": round(total_min / 10.0, 2),
        "factor": round(factor, 3),
    }


# ─────────────────────────────────────────────────────────────────
# SAUVEGARDE PMC EN BASE
# ─────────────────────────────────────────────────────────────────
def save_daily_load(conn: sqlite3.Connection, pmc: list[dict]) -> None:
    """Sauvegarde le PMC calculé dans la table daily_load."""
    cursor = conn.cursor()
    for row in pmc:
        cursor.execute("""
            INSERT OR REPLACE INTO daily_load (date, tss, ctl, atl, tsb)
            VALUES (?,?,?,?,?)
        """, (row["date"], row["tss"], row["ctl"], row["atl"], row["tsb"]))
    conn.commit()


# ─────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────────────────────────
def run(
    db_path:   Path = DB_PATH,
    verbose:   bool = True,
) -> dict:
    """Calcul complet de la charge d'entraînement."""
    conn = sqlite3.connect(str(db_path))
    today = date.today()

    # 1. TSS quotidien
    daily_tss = build_daily_tss(conn)
    print(f"   TSS calculés pour {len(daily_tss)} jours d'activité")

    # 2. PMC
    pmc = compute_pmc(daily_tss, end_date=today)
    save_daily_load(conn, pmc)

    today_pmc = pmc[-1] if pmc else {"ctl": 0, "atl": 0, "tsb": 0, "tss": 0}
    print(f"   PMC → CTL: {today_pmc['ctl']} | ATL: {today_pmc['atl']} | TSB: {today_pmc['tsb']}")

    # 3. ACWR
    acwr_data = compute_acwr(daily_tss, end_date=today)
    print(
        f"   ACWR: {acwr_data['acwr']} (zone: {acwr_data['zone']}, "
        f"roll={acwr_data.get('acwr_roll')}, ewma={acwr_data.get('acwr_ewma')})"
    )

    # 4. Métriques santé
    health = get_health_metrics(conn)
    print(
        f"   HRV: {health['hrv']} ms (J-{health.get('hrv_days_old','?')}) | "
        f"RHR: {health['rhr']} bpm (J-{health.get('rhr_days_old','?')}) | "
        f"Sommeil: {health['sleep_h']} h (J-{health.get('sleep_days_old','?')})"
    )

    # 5. Wakeboard Readiness
    wbs = compute_wakeboard_score(
        hrv_val=health["hrv"],
        hrv_baseline=health["hrv_baseline"],
        sleep_h=health["sleep_h"],
        acwr_val=acwr_data["acwr"],
        rhr_val=health.get("rhr"),
        rhr_baseline=health.get("rhr_baseline"),
        body_battery=health.get("body_battery"),
        freshness={
            "hrv": health.get("hrv_freshness", 1.0),
            "sleep": health.get("sleep_freshness", 1.0),
            "rhr": health.get("rhr_freshness", 1.0),
            "body_battery": health.get("body_battery_freshness", 1.0),
        },
    )
    conf = int(round(float(wbs.get("confidence", 1.0)) * 100))
    print(f"   Wakeboard Score: {wbs['score']}/100 ({wbs['label']}, confiance {conf}%)")

    # 6. Running
    running = analyze_running(conn, weeks=12)
    if running:
        run_conf = int(round(float(running.get("pred_10k_confidence", 0.25)) * 100))
        print(
            f"   Running: {running['km_per_week']:.1f} km/sem | "
            f"allure moy: {running['avg_pace']:.2f} min/km | "
            f"10k conf: {run_conf}%"
        )
        running["estimated_10k"] = estimate_10k_time(
            base_10k_min=running.get("pred_10k_base_min"),
            avg_pace_mpk=running.get("avg_pace"),
            ctl=float(today_pmc.get("ctl", 0) or 0),
            acwr=float(acwr_data.get("acwr", 0) or 0),
            readiness_score=float(wbs.get("score", 0) or 0),
        )

    # 7. Totaux historiques
    total_acts = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    total_km_all = conn.execute(
        "SELECT COALESCE(SUM(distance_m),0)/1000 FROM activities WHERE distance_m>0"
    ).fetchone()[0]
    strength_count = conn.execute("SELECT COUNT(*) FROM strength_sessions").fetchone()[0]

    # 8. Activités récentes (toutes types)
    recent_rows = conn.execute("""
        SELECT type, name, started_at, duration_s, distance_m, avg_hr
        FROM activities ORDER BY started_at DESC LIMIT 10
    """).fetchall()
    recent_activities = [{
        "type": r[0], "name": r[1], "started_at": r[2],
        "duration_s": r[3], "distance_m": r[4], "avg_hr": r[5],
    } for r in recent_rows]

    conn.close()

    return {
        "pmc":               today_pmc,
        "pmc_series":        pmc,
        "acwr":              acwr_data,
        "health":            health,
        "wakeboard":         wbs,
        "running":           running or {},
        "daily_tss":         daily_tss,
        "total_activities":  total_acts,
        "total_km":          round(total_km_all, 0),
        "strength_sessions": strength_count,
        "recent_activities": recent_activities,
        "garmin_connected":  False,  # mis à jour si Garmin OK
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DB_PATH))
    args = p.parse_args()
    result = run(Path(args.db))
