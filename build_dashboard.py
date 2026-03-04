#!/usr/bin/env python3
"""
Health Dashboard v2 — Simon Hingant
Sources : Apple Health (export.xml) + Strava (activities.csv)
Génère un rapport HTML interactif chaque dimanche.
"""

import pickle, json, math, sys, argparse, warnings
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
BASE          = Path(__file__).parent
EXPORT_XML    = BASE / "export.xml"
STRAVA_CSV    = BASE / "export_strava" / "activities.csv"
OUTPUT_DIR    = BASE / "reports"
CACHE_FILE    = BASE / ".ah_cache.pkl"
BIRTH_DATE    = date(1992, 10, 28)

AH_WORKOUT_MAP = {
    "HKWorkoutActivityTypeRunning":                    "Course à pied",
    "HKWorkoutActivityTypeCrossTraining":              "Entraînement",
    "HKWorkoutActivityTypeOther":                      "Autre",
    "HKWorkoutActivityTypeSwimming":                   "Natation",
    "HKWorkoutActivityTypeCycling":                    "Vélo",
    "HKWorkoutActivityTypeTraditionalStrengthTraining":"Entraînement aux poids",
    "HKWorkoutActivityTypeWalking":                    "Marche",
    "HKWorkoutActivityTypeYoga":                       "Yoga",
    "HKWorkoutActivityTypeSnowboarding":               "Snowboard",
    "HKWorkoutActivityTypeDownhillSkiing":             "Ski alpin",
    "HKWorkoutActivityTypeSnowSports":                 "Sports neige",
    "HKWorkoutActivityTypeElliptical":                 "Elliptique",
}

SPORT_ICONS = {
    "Course à pied":          "🏃",
    "Vélo":                   "🚴",
    "Entraînement aux poids": "💪",
    "Natation":               "🏊",
    "Marche":                 "🚶",
    "Snowboard":              "🏂",
    "Ski de randonnée":       "🎿",
    "Entraînement":           "⚡",
    "Autre":                  "🏋️",
}

AH_RECORDS = {
    "HKQuantityTypeIdentifierRestingHeartRate",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
    "HKQuantityTypeIdentifierVO2Max",
    "HKQuantityTypeIdentifierStepCount",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def age():
    t = date.today()
    return t.year - BIRTH_DATE.year - ((t.month, t.day) < (BIRTH_DATE.month, BIRTH_DATE.day))

def sf(v, d=0.0):
    try: return float(str(v).replace(',', '.').replace('\u202f','').strip() or d)
    except: return d

def strip_tz(s: pd.Series) -> pd.Series:
    s2 = pd.to_datetime(s, utc=False, errors='coerce')
    if s2.dt.tz is not None:
        return s2.dt.tz_convert('UTC').dt.tz_localize(None)
    return s2

def fmt_pace(p):
    if not p or pd.isna(p) or p <= 0 or p > 15: return "—"
    m, s = int(p), int(round((p - int(p)) * 60))
    return f"{m}:{s:02d}/km"

def fmt_time(secs):
    if not secs or pd.isna(secs): return "—"
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}h{m:02d}" if h else f"{m}:{s:02d}"

def sc(v):  # score color
    v = float(v) if v else 0
    return "#22c55e" if v >= 72 else ("#f59e0b" if v >= 50 else "#ef4444")

def pct_diff(a, b):
    try:
        p = (float(a) - float(b)) / float(b) * 100
        return (f"+{p:.0f}%", "up") if p >= 0 else (f"{p:.0f}%", "down")
    except: return ("—", "neutral")

# ─────────────────────────────────────────────────────────────────────────────
# PARSE APPLE HEALTH (streaming)
# ─────────────────────────────────────────────────────────────────────────────
def parse_apple_health(path: Path):
    print(f"📂 Parsing Apple Health ({path.stat().st_size/1e6:.0f} MB)…")
    workouts, records = [], defaultdict(list)
    n = 0
    for _, elem in ET.iterparse(str(path), events=("end",)):
        if elem.tag == "Workout":
            w = dict(
                type=elem.get("workoutActivityType",""),
                start=elem.get("startDate",""), end=elem.get("endDate",""),
                duration_min=sf(elem.get("duration")),
                distance_km=sf(elem.get("totalDistance")),
                calories=sf(elem.get("totalEnergyBurned")),
                avg_hr=None, source="AppleHealth",
            )
            for st in elem.findall("WorkoutStatistics"):
                t = st.get("type","")
                if any(x in t for x in ("DistanceWalkingRunning","DistanceCycling","DistanceSwimming")):
                    d = sf(st.get("sum")); u = st.get("unit","km")
                    if d > 0: w["distance_km"] = d * 1.60934 if u in ("mi","miles") else d
                elif "ActiveEnergyBurned" in t:
                    c = sf(st.get("sum"))
                    if c > 0 and w["calories"] == 0: w["calories"] = c
                elif "HeartRate" in t:
                    h = sf(st.get("average"))
                    if h > 0: w["avg_hr"] = h
            workouts.append(w); elem.clear()
        elif elem.tag == "Record":
            rt = elem.get("type","")
            if rt in AH_RECORDS:
                records[rt].append({"date": elem.get("startDate",""), "value": sf(elem.get("value"))})
            elem.clear()
            n += 1
            if n % 500_000 == 0: print(f"   …{n:,} records")
    print(f"✅ AH: {len(workouts)} workouts · {sum(len(v) for v in records.values()):,} records")
    return workouts, records

# ─────────────────────────────────────────────────────────────────────────────
# LOAD STRAVA
# ─────────────────────────────────────────────────────────────────────────────
def load_strava(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['date']        = strip_tz(df["Date de l'activité"])
    df['type']        = df["Type d'activité"].str.strip()
    df['dist_km']     = df['Distance'].apply(sf)
    df['dur_sec']     = pd.to_numeric(df['Temps écoulé'], errors='coerce')
    df['duration_min']= df['dur_sec'] / 60
    df['avg_hr']      = pd.to_numeric(df['Fréquence cardiaque moyenne'], errors='coerce')
    df['max_hr']      = pd.to_numeric(df['Fréquence cardiaque max.'], errors='coerce')
    df['calories']    = df['Calories'].apply(sf)
    df['elevation']   = df['Dénivelé positif'].apply(sf)
    df['source']      = 'Strava'
    tl_col = [c for c in df.columns if 'Charge' in c and 'entra' in c.lower()]
    df['training_load'] = df[tl_col[0]].apply(sf) if tl_col else np.nan
    df = df.rename(columns={'dist_km': 'distance_km'})
    print(f"✅ Strava: {len(df)} activities · types: {df['type'].value_counts().to_dict()}")
    return df

# ─────────────────────────────────────────────────────────────────────────────
# BUILD UNIFIED DATAFRAME + DEDUP
# ─────────────────────────────────────────────────────────────────────────────
def build_unified(ah_workouts, strava_df: pd.DataFrame) -> pd.DataFrame:
    """Merge Apple Health + Strava, deduplicate overlaps."""

    # ── Apple Health workouts ──────────────────────────────────────────────────
    ah = pd.DataFrame(ah_workouts)
    ah['start'] = strip_tz(ah['start'])
    ah['date']  = ah['start'].dt.date
    ah['type']  = ah['type'].map(AH_WORKOUT_MAP).fillna(ah['type'])
    ah['duration_min'] = ah['duration_min'].astype(float)
    ah['distance_km']  = ah['distance_km'].astype(float)
    ah['calories']     = ah['calories'].astype(float)
    ah['elevation']    = np.nan
    ah['training_load']= np.nan
    ah['max_hr']       = np.nan

    # ── Strava ────────────────────────────────────────────────────────────────
    st = strava_df.copy()
    st['date'] = st['date'].dt.date

    # ── Columns to keep ───────────────────────────────────────────────────────
    cols = ['date','type','duration_min','distance_km','calories','avg_hr','max_hr',
            'elevation','training_load','source']
    ah_sub = ah[cols].copy()
    st_sub = st[cols].copy()

    combined = pd.concat([ah_sub, st_sub], ignore_index=True)
    combined['date'] = pd.to_datetime(combined['date'])
    combined = combined.sort_values('date').reset_index(drop=True)

    # ── Deduplication ─────────────────────────────────────────────────────────
    # If same type + same date + duration within 10 min → keep Strava (richer)
    combined['dur_round'] = (combined['duration_min'] / 5).round() * 5
    combined['dedup_key'] = combined['type'].str.lower().str[:8] + "_" + \
                            combined['date'].dt.strftime("%Y%m%d") + "_" + \
                            combined['dur_round'].astype(int).astype(str)

    # Among duplicates prefer Strava
    combined['src_rank'] = combined['source'].map({'Strava': 0, 'AppleHealth': 1}).fillna(2)
    combined = combined.sort_values('src_rank').drop_duplicates('dedup_key', keep='first')
    combined = combined.drop(columns=['dur_round','dedup_key','src_rank'])
    combined = combined.sort_values('date').reset_index(drop=True)

    # ── Enrich ────────────────────────────────────────────────────────────────
    combined['year']     = combined['date'].dt.year
    combined['month']    = combined['date'].dt.to_period('M').astype(str)
    combined['week']     = combined['date'].dt.isocalendar().week.fillna(0).astype(int)
    combined['dow']      = combined['date'].dt.dayofweek  # 0=Mon

    # Running pace
    run_mask = (combined['type'] == 'Course à pied') & (combined['distance_km'] > 0.5)
    combined['pace_min_km'] = np.where(
        run_mask, combined['duration_min'] / combined['distance_km'], np.nan)
    combined.loc[~combined['pace_min_km'].between(3, 12), 'pace_min_km'] = np.nan
    combined['speed_kmh'] = np.where(
        run_mask & combined['pace_min_km'].notna(),
        combined['distance_km'] / (combined['duration_min'] / 60), np.nan)

    n_strava = (combined['source'] == 'Strava').sum()
    n_ah     = (combined['source'] == 'AppleHealth').sum()
    print(f"✅ Merged: {len(combined)} unique activities ({n_strava} Strava + {n_ah} AH)")
    return combined

# ─────────────────────────────────────────────────────────────────────────────
# BUILD DAILY HEALTH METRICS
# ─────────────────────────────────────────────────────────────────────────────
def build_daily_metrics(ah_records):
    SUM_T = {"HKQuantityTypeIdentifierStepCount","HKQuantityTypeIdentifierActiveEnergyBurned"}
    daily = {}
    for key, recs in ah_records.items():
        if not recs: continue
        df = pd.DataFrame(recs)
        d  = strip_tz(df['date'])
        df['date'] = d.dt.date
        agg = df.groupby('date')['value']
        daily[key] = (agg.sum() if key in SUM_T else agg.mean()).reset_index()
    return daily

# ─────────────────────────────────────────────────────────────────────────────
# TRAINING LOAD (PMC)
# ─────────────────────────────────────────────────────────────────────────────
def build_pmc(df: pd.DataFrame) -> pd.DataFrame:
    daily = df.groupby('date')['calories'].sum().reset_index()
    daily.columns = ['date','kcal']
    daily['date'] = pd.to_datetime(daily['date'])
    dr = pd.date_range(daily['date'].min(), date.today())
    daily = daily.set_index('date').reindex(dr, fill_value=0).reset_index()
    daily.columns = ['date','kcal']
    daily['tss'] = daily['kcal'] / 5.0
    daily['ctl'] = daily['tss'].ewm(span=42, min_periods=1).mean()
    daily['atl'] = daily['tss'].ewm(span=7,  min_periods=1).mean()
    daily['tsb'] = daily['ctl'] - daily['atl']
    return daily

# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def riegel_predict(dist_km, time_min, target_km):
    """Riegel formula: t2 = t1 * (d2/d1)^1.06"""
    if dist_km <= 0 or time_min <= 0: return None
    return time_min * (target_km / dist_km) ** 1.06

def estimate_vdot(pace_min_km, dist_km):
    """Estimate VO2Max from pace using Daniels VDOT approximation."""
    if pace_min_km <= 0 or dist_km < 3: return None
    speed_ms = 1000 / (pace_min_km * 60)
    # % VO2Max from distance (Daniels table approximation)
    pct = {5: 0.979, 10: 0.952, 21.1: 0.930, 42.2: 0.910}.get(
        min([5, 10, 21.1, 42.2], key=lambda d: abs(d - dist_km)), 0.95)
    vo2 = (-4.6 + 0.182258 * speed_ms * 60 + 0.000104 * (speed_ms * 60) ** 2) / pct
    return max(20, min(85, vo2))

def analyze_running(run_df: pd.DataFrame) -> dict:
    if run_df.empty:
        return {}
    recent10 = run_df.nlargest(10, 'date')
    recent5  = run_df.nlargest(5,  'date')

    avg_pace_all    = run_df['pace_min_km'].mean()
    avg_pace_r10    = recent10['pace_min_km'].mean()
    avg_pace_r5     = recent5['pace_min_km'].mean()
    best_pace       = run_df['pace_min_km'].min()
    avg_dist        = run_df['distance_km'].mean()
    avg_dist_r10    = recent10['distance_km'].mean()

    # Best effort on longest run
    long_run = run_df.nlargest(1, 'distance_km').iloc[0]
    pred_10k = riegel_predict(long_run['distance_km'], long_run['duration_min'], 10.0)

    # VDOT estimate from recent pace
    vdot_est = estimate_vdot(avg_pace_r5, avg_dist_r10) if avg_dist_r10 > 3 else None

    # Trend: comparing first half vs second half of history
    mid = len(run_df) // 2
    first_half  = run_df.iloc[:mid]['pace_min_km'].mean()
    second_half = run_df.iloc[mid:]['pace_min_km'].mean()
    trend = "progression" if second_half < first_half else "stable" if abs(second_half - first_half) < 0.3 else "régression"

    # Per-year avg pace
    yearly = run_df.groupby('year').agg(
        n=('pace_min_km','count'),
        avg_pace=('pace_min_km','mean'),
        total_km=('distance_km','sum'),
        avg_dist=('distance_km','mean'),
    ).round(2)

    return {
        'avg_pace_all': avg_pace_all,
        'avg_pace_r10': avg_pace_r10,
        'avg_pace_r5': avg_pace_r5,
        'best_pace': best_pace,
        'avg_dist_r10': avg_dist_r10,
        'pred_10k_min': pred_10k,
        'vdot_est': vdot_est,
        'trend': trend,
        'yearly': yearly,
        'total_runs': len(run_df),
        'total_km': run_df['distance_km'].sum(),
    }

def fitness_tier(pace_r10, vo2_max=None):
    """Classify runner fitness tier."""
    v = vo2_max or 0
    if pace_r10 < 4.5 or v > 60: return ("Elite / Compétiteur", 95, "#c084fc")
    if pace_r10 < 5.0 or v > 55: return ("Avancé", 82, "#60a5fa")
    if pace_r10 < 5.5 or v > 50: return ("Intermédiaire+", 68, "#34d399")
    if pace_r10 < 6.5 or v > 43: return ("Intermédiaire", 55, "#fbbf24")
    return ("Débutant / Reprenant", 35, "#f87171")

# ─────────────────────────────────────────────────────────────────────────────
# TRAINING ADVICE (rule-based coach)
# ─────────────────────────────────────────────────────────────────────────────
def generate_coaching(df: pd.DataFrame, run_stats: dict, daily: dict, pmc: pd.DataFrame) -> dict:
    today = date.today()
    last4w  = today - timedelta(days=28)
    last8w  = today - timedelta(days=56)

    recent  = df[df['date'].dt.date >= last4w]
    n_runs  = len(recent[recent['type'] == 'Course à pied'])
    n_str   = len(recent[recent['type'] == 'Entraînement aux poids'])
    n_total = len(recent)
    km_run  = recent[recent['type'] == 'Course à pied']['distance_km'].sum()

    # Last workout date
    last_date = df['date'].max().date() if not df.empty else None
    days_off  = (today - last_date).days if last_date else 999

    # TSB
    latest_tsb = pmc['tsb'].iloc[-1] if not pmc.empty else 0
    latest_ctl = pmc['ctl'].iloc[-1] if not pmc.empty else 0

    # VO2Max
    vo2 = run_stats.get('vdot_est') or None
    RHR_KEY = "HKQuantityTypeIdentifierRestingHeartRate"
    rhr = None
    if RHR_KEY in daily and not daily[RHR_KEY].empty:
        rhr = daily[RHR_KEY]['value'].iloc[-1]

    pace = run_stats.get('avg_pace_r5', 6.5)

    # Form assessment
    if days_off > 30:
        phase = "reprise"
        advice_title = "Phase de reprise progressive"
        assessment = (
            f"Tu n'as pas eu d'activité enregistrée depuis {days_off} jours. "
            f"C'est le moment idéal pour reprendre progressivement. "
            f"Ton niveau de base (FC repos {int(rhr) if rhr else '~58'} bpm, VO2Max estimé ~{round(vo2) if vo2 else 50}) "
            f"reste bon — la condition cardiovasculaire se maintient bien avec une pause. "
            f"La priorité est de ne pas te blesser en reprenant trop fort."
        )
    elif n_total < 3:
        phase = "faible_charge"
        advice_title = "Semaine légère — bon moment pour construire"
        assessment = (
            f"Volume des 4 dernières semaines faible ({n_total} séances, {km_run:.0f} km de course). "
            f"Le TSB actuel est de {latest_tsb:.0f} — tu es frais. "
            f"C'est une excellente base pour augmenter progressivement la charge."
        )
    elif latest_tsb < -15:
        phase = "fatigue"
        advice_title = "Fatigue accumulée — semaine de récupération recommandée"
        assessment = (
            f"Le TSB (forme) est à {latest_tsb:.0f}, ce qui indique une fatigue accumulée. "
            f"Avec {n_runs} courses et {km_run:.0f} km sur 4 semaines, le corps a besoin de récupérer. "
            f"Une réduction de 30-40% du volume cette semaine optimisera les adaptations."
        )
    else:
        phase = "progression"
        advice_title = "Progression solide — continue sur ta lancée"
        assessment = (
            f"{n_total} séances sur 4 semaines, dont {n_runs} courses ({km_run:.0f} km) "
            f"et {n_str} séances de musculation. "
            f"TSB à {latest_tsb:.0f} — bonne fraîcheur. VO2Max estimé à {round(vo2) if vo2 else '~50'} mL/kg/min. "
            f"Tu es dans une dynamique de progression solide."
        )

    # Weekly plan
    if phase == "reprise":
        plan = [
            ("Lundi",    "Marche active 30-40 min ou repos", "récupération"),
            ("Mardi",    "Course facile 20-25 min à allure conversationnelle (~7:00/km)", "endurance"),
            ("Mercredi", "Musculation — Haut du corps (60 min)", "force"),
            ("Jeudi",    "Repos actif / étirements", "récupération"),
            ("Vendredi", "Course facile 25-30 min + étirements", "endurance"),
            ("Samedi",   "Musculation — Bas du corps + gainage (60 min)", "force"),
            ("Dimanche", "Sortie longue douce 35-40 min ou vélo léger", "endurance"),
        ]
    elif phase == "fatigue":
        plan = [
            ("Lundi",    "Repos total ou marche légère 20 min", "récupération"),
            ("Mardi",    "Course de récupération 20 min à allure très facile (~7:30/km)", "récupération"),
            ("Mercredi", "Musculation légère — volume réduit de 40%", "force"),
            ("Jeudi",    "Repos actif / yoga / mobilité", "récupération"),
            ("Vendredi", "Course facile 25 min", "endurance"),
            ("Samedi",   "Musculation modérée — 45 min", "force"),
            ("Dimanche", "Sortie longue douce 40 min", "endurance"),
        ]
    elif pace < 5.5:
        plan = [
            ("Lundi",    "Repos ou marche 30 min", "récupération"),
            ("Mardi",    f"Intervalles 6×800m à {fmt_pace(pace - 0.5)} avec 90s récup", "vitesse"),
            ("Mercredi", "Musculation — Haut du corps + gainage (75 min)", "force"),
            ("Jeudi",    f"Course régénératrice 30 min à {fmt_pace(pace + 1.0)}", "récupération"),
            ("Vendredi", f"Tempo run 4-5 km à {fmt_pace(pace + 0.2)}", "seuil"),
            ("Samedi",   "Musculation — Bas du corps + plyométrie (75 min)", "force"),
            ("Dimanche", f"Sortie longue 10-12 km à {fmt_pace(pace + 1.2)}", "endurance"),
        ]
    else:
        plan = [
            ("Lundi",    "Repos ou marche / mobilité 30 min", "récupération"),
            ("Mardi",    f"Fartlek 30 min — 4×3 min à {fmt_pace(pace - 0.5)} / 2 min récup", "vitesse"),
            ("Mercredi", "Musculation — Haut du corps + core (60 min)", "force"),
            ("Jeudi",    f"Course facile 25-30 min à {fmt_pace(pace + 0.8)}", "endurance"),
            ("Vendredi", f"Seuil 3×1200m à {fmt_pace(pace - 0.2)}, récup 2 min", "seuil"),
            ("Samedi",   "Musculation — Bas du corps (60 min)", "force"),
            ("Dimanche", f"Sortie longue 8-10 km à {fmt_pace(pace + 1.0)}", "endurance"),
        ]

    # 4-week block
    block = []
    km_base = max(km_run, 15) if phase not in ("reprise","fatigue") else 10
    for i in range(4):
        factor = [1.0, 1.1, 1.2, 0.7][i]
        label  = ["Semaine de charge","Charge +10%","Charge +20%","Récupération / Décharge"][i]
        block.append({
            "week": f"Semaine {i+1}",
            "label": label,
            "km_target": round(km_base * factor, 1),
            "sessions": [4,5,5,3][i],
            "intensity": ["Modérée","Modérée+","Haute","Faible"][i],
        })

    return {
        "phase": phase,
        "advice_title": advice_title,
        "assessment": assessment,
        "plan": plan,
        "block": block,
        "days_off": days_off,
        "n_runs_4w": n_runs,
        "n_str_4w": n_str,
        "km_4w": round(km_run, 1),
        "tsb": round(latest_tsb, 1),
        "ctl": round(latest_ctl, 1),
    }

# ─────────────────────────────────────────────────────────────────────────────
# GENERATE HTML
# ─────────────────────────────────────────────────────────────────────────────
def generate_html(df, daily, pmc, run_stats, coaching, output_path: Path):
    today  = date.today()
    age_v  = age()

    # ── Latest health metrics ─────────────────────────────────────────────────
    def latest(key, n=1):
        d = daily.get(key)
        if d is None or d.empty: return None
        return d['value'].iloc[-n:].mean()

    rhr    = latest("HKQuantityTypeIdentifierRestingHeartRate")
    hrv    = latest("HKQuantityTypeIdentifierHeartRateVariabilitySDNN")
    vo2max = latest("HKQuantityTypeIdentifierVO2Max")

    # ── Scores ────────────────────────────────────────────────────────────────
    # Form score — use the most recent available data within progressive windows
    scores = {}
    for k, key, inv in [
        ("hrv",    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN", False),
        ("fc_rep", "HKQuantityTypeIdentifierRestingHeartRate",         True),
    ]:
        d = daily.get(key)
        if d is not None and not d.empty:
            d2 = d.copy(); d2['date'] = pd.to_datetime(d2['date'])
            # Try progressively wider windows until we get at least 3 data points
            r = None
            for days_back in [14, 30, 60, 90, 180, 365]:
                cutoff = today - timedelta(days=days_back)
                recent = d2[d2['date'].dt.date >= cutoff]['value']
                if len(recent) >= 3:
                    r = recent.mean()
                    break
            if r is None:
                # Use last 5 measurements regardless of date
                r = d2['value'].iloc[-5:].mean() if len(d2) >= 5 else d2['value'].mean()
            b = d2['value'].quantile(0.5)
            if b > 0 and not np.isnan(r) and r > 0:
                scores[k] = float(np.clip((b/r if inv else r/b) * 50 + 50, 0, 100))

    tsb_now = pmc['tsb'].iloc[-1] if not pmc.empty else 0
    scores['charge'] = float(np.clip(50 + tsb_now * 1.5, 0, 100))

    last4w_df = df[df['date'].dt.date >= today - timedelta(days=28)]
    scores['régularité'] = float(np.clip(len(last4w_df) * 6.25, 0, 100))

    w = {'hrv': .30, 'fc_rep': .25, 'charge': .25, 'régularité': .20}
    raw_form = sum(scores[k] * w.get(k,.1) for k in scores) / sum(w.get(k,.1) for k in scores) if scores else 50.0
    form = int(np.clip(0 if np.isnan(raw_form) or np.isinf(raw_form) else raw_form, 0, 100))

    # Wakeboard
    wake_c = {'forme': float(form)}
    str4w = len(df[(df['date'].dt.date >= today-timedelta(days=28)) &
                   (df['type'].isin(['Entraînement aux poids','Entraînement','CrossFit']))])
    wake_c['force'] = float(np.clip(str4w * 12, 0, 100))
    if vo2max: wake_c['vo2max'] = float(np.clip((vo2max/52)*100, 0, 100))
    ww = {'forme':.30,'force':.30,'vo2max':.25,'activité':.15}
    run4w = len(df[(df['date'].dt.date >= today-timedelta(days=28)) &
                   (df['type'] == 'Course à pied')])
    wake_c['activité'] = float(np.clip(run4w * 8, 0, 100))
    wake = int(np.clip(
        sum(wake_c[k]*ww.get(k,.15) for k in wake_c) / sum(ww.get(k,.15) for k in wake_c), 0, 100
    ))

    # ── Running charts ────────────────────────────────────────────────────────
    run_df = df[df['type']=='Course à pied'].copy()
    run_df = run_df[run_df['pace_min_km'].notna()].sort_values('date')

    run_2y = run_df[run_df['date'] >= pd.Timestamp(today-timedelta(days=730))]
    poly_x = list(range(len(run_2y)))
    poly_y = run_2y['pace_min_km'].tolist()
    if len(poly_x) >= 3:
        coeffs    = np.polyfit(poly_x, poly_y, 1)
        trend_y   = np.polyval(coeffs, poly_x).tolist()
    else:
        trend_y = poly_y[:]

    # Yearly running stats
    yearly = run_stats.get('yearly', pd.DataFrame())
    y_years = yearly.index.tolist() if not yearly.empty else []
    y_km    = yearly['total_km'].round(1).tolist() if not yearly.empty else []
    y_pace  = yearly['avg_pace'].round(2).tolist() if not yearly.empty else []

    # Weekly running km (52 weeks)
    run_df2 = run_df.copy()
    run_df2['week_start'] = run_df2['date'].dt.to_period('W').dt.start_time
    wkly = run_df2[run_df2['date'] >= pd.Timestamp(today-timedelta(weeks=52))]
    wkly = wkly.groupby('week_start')['distance_km'].sum().reset_index()
    wkly_dates = wkly['week_start'].dt.strftime('%Y-%m-%d').tolist()
    wkly_km    = wkly['distance_km'].round(1).tolist()

    # ── PMC chart ─────────────────────────────────────────────────────────────
    pmc12 = pmc[pmc['date'] >= pd.Timestamp(today-timedelta(days=365))].copy()
    # Weekly aggregation for PMC (end-of-week)
    pmc12['week'] = pmc12['date'].dt.to_period('W').dt.end_time.dt.date
    pmc_w = pmc12.groupby('week').agg(ctl=('ctl','last'),atl=('atl','last'),tsb=('tsb','last')).reset_index()

    # ── HRV / RHR ─────────────────────────────────────────────────────────────
    def rolling_series(key, days=730, win=7):
        d = daily.get(key)
        if d is None or d.empty: return [], [], []
        df2 = d.copy()
        df2['date'] = pd.to_datetime(df2['date'])
        df2 = df2[df2['date'] >= pd.Timestamp(today-timedelta(days=days))].sort_values('date')
        df2['roll'] = df2['value'].rolling(win, min_periods=1).mean()
        return df2['date'].dt.strftime('%Y-%m-%d').tolist(), df2['value'].round(1).tolist(), df2['roll'].round(1).tolist()

    hrv_d, hrv_v, hrv_r = rolling_series("HKQuantityTypeIdentifierHeartRateVariabilitySDNN")
    rhr_d, rhr_v, rhr_r = rolling_series("HKQuantityTypeIdentifierRestingHeartRate")
    vo2_d, vo2_v, _     = rolling_series("HKQuantityTypeIdentifierVO2Max", days=3000, win=1)

    # ── Activity heatmap (contributions GitHub-style) ─────────────────────────
    heat_start  = pd.Timestamp(today - timedelta(days=364))
    heat_df     = df[df['date'] >= heat_start].copy()
    heat_counts = heat_df.groupby(heat_df['date'].dt.date).size().reset_index()
    heat_counts.columns = ['date', 'n']
    heat_dict   = {str(r['date']): int(r['n']) for _, r in heat_counts.iterrows()}

    # ── Activity breakdown (12 months) ───────────────────────────────────────
    act12 = df[df['date'] >= pd.Timestamp(today-timedelta(days=365))]
    act_g = act12.groupby('type').agg(n=('duration_min','count'), h=('duration_min','sum'))
    act_g['h'] = (act_g['h'] / 60).round(1)
    act_g = act_g.sort_values('h', ascending=False)
    act_labels = [f"{SPORT_ICONS.get(t,'🏋️')} {t}" for t in act_g.index]
    act_hours  = act_g['h'].tolist()
    act_counts = act_g['n'].tolist()

    # ── This week ─────────────────────────────────────────────────────────────
    week_start = today - timedelta(days=today.weekday())
    tw = df[df['date'].dt.date >= week_start]
    tw_n   = len(tw)
    tw_h   = round(tw['duration_min'].sum() / 60, 1)
    tw_cal = int(tw['calories'].sum())
    tw_km  = round(tw[tw['type']=='Course à pied']['distance_km'].sum(), 1)

    # ── YoY ──────────────────────────────────────────────────────────────────
    def ystats(y):
        r = df[df['year'] == y]
        rn = r[r['type'] == 'Course à pied']
        return dict(n=len(r), h=round(r['duration_min'].sum()/60,1),
                    run_km=round(rn['distance_km'].sum(),1),
                    cal=int(r['calories'].sum()))
    cy, ly = today.year, today.year-1
    this_y, last_y = ystats(cy), ystats(ly)

    # ── Race predictions ──────────────────────────────────────────────────────
    pace_r5 = run_stats.get('avg_pace_r5', 6.5)
    avg_d   = run_stats.get('avg_dist_r10', 5.0)
    pred_5k    = pace_r5 * 5
    pred_10k   = riegel_predict(avg_d, pace_r5 * avg_d, 10.0) or pace_r5 * 10 * 1.05
    pred_hm    = riegel_predict(avg_d, pace_r5 * avg_d, 21.1) or None
    vdot_final = run_stats.get('vdot_est') or (vo2max or 50)
    tier_name, tier_pct, tier_col = fitness_tier(pace_r5, vdot_final)

    # ── Recent 10 sessions ───────────────────────────────────────────────────
    rec10 = df.nlargest(10, 'date')[
        ['date','type','duration_min','distance_km','calories','pace_min_km','avg_hr','source']
    ].copy()
    rec10['date_s']   = rec10['date'].dt.strftime('%d/%m/%Y')
    rec10['dur_s']    = rec10['duration_min'].apply(fmt_time)
    rec10['dist_s']   = rec10['distance_km'].apply(lambda x: f"{x:.1f} km" if x > 0 else "—")
    rec10['pace_s']   = rec10['pace_min_km'].apply(fmt_pace)
    rec10['cal_s']    = rec10['calories'].apply(lambda x: f"{int(x)}" if x > 0 else "—")
    rec10['hr_s']     = rec10['avg_hr'].apply(lambda x: f"{int(x)}" if pd.notna(x) and x > 0 else "—")
    rec10['icon']     = rec10['type'].apply(lambda t: SPORT_ICONS.get(t,'🏋️'))
    rec10_rows = rec10[['icon','type','date_s','dur_s','dist_s','pace_s','cal_s','hr_s','source']].to_dict('records')

    # ── Score bars ────────────────────────────────────────────────────────────
    def score_bar(label, val, w_pct=None):
        fv = float(val) if val is not None else 0.0
        fv = 0.0 if (np.isnan(fv) or np.isinf(fv)) else fv
        v = int(np.clip(round(fv), 0, 100))
        col = sc(v)
        wp = f"{w_pct}%" if w_pct else f"{v}%"
        return f"""<div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">
            <span style="color:#94a3b8">{label}</span><span style="color:{col};font-weight:700">{v}/100</span>
          </div>
          <div style="background:#0f172a;border-radius:4px;height:5px">
            <div style="width:{v}%;height:5px;border-radius:4px;background:{col};transition:width .6s ease"></div>
          </div></div>"""

    # ── Plan session rows ─────────────────────────────────────────────────────
    TYPE_COLORS = {"récupération":"#475569","endurance":"#3b82f6","vitesse":"#a855f7",
                   "force":"#22c55e","seuil":"#f59e0b"}
    plan_rows = "".join(f"""
    <div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #1e293b22">
      <div style="min-width:80px;font-size:12px;font-weight:600;color:#94a3b8;padding-top:2px">{p[0]}</div>
      <div style="flex:1;font-size:13px;color:#cbd5e1">{p[1]}</div>
      <div style="background:{TYPE_COLORS.get(p[2],'#475569')}22;color:{TYPE_COLORS.get(p[2],'#94a3b8')};
           padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;white-space:nowrap">{p[2].upper()}</div>
    </div>""" for p in coaching['plan'])

    block_cards = "".join(f"""
    <div style="background:#0f172a;border-radius:12px;padding:16px;border:1px solid #1e293b">
      <div style="font-size:12px;font-weight:700;color:#64748b;margin-bottom:6px">{b['week']}</div>
      <div style="font-size:14px;font-weight:600;color:#e2e8f0;margin-bottom:10px">{b['label']}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px">
        <div style="color:#64748b">Km cible</div><div style="color:#60a5fa;font-weight:600">{b['km_target']} km</div>
        <div style="color:#64748b">Séances</div><div style="color:#e2e8f0">{b['sessions']}</div>
        <div style="color:#64748b">Intensité</div><div style="color:#f59e0b">{b['intensity']}</div>
      </div>
    </div>""" for b in coaching['block'])

    # ── Heatmap (52 weeks × 7 days) ──────────────────────────────────────────
    def build_heatmap_html():
        # Build 52 weeks grid
        # Each cell = 1 day, color = activity count
        cols_html = []
        for week_i in range(52, -1, -1):
            week_end = today - timedelta(days=today.weekday()) + timedelta(days=6) - timedelta(weeks=week_i)
            week_days = [week_end - timedelta(days=6-d) for d in range(7)]
            cells = []
            for d in week_days:
                ds = str(d.date()) if hasattr(d,'date') else str(d)
                n  = heat_dict.get(ds, 0)
                col = "#1e293b" if n == 0 else ("#22c55e44" if n==1 else ("#22c55e88" if n==2 else "#22c55e"))
                cells.append(f'<div style="width:11px;height:11px;border-radius:2px;background:{col};margin:1px" title="{ds}: {n} activité(s)"></div>')
            cols_html.append(f'<div>{"".join(cells)}</div>')
        return f'<div style="display:flex;gap:2px;overflow-x:auto">{"".join(cols_html)}</div>'

    # ── Chart data object ─────────────────────────────────────────────────────
    CD = {
        "run_dates":    run_2y['date'].dt.strftime('%Y-%m-%d').tolist(),
        "run_pace":     run_2y['pace_min_km'].round(2).tolist(),
        "run_trend":    [round(v,2) for v in trend_y],
        "run_dist":     run_2y['distance_km'].round(2).tolist(),
        "run_hr":       run_2y['avg_hr'].fillna(0).round(0).tolist(),

        "y_years":  y_years, "y_km": y_km, "y_pace": y_pace,

        "wkly_dates": wkly_dates, "wkly_km": wkly_km,

        "pmc_dates": pmc_w['week'].astype(str).tolist(),
        "pmc_ctl":   pmc_w['ctl'].round(1).tolist(),
        "pmc_atl":   pmc_w['atl'].round(1).tolist(),
        "pmc_tsb":   pmc_w['tsb'].round(1).tolist(),

        "hrv_d": hrv_d, "hrv_v": hrv_v, "hrv_r": hrv_r,
        "rhr_d": rhr_d, "rhr_v": rhr_v, "rhr_r": rhr_r,
        "vo2_d": vo2_d, "vo2_v": vo2_v,

        "act_labels": act_labels, "act_hours": act_hours, "act_counts": act_counts,
    }

    report_date = today.strftime("%d %B %Y")

    # ── Render HTML ───────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Health Report · {report_date}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
:root{{--bg:#080c14;--card:#111827;--card2:#0f172a;--border:#1e293b;--text:#e2e8f0;--muted:#64748b;--accent:#3b82f6}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Segoe UI',sans-serif;background:var(--bg);color:var(--text);line-height:1.5}}
.topbar{{background:linear-gradient(135deg,#0f172a,#080c14);border-bottom:1px solid var(--border);padding:20px 32px;display:flex;justify-content:space-between;align-items:center}}
.topbar-title{{font-size:20px;font-weight:700;letter-spacing:-.3px}}
.topbar-sub{{font-size:12px;color:var(--muted);margin-top:2px}}
.topbar-meta{{font-size:12px;color:var(--muted);text-align:right}}
.page{{max-width:1440px;margin:0 auto;padding:24px}}
.section-hdr{{font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);font-weight:700;margin:28px 0 14px}}
.grid{{display:grid;gap:14px}}
.g2{{grid-template-columns:repeat(2,1fr)}}.g3{{grid-template-columns:repeat(3,1fr)}}.g4{{grid-template-columns:repeat(4,1fr)}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px}}
.card-sm{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}}
.card-title{{font-size:12px;font-weight:600;color:var(--muted);margin-bottom:14px;letter-spacing:.3px}}
.kv{{font-size:30px;font-weight:800;color:#fff;line-height:1}}
.kl{{font-size:11px;color:var(--muted);margin-top:5px}}
.ks{{font-size:11px;color:#475569;margin-top:3px}}
.ch{{height:240px}}
.ch-tall{{height:300px}}
.ring-wrap{{display:flex;flex-direction:column;align-items:center;padding:8px 0 16px}}
.score-num{{font-size:44px;font-weight:800;line-height:1}}
.score-lbl{{font-size:13px;font-weight:600;margin-top:4px}}
.score-sub{{font-size:11px;color:var(--muted);margin-top:2px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{padding:9px 14px;text-align:left;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.8px;border-bottom:1px solid var(--border);font-weight:600}}
td{{padding:9px 14px;border-bottom:1px solid #0f172a;color:#cbd5e1}}
tr:hover td{{background:#1e293b33}}
.badge{{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}}
.up{{background:#14532d33;color:#4ade80;border:1px solid #14532d55}}
.down{{background:#4c051933;color:#fb7185;border:1px solid #4c051955}}
.neutral{{background:var(--border);color:var(--muted)}}
.pill{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}}
.pred-card{{background:var(--card2);border-radius:10px;padding:14px;text-align:center}}
.pred-val{{font-size:22px;font-weight:800;color:#fff}}
.pred-lbl{{font-size:11px;color:var(--muted);margin-top:4px}}
.tier-bar{{background:var(--card2);border-radius:12px;padding:20px;display:flex;align-items:center;gap:16px}}
.coach-box{{background:var(--card2);border-radius:12px;padding:16px;border-left:3px solid #3b82f6;margin-bottom:14px;font-size:13px;color:#94a3b8;line-height:1.6}}
@media(max-width:900px){{.g2,.g3,.g4{{grid-template-columns:1fr}}}}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <div class="topbar-title">⚡ Health Dashboard · Simon Hingant</div>
    <div class="topbar-sub">Rapport du {report_date} · Apple Health + Strava · {len(df)} séances totales</div>
  </div>
  <div class="topbar-meta">
    {age_v} ans · Masculin<br>
    <span style="color:#3b82f6">●</span> Apple Health &nbsp; <span style="color:#f97316">●</span> Strava
  </div>
</div>

<div class="page">

<!-- ═══════════════════════════════════════════════════════════ SCORES & KPIs -->
<div class="section-hdr">Vue d'ensemble</div>
<div class="grid g4">

  <!-- Score forme -->
  <div class="card" style="grid-row:span 2">
    <div class="card-title">Forme actuelle</div>
    <div class="ring-wrap">
      <svg width="130" height="130" style="transform:rotate(-90deg)">
        <circle cx="65" cy="65" r="56" fill="none" stroke="#1e293b" stroke-width="10"/>
        <circle cx="65" cy="65" r="56" fill="none" stroke="{sc(form)}" stroke-width="10"
          stroke-dasharray="351.9" stroke-dashoffset="{351.9 - 351.9*form/100:.1f}" stroke-linecap="round"/>
      </svg>
      <div style="margin-top:-10px;text-align:center">
        <div class="score-num" style="color:{sc(form)}">{form}</div>
        <div class="score-lbl" style="color:{sc(form)}">{"Excellent 🔥" if form>=78 else "Bon 💪" if form>=60 else "Moyen ⚡" if form>=45 else "À récupérer 😴"}</div>
        <div class="score-sub">/100</div>
      </div>
    </div>
    <div style="padding:0 4px">
      {"".join(score_bar(k.replace('_',' ').title(), v) for k,v in scores.items())}
    </div>
  </div>

  <!-- Score Wakeboard -->
  <div class="card" style="grid-row:span 2">
    <div class="card-title">🏄 Wakeboard Ready</div>
    <div class="ring-wrap">
      <svg width="130" height="130" style="transform:rotate(-90deg)">
        <circle cx="65" cy="65" r="56" fill="none" stroke="#1e293b" stroke-width="10"/>
        <circle cx="65" cy="65" r="56" fill="none" stroke="{sc(wake)}" stroke-width="10"
          stroke-dasharray="351.9" stroke-dashoffset="{351.9 - 351.9*wake/100:.1f}" stroke-linecap="round"/>
      </svg>
      <div style="margin-top:-10px;text-align:center">
        <div class="score-num" style="color:{sc(wake)}">{wake}</div>
        <div class="score-lbl" style="color:{sc(wake)}">{"Prêt à rider 🤙" if wake>=72 else "Bonne condition 👍" if wake>=55 else "Encore un peu 💪"}</div>
        <div class="score-sub">/100</div>
      </div>
    </div>
    <div style="padding:0 4px">
      {"".join(score_bar(k.replace('_',' ').title(), v) for k,v in wake_c.items())}
    </div>
  </div>

  <!-- Cette semaine -->
  <div class="card">
    <div class="card-title">📅 Cette semaine</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="card-sm" style="padding:12px">
        <div class="kv" style="font-size:24px">{tw_n}</div><div class="kl">Séances</div>
      </div>
      <div class="card-sm" style="padding:12px">
        <div class="kv" style="font-size:24px">{tw_h}h</div><div class="kl">Volume</div>
      </div>
      <div class="card-sm" style="padding:12px">
        <div class="kv" style="font-size:24px">{tw_km} km</div><div class="kl">Distance run</div>
      </div>
      <div class="card-sm" style="padding:12px">
        <div class="kv" style="font-size:24px">{tw_cal}</div><div class="kl">kcal</div>
      </div>
    </div>
  </div>

  <!-- Métriques santé -->
  <div class="card">
    <div class="card-title">❤️ Biomarqueurs</div>
    <div style="display:flex;flex-direction:column;gap:8px">
      <div class="card-sm" style="padding:12px;display:flex;justify-content:space-between;align-items:center">
        <div><div class="kv" style="font-size:24px;color:#fb7185">{f"{int(rhr)}" if rhr else "—"}</div><div class="kl">FC repos (bpm)</div></div>
        <div style="font-size:26px">💓</div>
      </div>
      <div class="card-sm" style="padding:12px;display:flex;justify-content:space-between;align-items:center">
        <div><div class="kv" style="font-size:24px;color:#a78bfa">{f"{int(hrv)}" if hrv else "—"}</div><div class="kl">HRV (ms SDNN)</div></div>
        <div style="font-size:26px">📊</div>
      </div>
      <div class="card-sm" style="padding:12px;display:flex;justify-content:space-between;align-items:center">
        <div><div class="kv" style="font-size:24px;color:#06b6d4">{f"{vo2max:.1f}" if vo2max else "—"}</div><div class="kl">VO2Max Apple Watch</div></div>
        <div style="font-size:26px">🫁</div>
      </div>
    </div>
  </div>

</div>

<!-- ═══════════════════════════════════════════════════════════ PERFORMANCE COURSE -->
<div class="section-hdr">🏃 Performance Course à pied</div>

<!-- Niveau & Prédictions -->
<div class="card" style="margin-bottom:14px">
  <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
    <div class="tier-bar" style="flex:1;min-width:200px">
      <div style="width:50px;height:50px;border-radius:50%;background:{tier_col}22;border:2px solid {tier_col};
           display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0">🏃</div>
      <div>
        <div style="font-size:16px;font-weight:700;color:{tier_col}">{tier_name}</div>
        <div style="font-size:12px;color:var(--muted)">Niveau estimé · VO2Max ≈ {round(vdot_final) if vdot_final else "N/A"} mL/kg/min</div>
        <div style="margin-top:8px;background:var(--bg);border-radius:6px;height:6px;width:200px">
          <div style="width:{tier_pct}%;height:6px;border-radius:6px;background:{tier_col}"></div>
        </div>
        <div style="font-size:10px;color:#334155;margin-top:3px">Percentile {tier_pct}ème parmi coureurs réguliers masculins 30-35 ans</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;flex:1;min-width:300px">
      <div class="pred-card">
        <div class="pred-val" style="color:#60a5fa">{fmt_pace(pace_r5)}</div>
        <div class="pred-lbl">Allure récente<br>(moy. 5 dernières)</div>
      </div>
      <div class="pred-card">
        <div class="pred-val" style="color:#34d399">{fmt_time(pred_5k*60)}</div>
        <div class="pred-lbl">5 km estimé</div>
      </div>
      <div class="pred-card">
        <div class="pred-val" style="color:#fbbf24">{fmt_time(pred_10k*60) if pred_10k else "—"}</div>
        <div class="pred-lbl">10 km estimé</div>
      </div>
      <div class="pred-card">
        <div class="pred-val" style="color:#f87171">{fmt_time(pred_hm*60) if pred_hm else "—"}</div>
        <div class="pred-lbl">Semi estimé</div>
      </div>
    </div>
  </div>
</div>

<div class="grid g2">
  <div class="card">
    <div class="card-title">Évolution de l'allure (24 mois) — tendance incluse</div>
    <div id="ch-pace" class="ch-tall"></div>
  </div>
  <div class="card">
    <div class="card-title">Volume km / semaine (12 mois)</div>
    <div id="ch-wkly" class="ch-tall"></div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════ ANNÉE PAR ANNÉE -->
<div class="section-hdr">📅 Analyse Annuelle</div>
<div class="grid g2">
  <div class="card">
    <div class="card-title">Km de course par année</div>
    <div id="ch-ykm" class="ch"></div>
  </div>
  <div class="card">
    <div class="card-title">Allure moyenne par année</div>
    <div id="ch-ypace" class="ch"></div>
  </div>
</div>

<!-- YoY table -->
<div class="card" style="margin-top:14px">
  <div class="card-title">{cy} vs {ly} — comparaison clés</div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:4px">
    {"".join(f'''<div class="card-sm" style="text-align:center;padding:16px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:8px">{lbl}</div>
      <div style="font-size:22px;font-weight:800;color:#fff">{cv}{unit}</div>
      <div style="font-size:11px;color:var(--muted);margin-top:4px">{ly}: {lv}{unit}</div>
      <span class="badge {pct_diff(cv,lv)[1]}" style="margin-top:6px;display:inline-block">{pct_diff(cv,lv)[0]}</span>
    </div>'''
    for lbl, cv, lv, unit in [
        ("Séances", this_y['n'], last_y['n'], ""),
        ("Km course", this_y['run_km'], last_y['run_km'], " km"),
        ("Heures sport", this_y['h'], last_y['h'], " h"),
        ("Kcal brûlées", this_y['cal'], last_y['cal'], ""),
    ])}
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════ CHARGE + CARDIO -->
<div class="section-hdr">⚡ Charge d'entraînement & Récupération</div>
<div class="grid g2">
  <div class="card">
    <div class="card-title">Performance Management Chart (PMC) — 12 mois</div>
    <div id="ch-pmc" class="ch-tall"></div>
    <div style="font-size:10px;color:#334155;margin-top:8px">
      🔵 CTL Fitness (42j EWM) · 🔴 ATL Fatigue (7j EWM) · 🟡 TSB Forme = CTL−ATL · TSS proxy: 1 kcal ≈ 0.2 TSS
    </div>
  </div>
  <div class="card">
    <div class="card-title">Activité sur 12 mois (heatmap)</div>
    <div style="margin-top:8px">
      {build_heatmap_html()}
    </div>
    <div style="font-size:10px;color:#334155;margin-top:10px">
      Chaque colonne = 1 semaine · Chaque cellule = 1 jour · Couleur = nb d'activités
    </div>
    <div style="margin-top:16px">
      <div class="card-title" style="margin-bottom:8px">Répartition des activités (12 mois)</div>
      <div id="ch-act" style="height:180px"></div>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════ SANTÉ CARDIAQUE -->
<div class="section-hdr">❤️ Santé Cardiaque & VO2Max</div>
<div class="grid g3">
  <div class="card">
    <div class="card-title">HRV — Variabilité cardiaque (SDNN)</div>
    <div id="ch-hrv" class="ch"></div>
  </div>
  <div class="card">
    <div class="card-title">FC au repos — Tendance longue durée</div>
    <div id="ch-rhr" class="ch"></div>
  </div>
  <div class="card">
    <div class="card-title">VO2Max Apple Watch — Historique</div>
    <div id="ch-vo2" class="ch"></div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px">
      <div class="pred-card" style="padding:10px">
        <div style="font-size:11px;color:#4ade80;font-weight:700">> 52</div>
        <div style="font-size:10px;color:var(--muted)">Excellent</div>
      </div>
      <div class="pred-card" style="padding:10px">
        <div style="font-size:11px;color:#fbbf24;font-weight:700">43–52</div>
        <div style="font-size:10px;color:var(--muted)">Bon</div>
      </div>
      <div class="pred-card" style="padding:10px">
        <div style="font-size:11px;color:#f87171;font-weight:700">< 43</div>
        <div style="font-size:10px;color:var(--muted)">Moyen</div>
      </div>
    </div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════ COACH SECTION -->
<div class="section-hdr">🧠 Analyse Coach & Programme</div>
<div class="grid g2">

  <!-- Coach analysis -->
  <div>
    <div class="card" style="margin-bottom:14px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <div style="width:38px;height:38px;border-radius:50%;background:#1e293b;display:flex;align-items:center;justify-content:center;font-size:20px">🧠</div>
        <div>
          <div style="font-size:15px;font-weight:700;color:#e2e8f0">{coaching['advice_title']}</div>
          <div style="font-size:11px;color:var(--muted)">Analyse basée sur tes données des 4 dernières semaines</div>
        </div>
      </div>
      <div class="coach-box">{coaching['assessment']}</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px">
        <div class="card-sm" style="padding:12px;text-align:center">
          <div style="font-size:20px;font-weight:800;color:#60a5fa">{coaching['n_runs_4w']}</div>
          <div style="font-size:10px;color:var(--muted)">courses (4 sem.)</div>
        </div>
        <div class="card-sm" style="padding:12px;text-align:center">
          <div style="font-size:20px;font-weight:800;color:#34d399">{coaching['km_4w']}</div>
          <div style="font-size:10px;color:var(--muted)">km courus</div>
        </div>
        <div class="card-sm" style="padding:12px;text-align:center">
          <div style="font-size:20px;font-weight:800;color:#fbbf24">{coaching['n_str_4w']}</div>
          <div style="font-size:10px;color:var(--muted)">séances muscu</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title" style="margin-bottom:0">Programme 4 semaines</div>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:14px">
        {block_cards}
      </div>
    </div>
  </div>

  <!-- Weekly plan -->
  <div class="card">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
      <span style="font-size:16px">📋</span>
      <div style="font-size:14px;font-weight:700;color:#e2e8f0">Plan de la semaine prochaine</div>
    </div>
    {plan_rows}
    <div class="coach-box" style="margin-top:16px;border-left-color:#22c55e">
      <strong style="color:#4ade80">Rappel clé :</strong>
      Ta FC au repos à {f"{int(rhr)}" if rhr else "~58"} bpm est excellente pour ton âge.
      Ton VO2Max mesuré à {f"{vo2max:.1f}" if vo2max else "N/A"} mL/kg/min te place dans le top {"25%" if (vo2max or 50) > 50 else "40%"} des hommes de 30-35 ans.
      {"L'objectif principal est la régularité — 3 à 4 séances/semaine suffisent pour progresser significativement." if coaching['phase'] in ('reprise','faible_charge') else
       "Maintiens ce rythme et concentre-toi sur la qualité des séances plutôt que le volume brut." if coaching['phase'] == 'progression' else
       "Cette semaine, la récupération EST l'entraînement. Un corps reposé progresse plus vite qu'un corps épuisé."}
    </div>
  </div>

</div>

<!-- ═══════════════════════════════════════════════════════════ DERNIÈRES SÉANCES -->
<div class="section-hdr">🕐 10 dernières séances</div>
<div class="card">
  <table>
    <thead><tr>
      <th>Activité</th><th>Date</th><th>Durée</th>
      <th>Distance</th><th>Allure</th><th>kcal</th><th>FC moy.</th><th>Source</th>
    </tr></thead>
    <tbody>
    {"".join(f'''<tr>
      <td><span style="margin-right:6px">{r["icon"]}</span>{r["type"]}</td>
      <td style="color:var(--muted)">{r["date_s"]}</td>
      <td>{r["dur_s"]}</td>
      <td>{r["dist_s"]}</td>
      <td style="color:#60a5fa;font-family:monospace">{r["pace_s"]}</td>
      <td>{r["cal_s"]}</td>
      <td style="color:#fb7185">{r["hr_s"]}</td>
      <td><span style="padding:2px 7px;border-radius:10px;font-size:10px;font-weight:600;
        background:{"#f9731622" if r["source"]=="Strava" else "#3b82f622"};
        color:{"#f97316" if r["source"]=="Strava" else "#60a5fa"}">{r["source"]}</span></td>
    </tr>''' for r in rec10_rows)}
    </tbody>
  </table>
</div>

<div style="text-align:center;padding:32px 0 16px;font-size:11px;color:#1e293b">
  Généré le {report_date} · Health Dashboard · Simon Hingant · Apple Health + Strava
</div>

</div><!-- /page -->

<script>
const D = {json.dumps(CD)};
const B = {{
  paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{{color:'#64748b',size:11}},
  margin:{{t:8,r:12,b:36,l:44}},
  xaxis:{{gridcolor:'#1e293b',linecolor:'#1e293b',showgrid:true,zeroline:false}},
  yaxis:{{gridcolor:'#1e293b',linecolor:'#1e293b',showgrid:true,zeroline:false}},
  legend:{{bgcolor:'rgba(0,0,0,0)',font:{{color:'#64748b',size:10}},orientation:'h',y:-0.2}},
  hovermode:'x unified',
  hoverlabel:{{bgcolor:'#1e293b',bordercolor:'#334155',font:{{color:'#e2e8f0',size:12}}}},
}};
const C = {{responsive:true,displayModeBar:false}};
function fp(v){{if(!v||v<=0||v>15)return'';const m=Math.floor(v),s=Math.round((v-m)*60);return m+':'+(s<10?'0':'')+s+'/km'}}
function fh(s){{if(!s)return'';const h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=s%60;return h?h+'h'+String(m).padStart(2,'0'):m+':'+String(sec).padStart(2,'0')}}

// ── Allure course ────────────────────────────────────────────────────────────
Plotly.newPlot('ch-pace',[
  {{x:D.run_dates,y:D.run_pace,mode:'markers',name:'Allure',
    marker:{{color:'#3b82f6',size:7,opacity:0.45}},
    customdata:D.run_pace.map(fp),
    hovertemplate:'%{{x}}<br>%{{customdata}}<br>%{{text}} km<extra></extra>',
    text:D.run_dist}},
  {{x:D.run_dates,y:D.run_trend,mode:'lines',name:'Tendance',
    line:{{color:'#60a5fa',width:2.5,dash:'solid'}}}},
],{{...B,yaxis:{{...B.yaxis,autorange:'reversed',title:'min/km',
  ticktext:['4:30','5:00','5:30','6:00','6:30','7:00','7:30'],
  tickvals:[4.5,5,5.5,6,6.5,7,7.5]}}}},C);

// ── Volume hebdo ─────────────────────────────────────────────────────────────
Plotly.newPlot('ch-wkly',[
  {{x:D.wkly_dates,y:D.wkly_km,type:'bar',name:'km/semaine',
    marker:{{color:'#22c55e',opacity:0.75,line:{{width:0}}}},
    hovertemplate:'%{{x}}<br>%{{y:.1f}} km<extra></extra>'}},
],{{...B,yaxis:{{...B.yaxis,title:'km'}}}},C);

// ── Km par année ─────────────────────────────────────────────────────────────
Plotly.newPlot('ch-ykm',[
  {{x:D.y_years,y:D.y_km,type:'bar',name:'Km de course',
    marker:{{color:D.y_years.map(y=>y==={cy}?'#3b82f6':'#1e3a5f')}},
    text:D.y_km.map(v=>v.toFixed(0)+' km'),textposition:'outside',
    hovertemplate:'%{{x}}: %{{y:.0f}} km<extra></extra>'}},
],{{...B,yaxis:{{...B.yaxis,title:'km'}},showlegend:false}},C);

// ── Allure par année ──────────────────────────────────────────────────────────
Plotly.newPlot('ch-ypace',[
  {{x:D.y_years,y:D.y_pace,type:'scatter',mode:'lines+markers',name:'Allure moy.',
    line:{{color:'#f59e0b',width:2.5}},
    marker:{{color:D.y_years.map(y=>y==={cy}?'#fbbf24':'#78350f'),size:9}},
    customdata:D.y_pace.map(fp),
    hovertemplate:'%{{x}}: %{{customdata}}<extra></extra>'}},
],{{...B,yaxis:{{...B.yaxis,autorange:'reversed',title:'min/km',
  ticktext:['5:00','5:30','6:00','6:30','7:00','7:30'],tickvals:[5,5.5,6,6.5,7,7.5]}},showlegend:false}},C);

// ── PMC ──────────────────────────────────────────────────────────────────────
Plotly.newPlot('ch-pmc',[
  {{x:D.pmc_dates,y:D.pmc_ctl,mode:'lines',name:'Fitness (CTL)',line:{{color:'#3b82f6',width:2.5}}}},
  {{x:D.pmc_dates,y:D.pmc_atl,mode:'lines',name:'Fatigue (ATL)',line:{{color:'#ef4444',width:2}}}},
  {{x:D.pmc_dates,y:D.pmc_tsb,mode:'lines',name:'Forme (TSB)',
    line:{{color:'#f59e0b',width:2.5}},fill:'tozeroy',fillcolor:'rgba(245,158,11,0.07)'}},
  {{x:D.pmc_dates,y:Array(D.pmc_dates.length).fill(0),mode:'lines',showlegend:false,
    line:{{color:'#334155',width:1,dash:'dot'}}}},
],{{...B}},C);

// ── Activités ────────────────────────────────────────────────────────────────
Plotly.newPlot('ch-act',[
  {{labels:D.act_labels,values:D.act_hours,type:'pie',hole:0.5,
    marker:{{colors:['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#14b8a6','#f97316']}},
    textinfo:'label+percent',textfont:{{color:'#e2e8f0',size:10}},
    hovertemplate:'%{{label}}<br>%{{value:.1f}}h · %{{percent}}<extra></extra>'}},
],{{...B,margin:{{t:0,r:0,b:0,l:0}},legend:{{x:1.05,y:0.5}}}},C);

// ── HRV ──────────────────────────────────────────────────────────────────────
Plotly.newPlot('ch-hrv',[
  {{x:D.hrv_d,y:D.hrv_v,mode:'markers',name:'HRV SDNN',marker:{{color:'#a78bfa',size:5,opacity:0.4}}}},
  {{x:D.hrv_d,y:D.hrv_r,mode:'lines',name:'Moy. 7j',line:{{color:'#c4b5fd',width:2.5}}}},
],{{...B,yaxis:{{...B.yaxis,title:'ms'}}}},C);

// ── FC repos ─────────────────────────────────────────────────────────────────
Plotly.newPlot('ch-rhr',[
  {{x:D.rhr_d,y:D.rhr_v,mode:'markers',name:'FC repos',marker:{{color:'#f43f5e',size:5,opacity:0.4}}}},
  {{x:D.rhr_d,y:D.rhr_r,mode:'lines',name:'Moy. 7j',line:{{color:'#fb7185',width:2.5}}}},
],{{...B,yaxis:{{...B.yaxis,autorange:'reversed',title:'bpm'}}}},C);

// ── VO2Max ────────────────────────────────────────────────────────────────────
Plotly.newPlot('ch-vo2',[
  {{x:D.vo2_d,y:D.vo2_v,mode:'lines+markers',name:'VO2Max',
    line:{{color:'#06b6d4',width:2.5}},marker:{{size:8,color:'#06b6d4'}}}},
  {{x:D.vo2_d,y:Array(D.vo2_d.length).fill(52),mode:'lines',name:'Excellent (52)',
    line:{{color:'#22c55e',width:1,dash:'dot'}}}},
  {{x:D.vo2_d,y:Array(D.vo2_d.length).fill(43),mode:'lines',name:'Bon (43)',
    line:{{color:'#f59e0b',width:1,dash:'dot'}}}},
],{{...B,yaxis:{{...B.yaxis,title:'mL/kg/min',range:[35,65]}}}},C);
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding='utf-8')
    sz = output_path.stat().st_size
    print(f"✅ Dashboard → {output_path} ({sz/1024:.0f} KB)")
    return output_path

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-cache', action='store_true')
    parser.add_argument('--output',   default=None)
    parser.add_argument('--open',     action='store_true')
    args = parser.parse_args()

    today = date.today()
    out   = Path(args.output) if args.output else OUTPUT_DIR / f"dashboard_{today:%Y-%m-%d}.html"

    print(f"\n{'═'*58}")
    print(f"  ⚡  Health Dashboard — Simon Hingant")
    print(f"  {today:%d %B %Y}")
    print(f"{'═'*58}\n")

    # Load / parse Apple Health
    use_cache = CACHE_FILE.exists() and not args.no_cache and \
                CACHE_FILE.stat().st_mtime >= EXPORT_XML.stat().st_mtime
    if use_cache:
        print("⚡ Apple Health: chargement depuis cache…")
        ah_workouts, ah_records = pickle.load(open(CACHE_FILE,'rb'))
    else:
        ah_workouts, ah_records = parse_apple_health(EXPORT_XML)
        pickle.dump((ah_workouts, ah_records), open(CACHE_FILE,'wb'))
        print("💾 Cache AH sauvegardé")

    # Load Strava
    strava_df = load_strava(STRAVA_CSV)

    # Merge
    df_all = build_unified(ah_workouts, strava_df)

    # Daily health metrics
    daily = build_daily_metrics(ah_records)

    # PMC
    pmc = build_pmc(df_all)

    # Run analysis
    run_df = df_all[df_all['type'] == 'Course à pied'].copy()
    run_df = run_df[run_df['pace_min_km'].notna()]
    run_stats = analyze_running(run_df)
    print(f"🏃 Running: {run_stats.get('total_runs',0)} séances · "
          f"allure récente {fmt_pace(run_stats.get('avg_pace_r5'))} · "
          f"VO2Max estimé {round(run_stats.get('vdot_est') or 0)}")

    # Coaching
    coaching = generate_coaching(df_all, run_stats, daily, pmc)

    # Generate
    report = generate_html(df_all, daily, pmc, run_stats, coaching, out)
    print(f"\n🎉 Rapport prêt → file://{report.resolve()}\n")

    if args.open:
        import subprocess
        subprocess.run(['open', str(report)], check=False)

if __name__ == '__main__':
    main()
