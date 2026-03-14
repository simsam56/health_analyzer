"""Routes entraînement (PMC, ACWR, running)."""

from __future__ import annotations

from fastapi import APIRouter

from analytics.training_load import (
    analyze_running,
    build_daily_tss,
    compute_acwr,
    compute_pmc,
)
from api.deps import get_db

router = APIRouter(prefix="/api/training", tags=["training"])


@router.get("/pmc")
def pmc_data() -> dict:
    """Performance Management Chart : CTL, ATL, TSB."""
    conn = get_db()
    try:
        daily_tss = build_daily_tss(conn)
        pmc = compute_pmc(daily_tss)
        # Dernière entrée = état actuel
        current = pmc[-1] if pmc else {}
        # Série temporelle (limiter aux 6 derniers mois pour le graphe)
        series = pmc[-180:] if len(pmc) > 180 else pmc
        return {
            "ok": True,
            "current": {
                "ctl": current.get("ctl", 0),
                "atl": current.get("atl", 0),
                "tsb": current.get("tsb", 0),
                "tss": current.get("tss", 0),
                "date": current.get("date", ""),
            },
            "series": [
                {
                    "date": d.get("date", ""),
                    "ctl": round(d.get("ctl", 0), 1),
                    "atl": round(d.get("atl", 0), 1),
                    "tsb": round(d.get("tsb", 0), 1),
                }
                for d in series
            ],
        }
    finally:
        conn.close()


@router.get("/acwr")
def acwr_data() -> dict:
    """Acute:Chronic Workload Ratio."""
    conn = get_db()
    try:
        daily_tss = build_daily_tss(conn)
        data = compute_acwr(daily_tss)
        return {"ok": True, "acwr": data}
    finally:
        conn.close()


@router.get("/running")
def running_analysis(weeks: int = 12) -> dict:
    """Analyse running : allure, prédictions Riegel, volume."""
    conn = get_db()
    try:
        data = analyze_running(conn, weeks=weeks)
        return {"ok": True, "running": data}
    finally:
        conn.close()
