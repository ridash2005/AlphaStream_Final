"""
Signal/Alert MCP Server — threshold checking and alert dispatch.
Replaces MediaFlowAI's alert_server for financial domain.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

import yaml
import duckdb
from fastmcp import FastMCP

DB_PATH = str(pathlib.Path(__file__).parents[3] / "market_analytics.duckdb")
CLIENT_YAML = pathlib.Path(__file__).parents[4] / "config" / "clients" / "DEFAULT.yaml"

mcp = FastMCP("signal_server")
_conn = None


def _db():
    global _conn
    if _conn is None:
        _conn = duckdb.connect(DB_PATH, read_only=True)
    return _conn


def _client_config() -> dict:
    with open(CLIENT_YAML) as f:
        return yaml.safe_load(f)


@mcp.tool()
def check_thresholds() -> list[dict]:
    """Evaluate signal thresholds against live data. Returns alerts."""
    cfg = _client_config()
    thresholds = cfg.get("thresholds", {})
    alerts = []

    # High alpha score signals
    alpha_threshold = thresholds.get("alpha_score_high", 80)
    rows = _db().execute("""
        SELECT s.ticker, d.company_name, s.signal_type, s.direction,
               s.alpha_score, s.confidence
        FROM fact_signals s
        JOIN dim_stocks d ON s.ticker = d.ticker
        WHERE s.alpha_score >= ?
          AND s.signal_date >= current_date - INTERVAL '3 days'
        ORDER BY s.alpha_score DESC LIMIT 5
    """, [alpha_threshold]).fetchall()
    for ticker, name, sig_type, direction, score, conf in rows:
        alerts.append({
            "type": "ALPHA_SCORE", "ticker": ticker, "company": name,
            "value": score, "threshold": alpha_threshold,
            "status": "ALERT",
            "message": f"{name} ({ticker}) Alpha Score {score:.1f} — {direction} {sig_type} signal (confidence {conf:.0f}%)"
        })

    # FII streak detection
    fii_streak_days = thresholds.get("fii_streak_days", 5)
    fii_rows = _db().execute("""
        SELECT COUNT(*) AS streak
        FROM (
            SELECT date, fii_net_cr,
                   ROW_NUMBER() OVER (ORDER BY date DESC) AS rn
            FROM fact_fii_dii_flows
            WHERE fii_net_cr > 0
            ORDER BY date DESC
        )
        WHERE rn <= 10
    """).fetchone()
    if fii_rows and fii_rows[0] >= fii_streak_days:
        alerts.append({
            "type": "FII_STREAK", "ticker": "MARKET",
            "value": fii_rows[0], "threshold": fii_streak_days,
            "status": "ALERT",
            "message": f"FII net buying streak: {fii_rows[0]} consecutive sessions"
        })

    return alerts if alerts else [{"status": "OK", "message": "All thresholds within bounds"}]


@mcp.tool()
def fire_alert(alert: dict) -> dict:
    """Dispatch alert via configured channels (Slack webhook)."""
    cfg = _client_config()
    channels_fired = []
    msg = alert.get("message", str(alert))

    slack = cfg.get("alert_channels", {}).get("slack_webhook", "")
    if slack:
        try:
            import urllib.request
            import json
            payload = json.dumps({"text": f"[AlphaStream Alert] {msg}"}).encode()
            req = urllib.request.Request(slack, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
            channels_fired.append("slack")
        except Exception as e:
            channels_fired.append(f"slack:error:{e}")

    return {"dispatched": bool(channels_fired), "channels": channels_fired, "message": msg}


if __name__ == "__main__":
    mcp.run()
