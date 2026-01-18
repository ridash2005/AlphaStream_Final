"""
Report Generation Agent - Creates comprehensive PDF reports.

Combines all agent outputs into a professional PDF report with:
- Trading recommendation summary
- Price charts
- Insider trading activity
- Technical and risk analysis
- Sources and citations
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)


class ReportAgent:
    """
    Generates comprehensive PDF trading reports.
    
    Combines outputs from all agents into a professional document.
    """
    
    def __init__(self, output_dir: str = "reports"):
        """
        Initialize report agent.
        
        Args:
            output_dir: Directory to save PDF reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Custom styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#00ff88')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#8b5cf6')
        ))
        
        # Use unique name to avoid conflict with built-in 'BodyText'
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            textColor=colors.HexColor('#333333')
        ))
        
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['Normal'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=10,
            textColor=colors.HexColor('#00ff88')
        ))
    
    def generate_report(
        self,
        ticker: str,
        recommendation: dict[str, Any],
        insider_data: dict[str, Any] = None,
        chart_data: dict[str, Any] = None,
        technical_data: dict[str, Any] = None,
        risk_data: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Generate a comprehensive PDF report.
        
        Args:
            ticker: Stock symbol
            recommendation: Main recommendation from DecisionAgent
            insider_data: Insider trading analysis from InsiderAgent
            chart_data: Chart info from ChartAgent
            technical_data: Technical analysis from TechnicalAgent
            risk_data: Risk assessment from RiskAgent
            
        Returns:
            Dict with report path and metadata
        """
        try:
            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"{ticker}_report_{timestamp}.pdf"
            report_path = self.output_dir / report_filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(report_path),
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )
            
            # Build content
            story = []
            
            # Title
            story.append(Paragraph(
                f"AlphaStream Trading Report",
                self.styles['ReportTitle']
            ))
            story.append(Paragraph(
                f"<b>{ticker}</b> - {datetime.now().strftime('%B %d, %Y %H:%M')}",
                self.styles['ReportBody']
            ))
            story.append(Spacer(1, 20))
            
            # Recommendation Summary
            story.append(HRFlowable(width="100%", color=colors.HexColor('#8b5cf6')))
            story.append(Spacer(1, 10))
            
            rec_text = recommendation.get('recommendation', 'HOLD')
            confidence = recommendation.get('confidence', 0)
            rec_color = '#00ff88' if rec_text == 'BUY' else '#ff4444' if rec_text == 'SELL' else '#ffaa00'
            
            story.append(Paragraph(
                f"<font color='{rec_color}'><b>{rec_text}</b></font>",
                self.styles['Recommendation']
            ))
            story.append(Paragraph(
                f"Confidence: {confidence:.1f}%",
                ParagraphStyle('Centered', alignment=TA_CENTER, fontSize=12)
            ))
            story.append(Spacer(1, 20))
            
            # Key Factors
            story.append(Paragraph("Key Factors", self.styles['SectionHeader']))
            key_factors = recommendation.get('key_factors', [])
            for factor in key_factors[:5]:
                story.append(Paragraph(f"• {factor}", self.styles['ReportBody']))
            story.append(Spacer(1, 15))
            
            # Chart (if available)
            if chart_data and chart_data.get('chart_path'):
                chart_path = chart_data['chart_path']
                if os.path.exists(chart_path):
                    story.append(Paragraph("Price Chart (7-Day)", self.styles['SectionHeader']))
                    story.append(Image(chart_path, width=6*inch, height=3*inch))
                    story.append(Paragraph(
                        f"24h Change: {chart_data.get('price_change_24h_pct', 0):.2f}% | "
                        f"7d Change: {chart_data.get('price_change_7d_pct', 0):.2f}%",
                        self.styles['ReportBody']
                    ))
                    story.append(Spacer(1, 15))
            
            # Insider Activity
            if insider_data:
                story.append(Paragraph("Insider Trading Activity", self.styles['SectionHeader']))
                
                insider_score = insider_data.get('insider_score', 0)
                insider_sentiment = insider_data.get('sentiment', 'NEUTRAL')
                
                # Create insider summary table
                insider_table_data = [
                    ['Metric', 'Value'],
                    ['Insider Sentiment', insider_sentiment],
                    ['Insider Score', f"{insider_score:.2f}"],
                    ['Total Buy Value', f"${insider_data.get('total_buy_value', 0):,.0f}"],
                    ['Total Sell Value', f"${insider_data.get('total_sell_value', 0):,.0f}"],
                ]
                
                table = Table(insider_table_data, colWidths=[2*inch, 3*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(table)
                story.append(Spacer(1, 10))
                
                # Key transactions
                transactions = insider_data.get('key_transactions', [])
                for trans in transactions[:3]:
                    story.append(Paragraph(f"• {trans}", self.styles['ReportBody']))
                story.append(Spacer(1, 15))
            
            # Technical Analysis
            if technical_data:
                story.append(Paragraph("Technical Analysis", self.styles['SectionHeader']))
                
                tech_table_data = [
                    ['Indicator', 'Value', 'Signal'],
                    ['RSI', f"{technical_data.get('indicators', {}).get('rsi', 0):.1f}", 
                     'Oversold' if technical_data.get('indicators', {}).get('rsi', 50) < 30 else 
                     'Overbought' if technical_data.get('indicators', {}).get('rsi', 50) > 70 else 'Neutral'],
                    ['Technical Score', f"{technical_data.get('technical_score', 0):.2f}", 
                     technical_data.get('signal', 'HOLD')],
                ]
                
                table = Table(tech_table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(table)
                story.append(Spacer(1, 15))
            
            # Risk Assessment
            if risk_data:
                story.append(Paragraph("Risk Assessment", self.styles['SectionHeader']))
                story.append(Paragraph(
                    f"Risk Level: <b>{risk_data.get('risk_level', 'MEDIUM')}</b> | "
                    f"Suggested Position Size: {risk_data.get('suggested_position_size', 0.03)*100:.1f}%",
                    self.styles['ReportBody']
                ))
                story.append(Spacer(1, 15))
            
            # Sources
            story.append(Paragraph("Data Sources", self.styles['SectionHeader']))
            sources = recommendation.get('sources', [])
            for source in set(sources):
                story.append(Paragraph(f"• {source}", self.styles['ReportBody']))
            
            # Footer
            story.append(Spacer(1, 30))
            story.append(HRFlowable(width="100%", color=colors.grey))
            story.append(Paragraph(
                f"Generated by AlphaStream | Powered by Pathway Streaming Engine",
                ParagraphStyle('Footer', alignment=TA_CENTER, fontSize=8, textColor=colors.grey)
            ))
            story.append(Paragraph(
                f"This report is for informational purposes only. Not financial advice.",
                ParagraphStyle('Disclaimer', alignment=TA_CENTER, fontSize=7, textColor=colors.grey)
            ))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Report generated: {report_path}")
            
            return {
                "report_path": str(report_path),
                "ticker": ticker,
                "generated_at": datetime.now().isoformat(),
                "recommendation": rec_text,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return {
                "report_path": None,
                "error": str(e),
                "ticker": ticker
            }
