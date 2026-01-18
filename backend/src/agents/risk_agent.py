"""
Risk Assessment Agent.

Evaluates market volatility using REAL historical price data.
"""

import logging
from typing import Any, Dict

import numpy as np

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed. Risk agent will use simplified volatility.")


class RiskAgent:
    """
    Assesses trading risk using real volatility calculations.
    """

    def analyze(self, ticker: str, technical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze risk profile using real market data.

        Args:
            ticker: Stock symbol
            technical_data: Output from TechnicalAgent (contains price/indicators)

        Returns:
            Dict with risk_level, risk_score, volatility, position sizing
        """
        # Calculate real volatility from price data
        volatility = self._calculate_volatility(ticker)
        
        # Extract RSI for additional risk assessment
        indicators = technical_data.get("indicators", {})
        rsi = indicators.get("rsi", 50.0)
        
        # Adjust volatility based on RSI extremes (market stress indicator)
        if rsi > 75 or rsi < 25:
            volatility *= 1.3  # Increase risk in extreme RSI zones
            
        # Determine Risk Level based on annualized volatility
        annualized_vol = volatility * np.sqrt(252)
        
        if annualized_vol > 0.5:  # > 50% annualized volatility
            risk_level = "HIGH"
        elif annualized_vol > 0.25:  # > 25% annualized volatility
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        # Normalized risk score (0.0 to 1.0) for UI
        # Map volatility to score (cap at 1.0 for very high vol)
        risk_score = min(1.0, annualized_vol / 0.6)
        
        # Position Sizing using simplified Kelly-inspired approach
        # Higher volatility = smaller position
        if risk_level == "LOW":
            position_size = 0.05  # 5% of portfolio
        elif risk_level == "MEDIUM":
            position_size = 0.03  # 3% of portfolio
        else:
            position_size = 0.01  # 1% of portfolio
            
        # Stop loss based on volatility (2 standard deviations)
        stop_loss = volatility * 2
            
        return {
            "risk_level": risk_level,
            "risk_score": round(risk_score, 3),
            "volatility_daily": round(volatility, 4),
            "volatility_annualized": round(annualized_vol, 4),
            "suggested_position_size": position_size,
            "stop_loss_pct": round(stop_loss, 4)
        }
    
    def _calculate_volatility(self, ticker: str) -> float:
        """
        Calculate real historical volatility using yfinance.
        
        Returns daily volatility (standard deviation of log returns).
        """
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not available, using default volatility")
            return 0.02  # Default 2% daily volatility
        
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="3mo", interval="1d")
            
            if hist.empty or len(hist) < 10:
                logger.warning(f"Insufficient data for {ticker}, using default volatility")
                return 0.02
            
            # Calculate log returns
            close_prices = hist["Close"]
            log_returns = np.log(close_prices / close_prices.shift(1)).dropna()
            
            # Standard deviation of log returns = volatility
            volatility = log_returns.std()
            
            logger.info(f"Calculated volatility for {ticker}: {volatility:.4f} (daily)")
            return float(volatility)
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {ticker}: {e}")
            return 0.02  # Fallback
