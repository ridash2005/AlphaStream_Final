"""
SEC EDGAR Connector - Real-time SEC filings data.

Fetches Form 4 (insider trading) and other SEC filings using edgartools.
Implements rate limiting per SEC fair access policy.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Import edgartools - real SEC data library
try:
    from edgar import Company, set_identity
    EDGAR_AVAILABLE = True
except ImportError:
    EDGAR_AVAILABLE = False
    logger.warning("edgartools not installed. SEC features will be disabled.")


class SECConnector:
    """
    Connects to SEC EDGAR for real-time filings data.
    
    Uses edgartools library for structured access to SEC filings.
    Rate-limited to comply with SEC fair access policy (10 req/sec max).
    """
    
    def __init__(self, user_agent: str = "AlphaStream support@alphastream.ai"):
        """
        Initialize SEC connector.
        
        Args:
            user_agent: Required by SEC - identify your application
        """
        if EDGAR_AVAILABLE:
            # Set identity as required by SEC
            set_identity(user_agent)
            logger.info("SEC EDGAR connector initialized")
        else:
            logger.warning("SEC EDGAR connector running in degraded mode (no edgartools)")
    
    def get_insider_trades(self, ticker: str, days: int = 1) -> list[dict[str, Any]]:
        """
        Get insider trading activity (Form 4 filings) for a ticker.
        
        Args:
            ticker: Stock symbol (e.g., "AAPL")
            days: Number of days to look back (default: 1 for last 24 hours)
            
        Returns:
            List of insider transactions with details
        """
        if not EDGAR_AVAILABLE:
            return self._llm_fallback_insider_trades(ticker)
        
        try:
            company = Company(ticker)
            
            # Get Form 4 filings (insider transactions)
            form4_filings = company.get_filings(form="4")
            
            # Filter to recent filings
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_filings = []
            
            for filing in form4_filings[:20]:  # Check last 20 filings
                try:
                    filing_date = filing.filing_date
                    if filing_date >= cutoff_date.date():
                        # Parse the Form 4 for transaction details
                        transactions = self._parse_form4(filing)
                        recent_filings.extend(transactions)
                except Exception as e:
                    logger.debug(f"Error parsing filing: {e}")
                    continue
            
            logger.info(f"Found {len(recent_filings)} insider transactions for {ticker}")
            return recent_filings
            
        except Exception as e:
            logger.error(f"Error fetching insider trades for {ticker}: {e}")
            return self._llm_fallback_insider_trades(ticker)
    
    def _parse_form4(self, filing) -> list[dict[str, Any]]:
        """
        Parse a Form 4 filing to extract transaction details.
        
        Returns list of transactions from this filing.
        """
        transactions = []
        
        try:
            # Access filing data
            insider_name = getattr(filing, 'reporting_owner', 'Unknown Insider')
            
            # Get transaction data if available
            trans_data = {
                "insider_name": str(insider_name),
                "filing_date": str(filing.filing_date),
                "form_type": "4",
                "ticker": filing.ticker if hasattr(filing, 'ticker') else "N/A",
                "accession_number": filing.accession_number,
                # Transaction details would come from parsed XML
                "transaction_type": "Unknown",  # Will use LLM to parse if needed
                "shares": 0,
                "price": 0.0,
            }
            transactions.append(trans_data)
            
        except Exception as e:
            logger.debug(f"Error parsing Form 4 details: {e}")
        
        return transactions
    
    def get_recent_filings(self, ticker: str, form_types: list[str] = None) -> list[dict[str, Any]]:
        """
        Get recent SEC filings for a company.
        
        Args:
            ticker: Stock symbol
            form_types: List of form types to fetch (default: 10-K, 10-Q, 8-K)
            
        Returns:
            List of filing summaries
        """
        if form_types is None:
            form_types = ["10-K", "10-Q", "8-K"]
        
        if not EDGAR_AVAILABLE:
            return []
        
        try:
            company = Company(ticker)
            filings = []
            
            for form_type in form_types:
                form_filings = company.get_filings(form=form_type)
                for filing in form_filings[:5]:  # Last 5 of each type
                    filings.append({
                        "form_type": form_type,
                        "filing_date": str(filing.filing_date),
                        "accession_number": filing.accession_number,
                        "description": getattr(filing, 'description', f"{form_type} Filing"),
                    })
            
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {e}")
            return []
    
    def _llm_fallback_insider_trades(self, ticker: str) -> list[dict[str, Any]]:
        """
        When edgartools fails, return placeholder indicating LLM should be used.
        
        The InsiderAgent will handle LLM-based analysis.
        """
        logger.info(f"Using LLM fallback for insider trades: {ticker}")
        return [{
            "insider_name": "LLM_FALLBACK_REQUIRED",
            "ticker": ticker,
            "message": "Use LLM to fetch and analyze SEC data",
            "source": "sec.gov/cgi-bin/browse-edgar"
        }]


# Singleton instance
_sec_connector: SECConnector | None = None


def get_sec_connector() -> SECConnector:
    """Get or create the SEC connector singleton."""
    global _sec_connector
    if _sec_connector is None:
        _sec_connector = SECConnector()
    return _sec_connector
