"""
Insights API router — ambient AI alerts and notifications.
Adapted from MediaFlowAI insights system.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class MarkReadRequest(BaseModel):
    id: Optional[str] = None  # null = mark all


@router.get("/insights")
async def get_insights(
    limit: int = Query(20, le=100),
    type: Optional[str] = None,
    severity: Optional[str] = None,
    unread_only: bool = False,
):
    """List insights/alerts."""
    import duckdb
    from src.data.market_schema import get_db_path

    try:
        with duckdb.connect(get_db_path(), read_only=True) as con:
            sql = "SELECT * FROM insights WHERE dismissed = false"
            params = []
            if type:
                sql += " AND type = ?"
                params.append(type)
            if severity:
                sql += " AND severity = ?"
                params.append(severity)
            if unread_only:
                sql += " AND read = false"
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            return con.execute(sql, params).fetchdf().to_dict(orient="records")
    except Exception as e:
        logger.warning(f"Insights fetch failed: {e}")
        return []


@router.get("/insights/count")
async def get_insights_count():
    """Unread insight count for notification bell."""
    import duckdb
    from src.data.market_schema import get_db_path

    try:
        with duckdb.connect(get_db_path(), read_only=True) as con:
            count = con.execute(
                "SELECT count(*) FROM insights WHERE read = false AND dismissed = false"
            ).fetchone()[0]
        return {"unread": count}
    except Exception:
        return {"unread": 0}


@router.post("/insights/mark-read")
async def mark_read(body: MarkReadRequest):
    """Mark insight(s) as read."""
    import duckdb
    from src.data.market_schema import get_db_path

    try:
        with duckdb.connect(get_db_path()) as con:
            if body.id:
                con.execute("UPDATE insights SET read = true WHERE id = ?", [body.id])
            else:
                con.execute("UPDATE insights SET read = true")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Mark-read failed: {e}")
        return {"status": "error", "detail": str(e)}


@router.post("/insights/dismiss/{insight_id}")
async def dismiss_insight(insight_id: str):
    """Dismiss an insight."""
    import duckdb
    from src.data.market_schema import get_db_path

    try:
        with duckdb.connect(get_db_path()) as con:
            con.execute("UPDATE insights SET dismissed = true WHERE id = ?", [insight_id])
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Dismiss insight failed: {e}")
        return {"status": "error", "detail": str(e)}


@router.post("/insights/generate")
async def force_generate():
    """Force regeneration of insights (for demo/testing)."""
    try:
        from src.api.insights import generate_insights
        count = generate_insights()
        return {"status": "ok", "generated": count}
    except Exception as e:
        logger.error(f"Insight generation failed: {e}")
        return {"status": "error", "generated": 0, "detail": str(e)}
