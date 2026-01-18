"""
Chart Comparison Agent - Generates visual price charts.

Creates 7-day price charts with 24-hour highlighting and insider event overlays.
Uses Matplotlib for chart generation, saved as PNG.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

logger = logging.getLogger(__name__)

# Optional yfinance for price data
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed. Chart agent will have limited functionality.")


class ChartAgent:
    """
    Generates comparative price charts for trading analysis.
    
    Creates visual representations of price action with:
    - 7-day price history
    - Last 24 hours highlighted
    - Insider trading event markers
    """
    
    def __init__(self, output_dir: str = "reports/charts"):
        """
        Initialize chart agent.
        
        Args:
            output_dir: Directory to save chart images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set dark theme for charts (matches AlphaStream UI)
        plt.style.use('dark_background')
    
    def generate_comparison_chart(
        self, 
        ticker: str, 
        insider_events: list[dict] = None,
        days: int = 7
    ) -> dict[str, Any]:
        """
        Generate a price comparison chart.
        
        Args:
            ticker: Stock symbol
            insider_events: List of insider transactions to overlay
            days: Days of history to show
            
        Returns:
            Dict with chart path and analysis
        """
        if not YFINANCE_AVAILABLE:
            return self._error_response("yfinance not available")
        
        try:
            # Fetch price data
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period=f"{days}d", interval="1h")
            
            if hist.empty:
                return self._error_response(f"No price data for {ticker}")
            
            # Create the chart
            fig, ax = plt.subplots(figsize=(12, 6), facecolor='#1a1a2e')
            ax.set_facecolor('#1a1a2e')
            
            # Convert index to matplotlib dates
            dates = hist.index
            prices = hist['Close'].values
            
            # Find 24-hour boundary
            now = datetime.now()
            one_day_ago = now - timedelta(days=1)
            
            # Split data into prior week and last 24h
            mask_24h = dates >= one_day_ago
            
            # Plot prior period (dimmed)
            prior_dates = dates[~mask_24h]
            prior_prices = prices[~mask_24h]
            if len(prior_dates) > 0:
                ax.plot(prior_dates, prior_prices, color='#4a4a6a', linewidth=1.5, 
                       label='Prior Period', alpha=0.7)
            
            # Plot last 24 hours (highlighted)
            recent_dates = dates[mask_24h]
            recent_prices = prices[mask_24h]
            if len(recent_dates) > 0:
                ax.plot(recent_dates, recent_prices, color='#00ff88', linewidth=2.5, 
                       label='Last 24 Hours', alpha=1.0)
                
                # Fill area under 24h line
                ax.fill_between(recent_dates, recent_prices, alpha=0.2, color='#00ff88')
            
            # Add insider event markers if provided
            if insider_events:
                for event in insider_events[:5]:  # Limit markers
                    try:
                        event_date = datetime.fromisoformat(event.get('filing_date', ''))
                        if event_date >= dates[0]:
                            # Find closest price
                            idx = (dates - event_date).argmin()
                            price_at_event = prices[idx]
                            
                            # Marker color based on transaction type
                            color = '#00ff88' if 'buy' in str(event.get('transaction_type', '')).lower() else '#ff4444'
                            ax.scatter([event_date], [price_at_event], color=color, s=100, 
                                      marker='^' if color == '#00ff88' else 'v', zorder=5)
                    except:
                        continue
            
            # Styling
            ax.set_title(f'{ticker} - 7 Day Price Action', fontsize=14, color='white', pad=15)
            ax.set_xlabel('Date', fontsize=10, color='#888888')
            ax.set_ylabel('Price ($)', fontsize=10, color='#888888')
            ax.tick_params(colors='#888888')
            ax.grid(True, alpha=0.2, color='#333333')
            ax.legend(loc='upper left', facecolor='#1a1a2e', edgecolor='#333333')
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator())
            plt.xticks(rotation=45)
            
            # Calculate price change
            if len(prices) > 0:
                price_change_7d = ((prices[-1] - prices[0]) / prices[0]) * 100
                
                # 24h change
                if len(recent_prices) > 0 and len(prior_prices) > 0:
                    price_change_24h = ((recent_prices[-1] - prior_prices[-1]) / prior_prices[-1]) * 100
                else:
                    price_change_24h = 0
            else:
                price_change_7d = 0
                price_change_24h = 0
            
            # Save chart
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            chart_filename = f"{ticker}_{timestamp}.png"
            chart_path = self.output_dir / chart_filename
            
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
            plt.close()
            
            logger.info(f"Chart saved: {chart_path}")
            
            return {
                "chart_path": str(chart_path),
                "ticker": ticker,
                "current_price": float(prices[-1]) if len(prices) > 0 else 0,
                "price_change_7d_pct": round(price_change_7d, 2),
                "price_change_24h_pct": round(price_change_24h, 2),
                "data_points": len(prices),
                "insider_events_marked": len(insider_events) if insider_events else 0
            }
            
        except Exception as e:
            logger.error(f"Chart generation error for {ticker}: {e}")
            return self._error_response(str(e))
    
    def _error_response(self, reason: str) -> dict[str, Any]:
        """Return error response."""
        return {
            "chart_path": None,
            "error": reason,
            "ticker": "N/A",
            "current_price": 0,
            "price_change_7d_pct": 0,
            "price_change_24h_pct": 0
        }
