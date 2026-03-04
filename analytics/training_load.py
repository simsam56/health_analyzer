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

ROOT    = Path(__file__).parent.parent
DB_PATH = ROOT / "athlete.db"

# ─────────────────────────────────────────────────────────────────
# CONSTANTES PMC
# ─────────────────────────────────────────────────────────────────
CTL_DAYS = 42    # Chronic Training Load (fitness)
ATL_DAYS = 7     # Acute Training Load (fatigue)

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


# ─────────────────────────────────────────────────────────────────
# CALCUL TSS PROXY
# ─────────────────────────────────────────────────────────────────
def tss_from_activity(row: dict) -> float:
    """
    TSS proxy depuis les données disponibles.
    Priorité : training_load > formula FC × durée > calories > durée.
    """
    # 1. Training Load Apple Health (meilleure source)
    if row.get("training_load") and row["training_load"] > 0:
        return float(row["training_load"]) / 10.0  # normalise ~50-150 TSS

    act_type  = (row.get("type") or "").lower()
    duration  = row.get("duration_s") or 0
    avg_hr    = row.get("avg_hr") or 0
    calories  = row.get("calories") or 0
    dist_m    = row.get("distance_m") or 0

    if duration <= 0:
        return 0.0

    dur_h = duration / 3600

    # 2. Musculation : basé sur le nombre de séries et la fatigue neuronale
    if "strength" in act_type or "training" in act_type:
        name = (row.get("name") or "").lower()
        # Multiplier neuromusculaire
        mult = 1.0
        for key, val in NEURAL_FATIGUE_MULTIPLIERS.items():
            if key in name:
                mult = val
                break
        tss = dur_h * 60 * mult * 0.8  # ~48 TSS pour 1h muscu jambes
        return round(min(tss, 150), 1)

    # 3. FC disponible → formule classique
    if avg_hr > 0:
        # TRIMP simplifié : HR ratio × durée
        hr_ratio = avg_hr / 185  # 185 = FC max estimée
        tss = dur_h * 60 * hr_ratio * hr_ratio * 100
        return round(min(tss, 200), 1)

    # 4. Calories
    if calories > 0:
        return round(min(calories / 8.0, 150), 1)

    # 5. Durée seule (cardio ~50 TSS/h)
    if "running" in act_type or "cycling" in act_type:
        return round(min(dur_h * 55, 150), 1)

    return round(min(dur_h * 35, 100), 1)


# ─────────────────────────────────────────────────────────────────
# PMC (PERFORMANCE MANAGEMENT CHART)
# ─────────────────────────────────────────────────────────────────
def build_daily_tss(conn: sqlite3.Connection) -> dict[str, float]:
    """Agrège le TSS par jour depuis toutes les activités."""
    rows = conn.execute("""
        SELECT date(started_at) AS day, type, name,
               training_load, avg_hr, duration_s, calories, distance_m
        FROM activities
        WHERE started_at IS NOT NULL
        ORDER BY day
    """).fetchall()

    daily_tss: dict[str, float] = defaultdict(float)

    for row in rows:
        d = {
            "type": row[1], "name": row[2], "training_load": row[3],
            "avg_hr": row[4], "duration_s": row[5], "calories": row[6],
            "distance_m": row[7],
        }
        tss = tss_from_activity(d)
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

    # Facteurs de lissage EWM
    k_ctl = 2 / (CTL_DAYS + 1)
    k_atl = 2 / (ATL_DAYS + 1)

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

    acute   = avg_days(7)
    chronic = avg_days(28)

    acwr = acute / chronic if chronic > 0.5 else 0.0

    zone = "repos"
    for z, (lo, hi) in ACWR_ZONES.items():
        if lo <= acwr < hi:
            zone = z
            break

    return {
        "acwr":    round(acwr, 2),
        "acute":   round(acute, 1),
        "chronic": round(chronic, 1),
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

    def latest_metric(metric: str, windows=[7, 14, 30, 60, 90, 180, 365]) -> tuple[float | None, str | None]:
        for w in windows:
            cutoff = (end_date - timedelta(days=w)).strftime("%Y-%m-%d")
            row = conn.execute("""
                SELECT AVG(value), MAX(date)
                FROM health_metrics
                WHERE metric=? AND date>=? AND date<=?
            """, (metric, cutoff, str(end_date))).fetchone()
            if row and row[0] is not None:
                return round(float(row[0]), 2), row[1]
        # Fallback : 5 dernières valeurs sans limite de date
        row = conn.execute("""
            SELECT AVG(value), MAX(date)
            FROM (SELECT value, date FROM health_metrics
                  WHERE metric=? ORDER BY date DESC LIMIT 5)
        """, (metric,)).fetchone()
        if row and row[0] is not None:
            return round(float(row[0]), 2), row[1]
        return None, None

    hrv_val,     hrv_date     = latest_metric("hrv_sdnn")
    rhr_val,     rhr_date     = latest_metric("rhr")
    vo2max_val,  vo2max_date  = latest_metric("vo2max")
    sleep_val,   sleep_date   = latest_metric("sleep_h")
    weight_val,  weight_date  = latest_metric("weight_kg")

    # Baseline HRV (percentile 50 des 6 derniers mois)
    hrv_baseline = conn.execute("""
        SELECT AVG(value) FROM (
            SELECT value FROM health_metrics
            WHERE metric='hrv_sdnn'
            ORDER BY date DESC LIMIT 60
        )
    """).fetchone()
    hrv_baseline = float(hrv_baseline[0]) if hrv_baseline and hrv_baseline[0] else hrv_val

    return {
        "hrv":          hrv_val,
        "hrv_date":     hrv_date,
        "hrv_baseline": hrv_baseline,
        "rhr":          rhr_val,
        "rhr_date":     rhr_date,
        "vo2max":       vo2max_val,
        "vo2max_date":  vo2max_date,
        "sleep_h":      sleep_val,
        "sleep_date":   sleep_date,
        "weight_kg":    weight_val,
    }


# ─────────────────────────────────────────────────────────────────
# WAKEBOARD READINESS SCORE
# ─────────────────────────────────────────────────────────────────
def compute_wakeboard_score(
    hrv_val:     float | None,
    hrv_baseline:float | None,
    sleep_h:     float | None,
    acwr_val:    float,
) -> dict:
    """
    Wakeboard Readiness Score : 0-100

    Composantes :
      - HRV  (40%) : HRV / baseline × 50 + 50, capped 0-100
      - Sommeil (30%) : 8h idéal, pénalité si < 7h ou > 9.5h
      - ACWR (30%) : optimal zone 0.8-1.3

    Retourne le score et les composantes.
    """
    scores = {}

    # ── HRV (40%) ────────────────────────────────────────────────
    if hrv_val and hrv_baseline and hrv_baseline > 0:
        ratio = hrv_val / hrv_baseline
        s_hrv = max(0, min(100, (ratio - 0.5) / 0.5 * 100))
    else:
        s_hrv = 50.0  # neutre si pas de données

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

    scores["sleep"] = round(s_sleep, 1)

    # ── ACWR (30%) ───────────────────────────────────────────────
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
        scores["hrv"]   * 0.40 +
        scores["sleep"] * 0.30 +
        scores["acwr"]  * 0.30
    )
    total = round(total, 1)

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

    # Prédictions Riegel (depuis meilleure allure récente sur 5-10km)
    long_runs = [r for r in rows if r[2] and r[2] >= 5000]
    predictions = {}
    if long_runs and best_pace:
        # t = best_pace * distance
        for dist_km, label in [(5, "5km"), (10, "10km"), (21.1, "Semi"), (42.2, "Marathon")]:
            t_min = best_pace * dist_km
            h = int(t_min // 60)
            m = int(t_min % 60)
            s = int((t_min * 60) % 60)
            predictions[label] = f"{h}h{m:02d}m{s:02d}s" if h > 0 else f"{m}m{s:02d}s"

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
        "recent_activities": recent_acts,
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
    print(f"   ACWR: {acwr_data['acwr']} (zone: {acwr_data['zone']})")

    # 4. Métriques santé
    health = get_health_metrics(conn)
    print(f"   HRV: {health['hrv']} ms | RHR: {health['rhr']} bpm | Sommeil: {health['sleep_h']} h")

    # 5. Wakeboard Readiness
    wbs = compute_wakeboard_score(
        hrv_val=health["hrv"],
        hrv_baseline=health["hrv_baseline"],
        sleep_h=health["sleep_h"],
        acwr_val=acwr_data["acwr"],
    )
    print(f"   Wakeboard Score: {wbs['score']}/100 ({wbs['label']})")

    # 6. Running
    running = analyze_running(conn, weeks=12)
    if running:
        print(f"   Running: {running['km_per_week']:.1f} km/sem | allure moy: {running['avg_pace']:.2f} min/km")

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
