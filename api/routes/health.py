"""Routes métriques santé et readiness."""

from __future__ import annotations

from fastapi import APIRouter

from analytics.muscle_groups import analyze_imbalances, get_cumulative_volume
from analytics.training_load import (
    build_daily_tss,
    compute_acwr,
    compute_pmc,
    compute_wakeboard_score,
    compute_weekly_trends,
    generate_highlights,
    get_health_metrics,
    analyze_running,
)
from api.deps import get_db

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/metrics")
def health_metrics() -> dict:
    """Retourne toutes les métriques santé avec fraîcheur."""
    conn = get_db()
    try:
        metrics = get_health_metrics(conn)
        return {"ok": True, "metrics": metrics}
    finally:
        conn.close()


@router.get("/rings")
def health_rings() -> dict:
    """Retourne les scores des 3 anneaux (Recovery, Activity, Sleep)."""
    conn = get_db()
    try:
        metrics = get_health_metrics(conn)
        daily_tss = build_daily_tss(conn)
        pmc = compute_pmc(daily_tss)
        acwr = compute_acwr(daily_tss)

        # Recovery ring : basé sur le readiness score
        freshness = {
            "hrv": metrics.get("hrv_freshness", 0),
            "sleep": metrics.get("sleep_freshness", 0),
            "rhr": metrics.get("rhr_freshness", 0),
            "body_battery": metrics.get("body_battery_freshness", 0),
        }
        readiness = compute_wakeboard_score(
            hrv_val=metrics.get("hrv"),
            hrv_baseline=metrics.get("hrv_baseline"),
            sleep_h=metrics.get("sleep_h"),
            acwr_val=acwr.get("acwr", 0),
            rhr_val=metrics.get("rhr"),
            rhr_baseline=metrics.get("rhr_baseline"),
            body_battery=metrics.get("body_battery"),
            freshness=freshness,
        )

        # Activity ring : basé sur ACWR (0.8-1.3 = 100%)
        acwr_val = acwr.get("acwr", 0)
        if 0.8 <= acwr_val <= 1.3:
            activity_score = 100
        elif acwr_val < 0.8:
            activity_score = int(acwr_val / 0.8 * 100)
        else:
            activity_score = max(0, int(100 - (acwr_val - 1.3) / 0.7 * 100))

        # Sleep ring : basé sur les heures de sommeil
        sleep_h = metrics.get("sleep_h") or 0
        if 7.5 <= sleep_h <= 9.0:
            sleep_score = 100
        elif sleep_h >= 6.5:
            sleep_score = int(60 + 40 * (sleep_h - 6.5))
        elif sleep_h >= 5.0:
            sleep_score = int(20 + 40 * (sleep_h - 5.0) / 1.5)
        elif sleep_h > 0:
            sleep_score = int(sleep_h / 5.0 * 20)
        else:
            sleep_score = 0

        return {
            "ok": True,
            "rings": {
                "recovery": {
                    "score": readiness["score"],
                    "label": readiness["label"],
                    "color": readiness["color"],
                },
                "activity": {
                    "score": min(100, max(0, activity_score)),
                    "label": "Optimal" if 0.8 <= acwr_val <= 1.3 else "Sous-charge" if acwr_val < 0.8 else "Surcharge",
                    "color": "#30d158" if 0.8 <= acwr_val <= 1.3 else "#ff9f0a" if acwr_val < 0.8 else "#ff3b30",
                },
                "sleep": {
                    "score": min(100, max(0, sleep_score)),
                    "label": f"{sleep_h:.1f}h" if sleep_h else "—",
                    "color": "#30d158" if sleep_score >= 80 else "#ff9f0a" if sleep_score >= 50 else "#ff3b30",
                },
            },
        }
    finally:
        conn.close()


@router.get("/weekly-trends")
def weekly_trends(weeks: int = 8) -> dict:
    """Tendances hebdomadaires des métriques santé."""
    conn = get_db()
    try:
        trends = compute_weekly_trends(conn, weeks=weeks)
        return {"ok": True, "trends": trends}
    finally:
        conn.close()


@router.get("/highlights")
def health_highlights() -> dict:
    """Insights intelligents basés sur les données récentes."""
    conn = get_db()
    try:
        metrics = get_health_metrics(conn)
        daily_tss = build_daily_tss(conn)
        acwr = compute_acwr(daily_tss)
        running = analyze_running(conn, weeks=12)
        muscle_cumul = get_cumulative_volume(conn, weeks=4)
        muscle_alerts = analyze_imbalances(muscle_cumul, weeks=4)
        highlights = generate_highlights(conn, metrics, acwr, running, muscle_alerts)
        return {"ok": True, "highlights": highlights}
    finally:
        conn.close()


@router.get("/readiness")
def readiness() -> dict:
    """Retourne le Wakeboard Readiness Score détaillé."""
    conn = get_db()
    try:
        metrics = get_health_metrics(conn)
        daily_tss = build_daily_tss(conn)
        acwr = compute_acwr(daily_tss)
        freshness = {
            "hrv": metrics.get("hrv_freshness", 0),
            "sleep": metrics.get("sleep_freshness", 0),
            "rhr": metrics.get("rhr_freshness", 0),
            "body_battery": metrics.get("body_battery_freshness", 0),
        }
        score = compute_wakeboard_score(
            hrv_val=metrics.get("hrv"),
            hrv_baseline=metrics.get("hrv_baseline"),
            sleep_h=metrics.get("sleep_h"),
            acwr_val=acwr.get("acwr", 0),
            rhr_val=metrics.get("rhr"),
            rhr_baseline=metrics.get("rhr_baseline"),
            body_battery=metrics.get("body_battery"),
            freshness=freshness,
        )
        return {"ok": True, "readiness": score}
    finally:
        conn.close()
