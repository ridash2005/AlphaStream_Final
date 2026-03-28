"""
NLQ API router — SSE streaming + blocking NLQ endpoints.
Adapted from MediaFlowAI for AlphaStream India.
"""
import json
import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter()


def _safe_json(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if hasattr(obj, "__float__"):
        return float(obj)
    return str(obj)


class NLQRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field("default")
    portfolio_context: Optional[str] = None


class NLQResponse(BaseModel):
    answer: str = ""
    sql: Optional[str] = None
    data: Optional[list] = None
    chart_spec: Optional[dict] = None
    suggested_questions: Optional[list[str]] = None
    sources: Optional[list[str]] = None
    thought_process: str = ""


class NLQStreamRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field("default")
    portfolio_context: Optional[str] = None


@router.post("/nlq", response_model=NLQResponse)
async def nlq(body: NLQRequest):
    """Blocking NLQ endpoint."""
    try:
        from src.agents.nlq.qna_agent import run_qna_agent

        result = await run_qna_agent(
            query=body.question,
            session_id=body.session_id,
            portfolio_context=body.portfolio_context,
        )
        return NLQResponse(
            answer=result.get("narrative", ""),
            sql=result.get("sql"),
            data=result.get("result"),
            chart_spec=result.get("chart_spec"),
            suggested_questions=result.get("suggested_questions"),
            sources=result.get("sources"),
            thought_process=_fmt_steps(result.get("thought_steps", [])),
        )
    except Exception as e:
        return NLQResponse(answer=f"Agent error: {e}", thought_process=str(e))


@router.get("/nlq/stream")
async def nlq_stream_get(
    question: str = Query(..., max_length=2000, min_length=1),
    session_id: str = Query("default"),
):
    """SSE streaming NLQ endpoint (GET)."""
    return _stream_response(question, session_id)


@router.post("/nlq/stream")
async def nlq_stream_post(body: NLQStreamRequest):
    """SSE streaming NLQ endpoint (POST) — supports portfolio context."""
    return _stream_response(body.question, body.session_id, body.portfolio_context)


def _stream_response(question: str, session_id: str, portfolio_context: str = None):
    async def generator():
        try:
            from src.agents.nlq.qna_agent import stream_qna_agent

            async for event in stream_qna_agent(
                query=question,
                session_id=session_id,
                portfolio_context=portfolio_context,
            ):
                yield f"data: {json.dumps(event, default=_safe_json)}\n\n"
        except Exception as e:
            yield f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n'
        finally:
            yield 'data: {"type":"done"}\n\n'

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _fmt_steps(steps: list) -> str:
    if not steps:
        return ""
    return "\n".join(
        f"[{s.get('node','')}] {s.get('action','')} — {s.get('detail','')}"
        for s in steps
    )
