"""Routes activités récentes."""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import get_db

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("/recent")
def recent_activities(limit: int = 10) -> dict:
    """Dernières activités sportives."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT
                id, source, type, name, started_at,
                duration_s, distance_m, calories,
                avg_hr, max_hr, avg_pace_mpm, tss_proxy
            FROM activities
            WHERE started_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        activities = []
        for r in rows:
            duration_s = r[5] or 0
            distance_m = r[6] or 0
            activities.append({
                "id": r[0],
                "source": r[1],
                "type": r[2],
                "name": r[3],
                "started_at": r[4],
                "duration_s": duration_s,
                "duration_str": f"{duration_s // 3600}h{(duration_s % 3600) // 60:02d}",
                "distance_m": distance_m,
                "distance_km": round(distance_m / 1000, 1) if distance_m else None,
                "calories": r[7],
                "avg_hr": r[8],
                "max_hr": r[9],
                "avg_pace_mpm": r[10],
                "tss": round(r[11], 1) if r[11] else None,
            })

        return {"ok": True, "activities": activities}
    finally:
        conn.close()


@router.get("/weekly-hours")
def weekly_hours(weeks: int = 12) -> dict:
    """Heures d'entraînement par semaine (série temporelle)."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT
                strftime('%Y-W%W', started_at) AS week,
                ROUND(SUM(COALESCE(duration_s, 0)) / 3600.0, 2) AS hours
            FROM activities
            WHERE started_at IS NOT NULL
            GROUP BY week
            ORDER BY week DESC
            LIMIT ?
            """,
            (weeks,),
        ).fetchall()

        series = [{"week": r[0], "hours": r[1]} for r in reversed(rows)]
        return {"ok": True, "series": series}
    finally:
        conn.close()
