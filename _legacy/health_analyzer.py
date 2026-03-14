#!/usr/bin/env python3
"""
Health Analytics Dashboard Generator
Analyse les données Apple Health et génère un dashboard HTML interactif.
Auteur : Simon Hingant — Généré automatiquement chaque dimanche soir.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from defusedxml import ElementTree as ET

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
EXPORT_PATH = SCRIPT_DIR / "export.xml"
OUTPUT_DIR = SCRIPT_DIR / "reports"
BIRTH_DATE = date(1992, 10, 28)

WORKOUT_LABELS = {
    "HKWorkoutActivityTypeRunning": "🏃 Course",
    "HKWorkoutActivityTypeCrossTraining": "🏋️ Cross Training",
    "HKWorkoutActivityTypeOther": "⚡ Autre",
    "HKWorkoutActivityTypeSwimming": "🏊 Natation",
    "HKWorkoutActivityTypeCycling": "🚴 Vélo",
    "HKWorkoutActivityTypeTraditionalStrengthTraining": "💪 Musculation",
    "HKWorkoutActivityTypeWalking": "🚶 Marche",
    "HKWorkoutActivityTypeYoga": "🧘 Yoga",
    "HKWorkoutActivityTypeSnowboarding": "🏂 Snowboard",
    "HKWorkoutActivityTypeDownhillSkiing": "⛷️ Ski",
    "HKWorkoutActivityTypeSnowSports": "🎿 Sports neige",
    "HKWorkoutActivityTypeSkatingSports": "⛸️ Patinage",
    "HKWorkoutActivityTypeElliptical": "🔄 Elliptique",
    "HKWorkoutActivityTypeTennis": "🎾 Tennis",
    "HKWorkoutActivityTypeRowing": "🚣 Aviron",
}

TARGET_RECORD_TYPES = {
    "HKQuantityTypeIdentifierHeartRate",
    "HKQuantityTypeIdentifierRestingHeartRate",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
    "HKQuantityTypeIdentifierVO2Max",
    "HKQuantityTypeIdentifierStepCount",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKQuantityTypeIdentifierBodyMass",
    "HKQuantityTypeIdentifierAppleExerciseTime",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def age_years(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def format_pace(pace_decimal: float) -> str:
    """Convertit les min/km décimaux en format mm:ss/km"""
    if pd.isna(pace_decimal) or pace_decimal <= 0 or pace_decimal > 30:
        return "—"
    m = int(pace_decimal)
    s = int(round((pace_decimal - m) * 60))
    return f"{m}:{s:02d}/km"


def safe_float(val, default=0.0):
    try:
        return float(val or default)
    except (ValueError, TypeError):
        return default


def score_color(s: float) -> str:
    if s >= 75:
        return "#22c55e"
    elif s >= 50:
        return "#f59e0b"
    return "#ef4444"


def score_label(s: float) -> str:
    if s >= 80:
        return "Excellent 🔥"
    elif s >= 65:
        return "Bon 💪"
    elif s >= 50:
        return "Moyen ⚡"
    return "À récupérer 😴"


def pct_change(a, b) -> str:
    try:
        if b == 0:
            return "~"
        pct = ((float(a) - float(b)) / float(b)) * 100
        return f"+{pct:.0f}%" if pct >= 0 else f"{pct:.0f}%"
    except:
        return "~"


# ─────────────────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────────────────
def parse_health_data(export_path: Path):
    """Parse en streaming l'export Apple Health (gros fichier ~800MB)."""
    print(f"📂 Parsing {export_path.name} ({export_path.stat().st_size / 1e6:.0f} MB)…")
    print("   (Cette opération prend ~2-3 min la première fois)")

    workouts = []
    records = defaultdict(list)
    count = 0

    for _event, elem in ET.iterparse(str(export_path), events=("end",)):
        tag = elem.tag

        if tag == "Workout":
            w = {
                "type": elem.get("workoutActivityType", ""),
                "start": elem.get("startDate", ""),
                "end": elem.get("endDate", ""),
                "duration_min": safe_float(elem.get("duration")),
                "distance_km": safe_float(elem.get("totalDistance")),
                "calories": safe_float(elem.get("totalEnergyBurned")),
                "source": elem.get("sourceName", ""),
                "avg_hr": None,
            }
            # Extraire distance, calories, FC depuis WorkoutStatistics
            for stat in elem.findall("WorkoutStatistics"):
                stype = stat.get("type", "")
                if (
                    "DistanceWalkingRunning" in stype
                    or "DistanceCycling" in stype
                    or "DistanceSwimming" in stype
                ):
                    d = safe_float(stat.get("sum"))
                    unit = stat.get("unit", "km")
                    if d > 0:
                        # Convert miles to km if needed
                        w["distance_km"] = d * 1.60934 if unit in ("mi", "miles") else d
                elif "ActiveEnergyBurned" in stype:
                    c = safe_float(stat.get("sum"))
                    if c > 0 and w["calories"] == 0:
                        w["calories"] = c
                elif "HeartRate" in stype:
                    hr = safe_float(stat.get("average"))
                    if hr > 0:
                        w["avg_hr"] = hr
            workouts.append(w)
            elem.clear()

        elif tag == "Record":
            rtype = elem.get("type", "")
            if rtype in TARGET_RECORD_TYPES:
                records[rtype].append(
                    {
                        "date": elem.get("startDate", ""),
                        "value": safe_float(elem.get("value")),
                    }
                )
            elem.clear()
            count += 1
            if count % 500_000 == 0:
                print(f"   …{count:,} records traités")

    print(f"✅ {len(workouts)} entraînements · {sum(len(v) for v in records.values()):,} records")
    return workouts, records


# ─────────────────────────────────────────────────────────────────────────────
# DATAFRAMES
# ─────────────────────────────────────────────────────────────────────────────
def build_dataframes(workouts, records):
    """Construit les DataFrames propres depuis les données brutes."""

    # ── Workouts ──────────────────────────────────────────────────────────────
    df_w = pd.DataFrame(workouts) if workouts else pd.DataFrame()
    if not df_w.empty:
        # Parse timezone-aware strings, then strip tz for consistent comparisons
        s = pd.to_datetime(df_w["start"], utc=False, errors="coerce")
        df_w["start"] = s.dt.tz_convert("UTC").dt.tz_localize(None) if s.dt.tz is not None else s
        e = pd.to_datetime(df_w["end"], utc=False, errors="coerce")
        df_w["end"] = e.dt.tz_convert("UTC").dt.tz_localize(None) if e.dt.tz is not None else e
        df_w["date"] = df_w["start"].dt.date
        df_w["year"] = df_w["start"].dt.year
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df_w["month"] = df_w["start"].dt.to_period("M").astype(str)
        df_w["label"] = df_w["type"].map(WORKOUT_LABELS).fillna(df_w["type"])
        df_w["date_obj"] = df_w["date"]

        # Allure course en min/km
        mask = (df_w["type"] == "HKWorkoutActivityTypeRunning") & (df_w["distance_km"] > 0.5)
        df_w["pace_min_km"] = np.where(mask, df_w["duration_min"] / df_w["distance_km"], np.nan)
        # Filtre allures aberrantes (< 3 min/km ou > 15 min/km)
        df_w.loc[(df_w["pace_min_km"] < 3) | (df_w["pace_min_km"] > 15), "pace_min_km"] = np.nan

    # ── Records journaliers ───────────────────────────────────────────────────
    SUM_TYPES = {
        "HKQuantityTypeIdentifierStepCount",
        "HKQuantityTypeIdentifierActiveEnergyBurned",
        "HKQuantityTypeIdentifierAppleExerciseTime",
    }

    daily = {}
    for key, recs in records.items():
        if not recs:
            continue
        df_r = pd.DataFrame(recs)
        d_col = pd.to_datetime(df_r["date"], utc=False, errors="coerce")
        if d_col.dt.tz is not None:
            d_col = d_col.dt.tz_convert("UTC").dt.tz_localize(None)
        df_r["date"] = d_col.dt.date
        agg = df_r.groupby("date")["value"]
        daily[key] = (agg.sum() if key in SUM_TYPES else agg.mean()).reset_index()

    return df_w, daily


# ─────────────────────────────────────────────────────────────────────────────
# CHARGE D'ENTRAÎNEMENT (CTL / ATL / TSB)
# ─────────────────────────────────────────────────────────────────────────────
def calculate_training_load(df_workouts: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule la charge d'entraînement selon le modèle Bannister (PMC) :
    - CTL (Chronic Training Load / Fitness)  : EWM 42 jours
    - ATL (Acute Training Load / Fatigue)    : EWM  7 jours
    - TSB (Training Stress Balance / Forme)  : CTL - ATL
    Proxy TSS : 500 kcal ≈ 100 points TSS
    """
    if df_workouts.empty:
        return pd.DataFrame()

    daily_load = df_workouts.groupby("date")["calories"].sum().reset_index()
    daily_load.columns = ["date", "kcal"]
    daily_load["date"] = pd.to_datetime(daily_load["date"])

    date_range = pd.date_range(daily_load["date"].min(), date.today(), freq="D")
    daily_load = daily_load.set_index("date").reindex(date_range, fill_value=0).reset_index()
    daily_load.columns = ["date", "kcal"]
    daily_load["tss"] = daily_load["kcal"] / 5.0

    daily_load["ctl"] = daily_load["tss"].ewm(span=42, min_periods=1).mean()
    daily_load["atl"] = daily_load["tss"].ewm(span=7, min_periods=1).mean()
    daily_load["tsb"] = daily_load["ctl"] - daily_load["atl"]

    return daily_load


# ─────────────────────────────────────────────────────────────────────────────
# SCORES
# ─────────────────────────────────────────────────────────────────────────────
def calculate_form_score(daily_metrics, training_load, df_workouts):
    """Score de forme composite (0-100) basé sur HRV, FC repos, TSB, régularité."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    scores = {}

    HRV = "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
    RHR = "HKQuantityTypeIdentifierRestingHeartRate"

    # HRV (↑ = mieux récupéré)
    if HRV in daily_metrics and not daily_metrics[HRV].empty:
        df_h = daily_metrics[HRV].copy()
        df_h["date"] = pd.to_datetime(df_h["date"]).dt.date
        recent = df_h[df_h["date"] >= week_ago]["value"].mean()
        baseline = df_h["value"].quantile(0.5)
        if baseline > 0:
            scores["hrv"] = float(np.clip((recent / baseline) * 50 + 50, 0, 100))

    # FC repos (↓ = meilleure forme)
    if RHR in daily_metrics and not daily_metrics[RHR].empty:
        df_r = daily_metrics[RHR].copy()
        df_r["date"] = pd.to_datetime(df_r["date"]).dt.date
        recent = df_r[df_r["date"] >= week_ago]["value"].mean()
        baseline = df_r["value"].quantile(0.5)
        if recent > 0:
            scores["rhr"] = float(np.clip((baseline / recent) * 50 + 50, 0, 100))

    # TSB (forme CTL-ATL)
    if not training_load.empty:
        recent_tsb = training_load[training_load["date"].dt.date >= week_ago]["tsb"].mean()
        scores["tsb"] = float(np.clip(50 + recent_tsb * 1.5, 0, 100))

    # Régularité (entraînements sur 4 semaines)
    if not df_workouts.empty:
        four_weeks_ago = today - timedelta(days=28)
        n = len(df_workouts[df_workouts["date_obj"] >= four_weeks_ago])
        scores["régularité"] = float(np.clip(n * 7, 0, 100))  # 14 séances = 100

    if not scores:
        return 50, {}

    weights = {"hrv": 0.35, "rhr": 0.25, "tsb": 0.25, "régularité": 0.15}
    total_w = sum(weights.get(k, 0.1) for k in scores)
    fs = sum(scores[k] * weights.get(k, 0.1) for k in scores) / total_w
    fs = 50.0 if (np.isnan(fs) or np.isinf(fs)) else fs
    return int(round(float(np.clip(fs, 0, 100)))), scores


def calculate_wakeboard_readiness(form_score, df_workouts, daily_metrics):
    """
    Score de préparation wakeboard (0-100).
    Le wakeboard demande : cardio, force haut du corps, équilibre, faible fatigue.
    """
    today = date.today()
    four_weeks_ago = today - timedelta(days=28)
    components = {}

    components["forme_générale"] = float(form_score)

    # Force haut du corps
    if not df_workouts.empty:
        strength_types = {
            "HKWorkoutActivityTypeTraditionalStrengthTraining",
            "HKWorkoutActivityTypeCrossTraining",
        }
        n_strength = len(
            df_workouts[
                (df_workouts["date_obj"] >= four_weeks_ago)
                & (df_workouts["type"].isin(strength_types))
            ]
        )
        components["force_haut_corps"] = float(np.clip(n_strength * 14, 0, 100))

    # VO2Max (cardio)
    VO2 = "HKQuantityTypeIdentifierVO2Max"
    if VO2 in daily_metrics and not daily_metrics[VO2].empty:
        latest_vo2 = daily_metrics[VO2]["value"].iloc[-1]
        age = age_years(BIRTH_DATE)
        excellent = 52 if age < 35 else (48 if age < 45 else 44)
        components["cardio_vo2max"] = float(np.clip((latest_vo2 / excellent) * 100, 0, 100))

    # Sports aquatiques / activité récente
    if not df_workouts.empty:
        water_types = {
            "HKWorkoutActivityTypeSwimming",
            "HKWorkoutActivityTypeOther",
            "HKWorkoutActivityTypeCycling",
            "HKWorkoutActivityTypeRunning",
        }
        n_active = len(
            df_workouts[
                (df_workouts["date_obj"] >= four_weeks_ago)
                & (df_workouts["type"].isin(water_types))
            ]
        )
        components["activité_cardio"] = float(np.clip(n_active * 9, 0, 100))

    weights = {
        "forme_générale": 0.30,
        "force_haut_corps": 0.25,
        "cardio_vo2max": 0.25,
        "activité_cardio": 0.20,
    }
    total_w = sum(weights.get(k, 0.1) for k in components)
    ws = sum(components[k] * weights.get(k, 0.1) for k in components) / total_w
    ws = 50.0 if (np.isnan(ws) or np.isinf(ws)) else ws
    return int(round(float(np.clip(ws, 0, 100)))), components


# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION DU RAPPORT HTML
# ─────────────────────────────────────────────────────────────────────────────
def generate_report(df_workouts, daily_metrics, training_load, output_path: Path):
    today = date.today()

    # ── Scores ────────────────────────────────────────────────────────────────
    form_score, form_comp = calculate_form_score(daily_metrics, training_load, df_workouts)
    wake_score, wake_comp = calculate_wakeboard_readiness(form_score, df_workouts, daily_metrics)

    # ── Filtre séances de course ──────────────────────────────────────────────
    run_df = df_workouts[
        (df_workouts["type"] == "HKWorkoutActivityTypeRunning") & df_workouts["pace_min_km"].notna()
    ].copy()

    # ── Cette semaine ──────────────────────────────────────────────────────────
    week_start = today - timedelta(days=today.weekday())
    this_week = df_workouts[df_workouts["date_obj"] >= week_start]
    tw_workouts = len(this_week)
    tw_duration = round(this_week["duration_min"].sum() / 60, 1)
    tw_calories = int(this_week["calories"].sum())

    # ── Allure récente ────────────────────────────────────────────────────────
    if not run_df.empty and len(run_df) >= 3:
        last5 = run_df.nlargest(5, "start")
        avg_pace = last5["pace_min_km"].mean()
        all_pace = run_df["pace_min_km"].mean()
        pace_str = format_pace(avg_pace)
        trend_str = "📈 En progression" if avg_pace < all_pace else "Stable"
    else:
        pace_str = "—"
        trend_str = "Pas encore de données"

    # ── Métriques clés ────────────────────────────────────────────────────────
    def latest_metric(key):
        df = daily_metrics.get(key)
        if df is None or df.empty:
            return None
        return df["value"].iloc[-1]

    vo2 = latest_metric("HKQuantityTypeIdentifierVO2Max")
    rhr = latest_metric("HKQuantityTypeIdentifierRestingHeartRate")
    hrv = latest_metric("HKQuantityTypeIdentifierHeartRateVariabilitySDNN")
    vo2_str = f"{vo2:.1f}" if vo2 else "—"
    rhr_str = f"{int(rhr)}" if rhr else "—"
    hrv_str = f"{int(hrv)}" if hrv else "—"

    # ── Comparaison annuelle ───────────────────────────────────────────────────
    def year_stats(y):
        df = df_workouts[df_workouts["year"] == y]
        run = df[df["type"] == "HKWorkoutActivityTypeRunning"]
        return {
            "workouts": len(df),
            "total_km": round(df["distance_km"].sum(), 1),
            "total_h": round(df["duration_min"].sum() / 60, 1),
            "run_km": round(run["distance_km"].sum(), 1),
            "total_cal": int(df["calories"].sum()),
        }

    this_y = year_stats(today.year)
    last_y = year_stats(today.year - 1)

    yoy_metrics = [
        {
            "label": "Entraînements",
            "this": this_y["workouts"],
            "last": last_y["workouts"],
            "unit": "",
        },
        {
            "label": "Km de course",
            "this": this_y["run_km"],
            "last": last_y["run_km"],
            "unit": " km",
        },
        {
            "label": "Heures sport",
            "this": this_y["total_h"],
            "last": last_y["total_h"],
            "unit": " h",
        },
        {
            "label": "Kcal brûlées",
            "this": this_y["total_cal"],
            "last": last_y["total_cal"],
            "unit": " kcal",
        },
    ]
    for m in yoy_metrics:
        m["change"] = pct_change(m["this"], m["last"])

    # ── Données graphiques ────────────────────────────────────────────────────
    cutoff_24m = pd.Timestamp(today - timedelta(days=730))
    cutoff_12m = pd.Timestamp(today - timedelta(days=365))
    cutoff_6m = pd.Timestamp(today - timedelta(days=180))
    cutoff_26w = pd.Timestamp(today - timedelta(weeks=26))

    # Course : allure + distance hebdo
    run_chart = run_df[run_df["start"] >= cutoff_24m].sort_values("start").copy()
    run_chart["pace_roll"] = run_chart["pace_min_km"].rolling(5, min_periods=1).mean()

    if not run_df.empty:
        run_df2 = run_df.copy()
        run_df2["week_start"] = run_df2["start"].apply(
            lambda d: (d - timedelta(days=d.weekday())).date()
        )
        wkly_run = (
            run_df2[run_df2["start"] >= cutoff_26w]
            .groupby("week_start")["distance_km"]
            .sum()
            .reset_index()
        )
        wkly_run_dates = [str(d) for d in wkly_run["week_start"]]
        wkly_run_km = wkly_run["distance_km"].round(1).tolist()
    else:
        wkly_run_dates, wkly_run_km = [], []

    # Charge d'entraînement
    load_12m = (
        training_load[training_load["date"] >= cutoff_12m].copy()
        if not training_load.empty
        else pd.DataFrame()
    )

    # HRV & FC repos (6 derniers mois)
    def rolling_series(key, window=7, fallback_days=730):
        df = daily_metrics.get(key)
        if df is None or df.empty:
            return [], [], []
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        # Try 6 months; if sparse, fall back to longer window
        recent = df[df["date"] >= cutoff_6m]
        if len(recent) < 5:
            recent = df[df["date"] >= pd.Timestamp(today - timedelta(days=fallback_days))]
        recent = recent.sort_values("date")
        recent["rolling"] = recent["value"].rolling(window, min_periods=1).mean()
        return (
            recent["date"].dt.strftime("%Y-%m-%d").tolist(),
            recent["value"].round(1).tolist(),
            recent["rolling"].round(1).tolist(),
        )

    hrv_dates, hrv_vals, hrv_roll = rolling_series(
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
    )
    rhr_dates, rhr_vals, rhr_roll = rolling_series("HKQuantityTypeIdentifierRestingHeartRate")

    # VO2Max historique
    vo2_key = "HKQuantityTypeIdentifierVO2Max"
    if vo2_key in daily_metrics and not daily_metrics[vo2_key].empty:
        vo2_df = daily_metrics[vo2_key].copy()
        vo2_df["date"] = pd.to_datetime(vo2_df["date"])
        vo2_df = vo2_df.sort_values("date")
        vo2_dates = vo2_df["date"].dt.strftime("%Y-%m-%d").tolist()
        vo2_vals = vo2_df["value"].round(1).tolist()
    else:
        vo2_dates, vo2_vals = [], []

    # Répartition activités (12 mois)
    act12 = df_workouts[df_workouts["date_obj"] >= today - timedelta(days=365)]
    act_grp = act12.groupby("label")["duration_min"].sum().sort_values(ascending=False)
    act_labels = act_grp.index.tolist()
    act_hours = (act_grp / 60).round(1).tolist()

    # Calories hebdo
    df_workouts["week_start_ts"] = df_workouts["start"].apply(
        lambda d: d - timedelta(days=d.weekday())
    )
    wcal = (
        df_workouts[df_workouts["week_start_ts"] >= cutoff_26w]
        .groupby("week_start_ts")["calories"]
        .sum()
        .reset_index()
    )
    wcal_dates = wcal["week_start_ts"].dt.strftime("%Y-%m-%d").tolist()
    wcal_vals = wcal["calories"].round().astype(int).tolist()

    # Steps (derniers 3 mois)
    steps_key = "HKQuantityTypeIdentifierStepCount"
    if steps_key in daily_metrics:
        sd = daily_metrics[steps_key].copy()
        sd["date"] = pd.to_datetime(sd["date"])
        sd = sd[sd["date"] >= pd.Timestamp(today - timedelta(days=90))].sort_values("date")
        steps_dates = sd["date"].dt.strftime("%Y-%m-%d").tolist()
        steps_vals = sd["value"].astype(int).tolist()
    else:
        steps_dates, steps_vals = [], []

    # 10 dernières séances
    recent10 = df_workouts.nlargest(10, "start")[
        ["label", "date", "duration_min", "distance_km", "calories", "pace_min_km", "avg_hr"]
    ].copy()
    recent10["date"] = pd.to_datetime(recent10["date"]).apply(lambda d: d.strftime("%d/%m/%Y"))
    recent10["duration"] = recent10["duration_min"].apply(
        lambda x: f"{int(x // 60)}h{int(x % 60):02d}" if x >= 60 else f"{int(x)} min"
    )
    recent10["dist_str"] = recent10["distance_km"].apply(lambda x: f"{x:.1f} km" if x > 0 else "—")
    recent10["pace_str"] = recent10["pace_min_km"].apply(format_pace)
    recent10["cal_str"] = recent10["calories"].apply(lambda x: f"{int(x)}" if x > 0 else "—")
    recent10["hr_str"] = recent10["avg_hr"].apply(
        lambda x: f"{int(x)} bpm" if (pd.notna(x) and x and x > 0) else "—"
    )

    table_rows = recent10[
        ["label", "date", "duration", "dist_str", "pace_str", "cal_str", "hr_str"]
    ].to_dict("records")

    # JSON pour Plotly
    cd = {
        "run_dates": run_chart["start"].dt.strftime("%Y-%m-%d").tolist(),
        "run_pace": run_chart["pace_min_km"].round(2).tolist(),
        "run_pace_roll": run_chart["pace_roll"].round(2).tolist(),
        "run_dist": run_chart["distance_km"].round(2).tolist(),
        "load_dates": load_12m["date"].dt.strftime("%Y-%m-%d").tolist()
        if not load_12m.empty
        else [],
        "ctl": load_12m["ctl"].round(1).tolist() if not load_12m.empty else [],
        "atl": load_12m["atl"].round(1).tolist() if not load_12m.empty else [],
        "tsb": load_12m["tsb"].round(1).tolist() if not load_12m.empty else [],
        "hrv_dates": hrv_dates,
        "hrv_vals": hrv_vals,
        "hrv_roll": hrv_roll,
        "rhr_dates": rhr_dates,
        "rhr_vals": rhr_vals,
        "rhr_roll": rhr_roll,
        "vo2_dates": vo2_dates,
        "vo2_vals": vo2_vals,
        "act_labels": act_labels,
        "act_hours": act_hours,
        "wkly_run_dates": wkly_run_dates,
        "wkly_run_km": wkly_run_km,
        "wcal_dates": wcal_dates,
        "wcal_vals": wcal_vals,
        "steps_dates": steps_dates,
        "steps_vals": steps_vals,
    }

    # ── HTML ──────────────────────────────────────────────────────────────────
    report_date_str = today.strftime("%d %B %Y")

    def render_score_bar(label, val):
        v = (
            0
            if (val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))))
            else int(round(float(np.clip(val, 0, 100))))
        )
        col = score_color(v)
        return f"""
        <div style="margin-top:10px">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
            <span style="color:#94a3b8">{label}</span>
            <span style="color:{col};font-weight:600">{v}/100</span>
          </div>
          <div style="background:#334155;border-radius:4px;height:6px">
            <div style="width:{v}%;height:100%;border-radius:4px;background:{col}"></div>
          </div>
        </div>"""

    def badge_cls(change_str):
        if "+" in str(change_str):
            return "badge-green"
        if "-" in str(change_str):
            return "badge-red"
        return "badge-neutral"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Health Dashboard · Simon · {report_date_str}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0d14;color:#e2e8f0;min-height:100vh}}
.top-bar{{background:linear-gradient(135deg,#1a1f2e 0%,#111827 100%);padding:28px 32px;border-bottom:1px solid #1e293b;display:flex;justify-content:space-between;align-items:center}}
.top-bar h1{{font-size:24px;font-weight:700;color:#fff;letter-spacing:-0.5px}}
.top-bar .date{{font-size:13px;color:#475569}}
.container{{max-width:1440px;margin:0 auto;padding:28px 24px}}
.section{{margin-bottom:24px}}
.section-label{{font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#475569;margin-bottom:14px;font-weight:600}}
.grid{{display:grid;gap:16px}}
.g2{{grid-template-columns:repeat(2,1fr)}}
.g3{{grid-template-columns:repeat(3,1fr)}}
.g4{{grid-template-columns:repeat(4,1fr)}}
.card{{background:#131928;border:1px solid #1e293b;border-radius:14px;padding:20px}}
.card-title{{font-size:13px;font-weight:600;color:#94a3b8;margin-bottom:14px}}
.score-ring{{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:28px 20px}}
.ring-num{{font-size:52px;font-weight:800;line-height:1}}
.ring-sub{{font-size:12px;color:#64748b;margin-top:6px;text-align:center}}
.kpi-val{{font-size:32px;font-weight:700;color:#fff;line-height:1}}
.kpi-lbl{{font-size:12px;color:#64748b;margin-top:6px}}
.kpi-sub{{font-size:11px;color:#475569;margin-top:4px}}
.kpi-icon{{font-size:26px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{padding:10px 14px;text-align:left;color:#475569;font-size:11px;text-transform:uppercase;letter-spacing:.8px;border-bottom:1px solid #1e293b;font-weight:600}}
td{{padding:10px 14px;border-bottom:1px solid #131928;color:#cbd5e1}}
tr:hover td{{background:#1e293b44}}
.badge{{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}}
.badge-green{{background:#14532d44;color:#4ade80;border:1px solid #14532d}}
.badge-red{{background:#4c051944;color:#fb7185;border:1px solid #4c0519}}
.badge-neutral{{background:#1e293b;color:#94a3b8;border:1px solid #334155}}
.yoy-row{{display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid #1e293b22}}
.yoy-row:last-child{{border-bottom:none}}
.chart-wrap{{height:260px}}
.sep{{width:1px;background:#1e293b;margin:0 4px}}
@media(max-width:900px){{.g2,.g3,.g4{{grid-template-columns:1fr}}}}
</style>
</head>
<body>

<div class="top-bar">
  <div>
    <h1>🏋️ Health Dashboard · Simon</h1>
    <div class="date">Rapport du {report_date_str} · Export Apple Watch & Health</div>
  </div>
  <div style="font-size:13px;color:#334155">Age {age_years(BIRTH_DATE)} ans · {
        len(df_workouts)
    } séances totales enregistrées</div>
</div>

<div class="container">

  <!-- ── SCORES & KPIs ────────────────────────────────────────────────────── -->
  <div class="section">
    <div class="section-label">Tableau de bord</div>
    <div class="grid g4">

      <!-- Score de forme -->
      <div class="card score-ring">
        <div style="position:relative;width:120px;height:120px;margin-bottom:12px">
          <svg viewBox="0 0 120 120" style="width:120px;height:120px;transform:rotate(-90deg)">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#1e293b" stroke-width="10"/>
            <circle cx="60" cy="60" r="50" fill="none" stroke="{
        score_color(form_score)
    }" stroke-width="10"
              stroke-dasharray="314" stroke-dashoffset="{
        314 - 314 * form_score / 100:.0f}" stroke-linecap="round"/>
          </svg>
          <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center">
            <div class="ring-num" style="color:{score_color(form_score)}">{form_score}</div>
            <div style="font-size:10px;color:#475569">/100</div>
          </div>
        </div>
        <div style="font-size:15px;font-weight:700;color:#e2e8f0">Forme actuelle</div>
        <div style="font-size:13px;color:#64748b;margin-top:2px">{score_label(form_score)}</div>
        {"".join(render_score_bar(k, v) for k, v in form_comp.items())}
      </div>

      <!-- Score Wakeboard -->
      <div class="card score-ring">
        <div style="position:relative;width:120px;height:120px;margin-bottom:12px">
          <svg viewBox="0 0 120 120" style="width:120px;height:120px;transform:rotate(-90deg)">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#1e293b" stroke-width="10"/>
            <circle cx="60" cy="60" r="50" fill="none" stroke="{
        score_color(wake_score)
    }" stroke-width="10"
              stroke-dasharray="314" stroke-dashoffset="{
        314 - 314 * wake_score / 100:.0f}" stroke-linecap="round"/>
          </svg>
          <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center">
            <div class="ring-num" style="color:{score_color(wake_score)}">{wake_score}</div>
            <div style="font-size:10px;color:#475569">/100</div>
          </div>
        </div>
        <div style="font-size:15px;font-weight:700;color:#e2e8f0">🏄 Wakeboard Ready</div>
        <div style="font-size:13px;color:#64748b;margin-top:2px">{score_label(wake_score)}</div>
        {"".join(render_score_bar(k, v) for k, v in wake_comp.items())}
      </div>

      <!-- Cette semaine -->
      <div class="card">
        <div class="card-title">📅 Cette semaine</div>
        <div class="grid g2" style="gap:10px">
          <div style="background:#0a0d14;border-radius:10px;padding:14px">
            <div class="kpi-val">{tw_workouts}</div>
            <div class="kpi-lbl">Séances</div>
          </div>
          <div style="background:#0a0d14;border-radius:10px;padding:14px">
            <div class="kpi-val">{tw_duration}h</div>
            <div class="kpi-lbl">Volume</div>
          </div>
          <div style="background:#0a0d14;border-radius:10px;padding:14px">
            <div class="kpi-val">{tw_calories}</div>
            <div class="kpi-lbl">kcal</div>
          </div>
          <div style="background:#0a0d14;border-radius:10px;padding:14px">
            <div class="kpi-val" style="font-size:20px">{pace_str}</div>
            <div class="kpi-lbl">Allure récente</div>
            <div class="kpi-sub">{trend_str}</div>
          </div>
        </div>
      </div>

      <!-- Métriques santé -->
      <div class="card">
        <div class="card-title">❤️ Métriques clés</div>
        <div style="display:flex;flex-direction:column;gap:10px">
          <div style="background:#0a0d14;border-radius:10px;padding:14px;display:flex;justify-content:space-between;align-items:center">
            <div>
              <div class="kpi-val">{rhr_str}</div>
              <div class="kpi-lbl">FC repos (bpm)</div>
            </div>
            <div class="kpi-icon">💓</div>
          </div>
          <div style="background:#0a0d14;border-radius:10px;padding:14px;display:flex;justify-content:space-between;align-items:center">
            <div>
              <div class="kpi-val">{hrv_str}</div>
              <div class="kpi-lbl">HRV (ms)</div>
            </div>
            <div class="kpi-icon">📊</div>
          </div>
          <div style="background:#0a0d14;border-radius:10px;padding:14px;display:flex;justify-content:space-between;align-items:center">
            <div>
              <div class="kpi-val">{vo2_str}</div>
              <div class="kpi-lbl">VO2Max (mL/kg/min)</div>
            </div>
            <div class="kpi-icon">🫁</div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- ── GRAPHIQUES COURSE ─────────────────────────────────────────────────── -->
  <div class="section">
    <div class="section-label">🏃 Course à pied</div>
    <div class="grid g2">
      <div class="card">
        <div class="card-title">Évolution de l'allure (24 mois)</div>
        <div id="ch-pace" class="chart-wrap"></div>
      </div>
      <div class="card">
        <div class="card-title">Volume hebdomadaire (km — 6 mois)</div>
        <div id="ch-wkly-run" class="chart-wrap"></div>
      </div>
    </div>
  </div>

  <!-- ── CHARGE D'ENTRAÎNEMENT ─────────────────────────────────────────────── -->
  <div class="section">
    <div class="section-label">⚡ Charge & Récupération</div>
    <div class="grid g2">
      <div class="card">
        <div class="card-title">Charge d'entraînement — CTL / ATL / TSB (12 mois)</div>
        <div id="ch-load" class="chart-wrap"></div>
        <div style="font-size:11px;color:#334155;margin-top:8px">
          🔵 CTL = Fitness (42j) &nbsp;·&nbsp; 🔴 ATL = Fatigue (7j) &nbsp;·&nbsp; 🟡 TSB = Forme (CTL−ATL, positif = frais)
        </div>
      </div>
      <div class="card">
        <div class="card-title">Calories actives hebdomadaires (6 mois)</div>
        <div id="ch-wcal" class="chart-wrap"></div>
      </div>
    </div>
  </div>

  <!-- ── SANTÉ CARDIAQUE ───────────────────────────────────────────────────── -->
  <div class="section">
    <div class="section-label">❤️ Santé cardiaque</div>
    <div class="grid g3">
      <div class="card">
        <div class="card-title">HRV – Variabilité cardiaque (6 mois)</div>
        <div id="ch-hrv" class="chart-wrap"></div>
      </div>
      <div class="card">
        <div class="card-title">FC au repos (6 mois)</div>
        <div id="ch-rhr" class="chart-wrap"></div>
      </div>
      <div class="card">
        <div class="card-title">VO2Max historique</div>
        <div id="ch-vo2" class="chart-wrap"></div>
      </div>
    </div>
  </div>

  <!-- ── ACTIVITÉS & COMPARAISON ──────────────────────────────────────────── -->
  <div class="section">
    <div class="section-label">📊 Activités & Année vs Année</div>
    <div class="grid g2">

      <!-- Répartition -->
      <div class="card">
        <div class="card-title">Répartition des activités — 12 derniers mois (heures)</div>
        <div id="ch-act" style="height:300px"></div>
      </div>

      <!-- Year over year -->
      <div class="card">
        <div class="card-title">Comparaison {today.year} vs {today.year - 1}</div>
        <div style="display:grid;grid-template-columns:auto 1fr 1fr auto;gap:10px;font-size:13px;margin-bottom:10px;color:#475569;align-items:center">
          <div></div><div style="text-align:right;font-weight:600">{today.year - 1}</div>
          <div style="font-weight:600">{today.year}</div><div></div>
        </div>
        {
        "".join(
            f'''
        <div class="yoy-row">
          <div style="font-size:14px;color:#94a3b8">{m["label"]}</div>
          <div style="display:flex;gap:14px;align-items:center">
            <span style="color:#475569">{m["last"]}{m["unit"]}</span>
            <span style="font-weight:700;color:#e2e8f0">{m["this"]}{m["unit"]}</span>
            <span class="badge {badge_cls(m["change"])}">{m["change"]}</span>
          </div>
        </div>'''
            for m in yoy_metrics
        )
    }
        <div id="ch-steps" style="height:140px;margin-top:20px"></div>
        <div style="font-size:11px;color:#334155;margin-top:4px">Pas quotidiens — 90 derniers jours</div>
      </div>

    </div>
  </div>

  <!-- ── 10 DERNIÈRES SÉANCES ──────────────────────────────────────────────── -->
  <div class="section">
    <div class="section-label">🕐 Dernières séances</div>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Activité</th><th>Date</th><th>Durée</th>
            <th>Distance</th><th>Allure</th><th>kcal</th><th>FC moy.</th>
          </tr>
        </thead>
        <tbody>
          {
        "".join(
            f'''<tr>
            <td>{r["label"]}</td>
            <td style="color:#475569">{r["date"]}</td>
            <td>{r["duration"]}</td>
            <td>{r["dist_str"]}</td>
            <td style="color:#60a5fa;font-family:monospace">{r["pace_str"]}</td>
            <td>{r["cal_str"]}</td>
            <td style="color:#f87171">{r["hr_str"]}</td>
          </tr>'''
            for r in table_rows
        )
    }
        </tbody>
      </table>
    </div>
  </div>

  <div style="text-align:center;padding:20px;font-size:12px;color:#1e293b">
    Généré le {report_date_str} · Health Analyzer · Simon Hingant
  </div>

</div><!-- /container -->

<script>
const D = {json.dumps(cd)};
const BASE = {{
  paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{{color:'#64748b',size:11}},
  margin:{{t:10,r:16,b:36,l:48}},
  xaxis:{{gridcolor:'#1e293b',linecolor:'#1e293b',showgrid:true}},
  yaxis:{{gridcolor:'#1e293b',linecolor:'#1e293b',showgrid:true}},
  legend:{{bgcolor:'rgba(0,0,0,0)',font:{{color:'#64748b',size:11}}}},
  hovermode:'x unified',
  hoverlabel:{{bgcolor:'#1e293b',bordercolor:'#334155',font:{{color:'#e2e8f0'}}}},
}};
const CFG = {{responsive:true,displayModeBar:false}};

// Pace formatter
function fmtPace(v){{
  if(!v||v<=0||v>20) return '';
  const m=Math.floor(v), s=Math.round((v-m)*60);
  return m+':'+(s<10?'0':'')+s+'/km';
}}

// ── Allure course ────────────────────────────────────────────────────────────
Plotly.newPlot('ch-pace',[
  {{x:D.run_dates,y:D.run_pace,mode:'markers',name:'Allure',
    marker:{{color:'#3b82f6',size:6,opacity:0.35}},
    hovertemplate:'%{{x}}<br>Allure: %{{customdata}}<extra></extra>',
    customdata:D.run_pace.map(fmtPace)}},
  {{x:D.run_dates,y:D.run_pace_roll,mode:'lines',name:'Moy. mobile (5 séances)',
    line:{{color:'#60a5fa',width:2.5}},
    hovertemplate:'%{{x}}<br>Moy: %{{customdata}}<extra></extra>',
    customdata:D.run_pace_roll.map(fmtPace)}},
],{{...BASE,
  yaxis:{{...BASE.yaxis,autorange:'reversed',title:'min/km',
    ticktext:['4:00','4:30','5:00','5:30','6:00','6:30','7:00','7:30','8:00'],
    tickvals:[4,4.5,5,5.5,6,6.5,7,7.5,8]}},
  legend:{{orientation:'h',y:-0.15}},
}},CFG);

// ── Volume course hebdomadaire ────────────────────────────────────────────────
Plotly.newPlot('ch-wkly-run',[
  {{x:D.wkly_run_dates,y:D.wkly_run_km,type:'bar',name:'Distance',
    marker:{{color:'#22c55e',opacity:0.8}},
    hovertemplate:'%{{x}}<br>%{{y:.1f}} km<extra></extra>'}},
],{{...BASE,yaxis:{{...BASE.yaxis,title:'km'}}}},CFG);

// ── Charge CTL/ATL/TSB ───────────────────────────────────────────────────────
Plotly.newPlot('ch-load',[
  {{x:D.load_dates,y:D.ctl,mode:'lines',name:'Fitness (CTL)',
    line:{{color:'#3b82f6',width:2}}}},
  {{x:D.load_dates,y:D.atl,mode:'lines',name:'Fatigue (ATL)',
    line:{{color:'#ef4444',width:2}}}},
  {{x:D.load_dates,y:D.tsb,mode:'lines',name:'Forme (TSB)',
    line:{{color:'#f59e0b',width:2.5}},
    fill:'tozeroy',fillcolor:'rgba(245,158,11,0.07)'}},
],{{...BASE,legend:{{orientation:'h',y:-0.15}}}},CFG);

// ── Calories hebdo ───────────────────────────────────────────────────────────
Plotly.newPlot('ch-wcal',[
  {{x:D.wcal_dates,y:D.wcal_vals,type:'bar',name:'kcal actives',
    marker:{{color:'#8b5cf6',opacity:0.75}},
    hovertemplate:'%{{x}}<br>%{{y:.0f}} kcal<extra></extra>'}},
],{{...BASE,yaxis:{{...BASE.yaxis,title:'kcal'}}}},CFG);

// ── HRV ──────────────────────────────────────────────────────────────────────
Plotly.newPlot('ch-hrv',[
  {{x:D.hrv_dates,y:D.hrv_vals,mode:'markers',name:'HRV',
    marker:{{color:'#a78bfa',size:4,opacity:0.4}}}},
  {{x:D.hrv_dates,y:D.hrv_roll,mode:'lines',name:'Moy. 7j',
    line:{{color:'#c4b5fd',width:2.5}}}},
],{{...BASE,yaxis:{{...BASE.yaxis,title:'ms'}},
  legend:{{orientation:'h',y:-0.15}}}},CFG);

// ── FC repos ──────────────────────────────────────────────────────────────────
Plotly.newPlot('ch-rhr',[
  {{x:D.rhr_dates,y:D.rhr_vals,mode:'markers',name:'FC repos',
    marker:{{color:'#f43f5e',size:4,opacity:0.4}}}},
  {{x:D.rhr_dates,y:D.rhr_roll,mode:'lines',name:'Moy. 7j',
    line:{{color:'#fb7185',width:2.5}}}},
],{{...BASE,
  yaxis:{{...BASE.yaxis,autorange:'reversed',title:'bpm'}},
  legend:{{orientation:'h',y:-0.15}}}},CFG);

// ── VO2Max ────────────────────────────────────────────────────────────────────
Plotly.newPlot('ch-vo2',[
  {{x:D.vo2_dates,y:D.vo2_vals,mode:'lines+markers',name:'VO2Max',
    line:{{color:'#06b6d4',width:2.5}},
    marker:{{color:'#06b6d4',size:7}},
    hovertemplate:'%{{x}}<br>VO2Max: %{{y:.1f}} mL/kg/min<extra></extra>'}},
  {{x:D.vo2_dates,y:Array(D.vo2_dates.length).fill(52),mode:'lines',name:'Excellent (>52)',
    line:{{color:'#22c55e',width:1,dash:'dot'}}}},
  {{x:D.vo2_dates,y:Array(D.vo2_dates.length).fill(43),mode:'lines',name:'Bon (>43)',
    line:{{color:'#f59e0b',width:1,dash:'dot'}}}},
],{{...BASE,yaxis:{{...BASE.yaxis,title:'mL/kg/min'}},
  legend:{{orientation:'h',y:-0.15}}}},CFG);

// ── Répartition activités ─────────────────────────────────────────────────────
Plotly.newPlot('ch-act',[
  {{labels:D.act_labels,values:D.act_hours,type:'pie',hole:0.42,
    marker:{{colors:['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#14b8a6','#f97316']}},
    textinfo:'label+percent',
    textfont:{{color:'#e2e8f0',size:11}},
    hovertemplate:'%{{label}}<br>%{{value:.1f}}h (%{{percent}})<extra></extra>'}},
],{{...BASE,
  margin:{{t:10,r:10,b:10,l:10}},
  legend:{{bgcolor:'rgba(0,0,0,0)',font:{{color:'#64748b',size:10}}}},
  showlegend:true,
}},CFG);

// ── Pas quotidiens ────────────────────────────────────────────────────────────
Plotly.newPlot('ch-steps',[
  {{x:D.steps_dates,y:D.steps_vals,type:'bar',name:'Pas',
    marker:{{color:'#10b981',opacity:0.6}},
    hovertemplate:'%{{x}}<br>%{{y:,}} pas<extra></extra>'}},
  {{x:D.steps_dates,y:Array(D.steps_dates.length).fill(10000),mode:'lines',name:'Objectif 10k',
    line:{{color:'#6ee7b7',width:1,dash:'dot'}}}},
],{{...BASE,
  margin:{{t:4,r:8,b:28,l:40}},
  yaxis:{{...BASE.yaxis,title:'',tickformat:','}},
  legend:{{orientation:'h',y:1.15}},
}},CFG);
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard sauvegardé → {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Health Analytics Dashboard Generator")
    parser.add_argument("--export", default=str(EXPORT_PATH), help="Chemin vers export.xml")
    parser.add_argument("--output", default=None, help="Chemin du fichier HTML de sortie")
    parser.add_argument(
        "--open", action="store_true", help="Ouvre le rapport dans le navigateur après génération"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Force le re-parsing (ignore le cache)"
    )
    args = parser.parse_args()

    export_path = Path(args.export)
    if not export_path.exists():
        print(f"❌ Fichier introuvable : {export_path}")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = OUTPUT_DIR / f"health_report_{date.today().strftime('%Y-%m-%d')}.html"

    print(f"\n{'=' * 60}")
    print("  🏋️  Health Analytics Dashboard — Simon Hingant")
    print(f"  Date : {date.today().strftime('%d %B %Y')}")
    print(f"{'=' * 60}\n")

    # Cache joblib pour accélérer les relances (sécurisé)
    import joblib

    cache_path = SCRIPT_DIR / ".health_cache.pkl"
    use_cache = (
        cache_path.exists()
        and not args.no_cache
        and cache_path.stat().st_mtime >= export_path.stat().st_mtime
    )

    if use_cache:
        print("⚡ Chargement depuis le cache (utilisez --no-cache pour re-parser)…")
        workouts, records = joblib.load(cache_path)
    else:
        workouts, records = parse_health_data(export_path)
        joblib.dump((workouts, records), cache_path, compress=3)
        print("💾 Cache sauvegardé")

    df_workouts, daily = build_dataframes(workouts, records)
    training_load = calculate_training_load(df_workouts)
    report = generate_report(df_workouts, daily, training_load, output_path)

    print("\n🎉 Rapport prêt !")
    print(f"   → file://{report.resolve()}")

    if args.open:
        import subprocess

        subprocess.run(["open", str(report)], check=False)


if __name__ == "__main__":
    main()
