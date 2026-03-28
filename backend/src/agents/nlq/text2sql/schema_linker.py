"""
Schema Linker — maps NL entities to financial database columns.
Adapted from MediaFlowAI for Indian stock market analytics.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from src.agents.nlq.llm_provider import complete, get_llm

_SCHEMA_CONTEXT = """
DuckDB tables for Indian stock market analytics:

TABLE: dim_stocks
  ticker (VARCHAR PK), company_name (VARCHAR), sector (VARCHAR),
  industry (VARCHAR), isin (VARCHAR), market_cap_cr (DOUBLE),
  index_membership (VARCHAR[])  -- e.g. ['nifty50']

TABLE: fact_daily_prices
  ticker (VARCHAR), date (DATE), open (DOUBLE), high (DOUBLE),
  low (DOUBLE), close (DOUBLE), volume (BIGINT), adj_close (DOUBLE)
  PRIMARY KEY (ticker, date)

TABLE: fact_signals
  signal_id (VARCHAR PK), ticker (VARCHAR), signal_date (DATE),
  signal_type (VARCHAR), direction (VARCHAR), confidence (DOUBLE),
  alpha_score (DOUBLE), evidence_json (JSON), backtest_json (JSON),
  created_at (TIMESTAMP)

TABLE: fact_insider_trades
  id (VARCHAR PK), ticker (VARCHAR), person_name (VARCHAR),
  person_category (VARCHAR), trade_type (VARCHAR),
  quantity (BIGINT), value_lakhs (DOUBLE), trade_date (DATE), source (VARCHAR)

TABLE: fact_fii_dii_flows
  date (DATE PK), fii_buy_cr (DOUBLE), fii_sell_cr (DOUBLE),
  fii_net_cr (DOUBLE), dii_buy_cr (DOUBLE), dii_sell_cr (DOUBLE),
  dii_net_cr (DOUBLE)

TABLE: fact_filings
  filing_id (VARCHAR PK), ticker (VARCHAR), filing_date (TIMESTAMP),
  filing_type (VARCHAR), subject (TEXT), materiality (VARCHAR),
  sentiment (VARCHAR), key_facts (JSON), source_url (VARCHAR)

TABLE: fact_quarterly_results
  ticker (VARCHAR), quarter (VARCHAR), revenue_cr (DOUBLE),
  pat_cr (DOUBLE), ebitda_margin (DOUBLE), yoy_revenue_growth (DOUBLE),
  yoy_pat_growth (DOUBLE)
  PRIMARY KEY (ticker, quarter)

PRE-BUILT VIEWS:
  v_signal_summary — signals joined with stock info, ordered by alpha_score
  v_insider_activity_30d — insider trades last 30 days with stock info
  v_fii_dii_trend — FII/DII flows with 5d/20d rolling sums
  v_sector_heatmap — sector-wise signal counts and avg alpha scores
  v_stock_screener — latest price + latest signal per stock

Dimension values:
- sector: Financial Services, Information Technology, Energy, Automobile, Healthcare, Fast Moving Consumer Goods, Materials, Industrials, Consumer Durables, Utilities, Construction Materials, Communication Services
- signal_type: technical, filing, insider, flow, sentiment
- direction: bullish, bearish, neutral
- trade_type: buy, sell
- person_category: promoter, director, kmp
- filing_type: board_meeting, acquisition, debt, expansion, regulatory, routine
- materiality: high, medium, low
- index_membership values: nifty50, nifty100, nifty500

DuckDB rules:
- Date comparisons: use current_date, INTERVAL syntax
- Array contains: 'nifty50' = ANY(index_membership)
- JSON access: evidence_json->>'pattern'
"""


class SchemaLink(BaseModel):
    columns: dict[str, str] = Field(default_factory=dict)
    filter_values: dict[str, str] = Field(default_factory=dict)
    requires_date_filter: bool = False
    time_window_hint: str = ""


def link_schema(question: str) -> SchemaLink:
    """Returns SchemaLink for columns relevant to the question."""
    try:
        llm = get_llm(temperature=0.0).with_structured_output(SchemaLink)
        prompt = (
            f"You are a schema linking agent for a DuckDB financial analytics database.\n\n"
            f"Schema:\n{_SCHEMA_CONTEXT}\n\n"
            f"Question: {question}\n\n"
            "Identify which tables and columns are relevant. "
            "For filter_values, extract specific values mentioned "
            "(e.g., 'Financial Services' for sector, 'RELIANCE' for ticker). "
            "Set requires_date_filter=true if the question involves time/dates. "
            "Set time_window_hint to any time period mentioned."
        )
        return llm.invoke(prompt)
    except Exception:
        pass

    # Fallback: text completion
    try:
        prompt = (
            f"Schema:\n{_SCHEMA_CONTEXT}\n\n"
            f"Question: {question}\n\n"
            "List relevant columns, one per line as: column_name: reason"
        )
        text = complete(prompt, max_tokens=512)
        columns = {}
        for line in text.strip().splitlines():
            if ":" in line:
                col, _, reason = line.partition(":")
                col = col.strip()
                if col and not col.startswith("#"):
                    columns[col] = reason.strip()
        return SchemaLink(columns=columns)
    except Exception:
        return SchemaLink()


def get_schema_context() -> str:
    return _SCHEMA_CONTEXT
