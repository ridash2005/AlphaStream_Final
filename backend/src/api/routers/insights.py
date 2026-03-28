"""
Insights API router — ambient AI alerts and notifications.
Adapted from MediaFlowAI insights system.
"""
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

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

    con = duckdb.connect(get_db_path(), read_only=True)
    try:
        sql = "SELECT * FROM insights WHERE dismissed = false"
        if type:
            sql += f" AND type = '{type}'"
        if severity:
            sql += f" AND severity = '{severity}'"
        if unread_only:
            sql += " AND read = false"
        sql += f" ORDER BY created_at DESC LIMIT {limit}"

        return con.execute(sql).fetchdf().to_dict(orient="records")
    except Exception:
        return []
    finally:
        con.close()


@router.get("/insights/count")
async def get_insights_count():
    """Unread insight count for notification bell."""
    import duckdb
    from src.data.market_schema import get_db_path

    con = duckdb.connect(get_db_path(), read_only=True)
    try:
        count = con.execute(
            "SELECT count(*) FROM insights WHERE read = false AND dismissed = false"
        ).fetchone()[0]
        return {"unread": count}
    except Exception:
        return {"unread": 0}
    finally:
        con.close()


@router.post("/insights/mark-read")
async def mark_read(body: MarkReadRequest):
    """Mark insight(s) as read."""
    import duckdb
    from src.data.market_schema import get_db_path

    con = duckdb.connect(get_db_path())
    try:
        if body.id:
            con.execute("UPDATE insights SET read = true WHERE id = ?", [body.id])
        else:
            con.execute("UPDATE insights SET read = true")
        return {"status": "ok"}
    finally:
        con.close()


@router.post("/insights/dismiss/{insight_id}")
async def dismiss_insight(insight_id: str):
    """Dismiss an insight."""
    import duckdb
    from src.data.market_schema import get_db_path

    con = duckdb.connect(get_db_path())
    try:
        con.execute("UPDATE insights SET dismissed = true WHERE id = ?", [insight_id])
        return {"status": "ok"}
    finally:
        con.close()


@router.post("/insights/generate")
async def force_generate():
    """Force regeneration of insights (for demo/testing)."""
    from src.api.insights import generate_insights
    count = generate_insights()
    return {"status": "ok", "generated": count}
