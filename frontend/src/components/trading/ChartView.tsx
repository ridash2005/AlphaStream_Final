import { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { BarChart2, TrendingUp, TrendingDown, Loader2, Clock } from 'lucide-react';
import { apiService } from '@/services/api';
import { useAppStore } from '@/store/appStore';
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

const PERIODS = ['1mo', '3mo', '6mo', '1y', '5y'] as const;

interface Pattern {
  pattern: string;
  direction: string;
  confidence: number;
  explanation: string;
  ticker: string;
}

interface BacktestResult {
  ticker: string;
  pattern: string;
  instances_found: number;
  results: Record<string, { win_rate: number; avg_return: number; max_drawdown: number; sharpe: number; samples: number }>;
}

export function ChartView() {
  const { currentTicker } = useAppStore();
  const [ticker, setTicker] = useState(currentTicker || 'RELIANCE');
  const [period, setPeriod] = useState<string>('6mo');
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [backtest, setBacktest] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);

  const loadChart = async () => {
    setLoading(true);
    try {
      const [ohlcv, pats] = await Promise.all([
        apiService.getOHLCV(ticker, period),
        apiService.getPatterns(ticker),
      ]);
      setPatterns(Array.isArray(pats) ? pats : []);

      // Render TradingView chart
      if (chartContainerRef.current && Array.isArray(ohlcv) && ohlcv.length > 0) {
        if (chartRef.current) {
          chartRef.current.remove();
        }
        const chart = createChart(chartContainerRef.current, {
          layout: { background: { type: ColorType.Solid, color: '#0a0a1a' }, textColor: '#888' },
          grid: { vertLines: { color: '#1a1a2e' }, horzLines: { color: '#1a1a2e' } },
          width: chartContainerRef.current.clientWidth,
          height: 400,
          crosshair: { mode: 0 },
        });
        // lightweight-charts v5 API
        const candlestickSeries = chart.addSeries(CandlestickSeries, {
          upColor: '#00ff88', downColor: '#ff4444',
          borderUpColor: '#00ff88', borderDownColor: '#ff4444',
          wickUpColor: '#00ff88', wickDownColor: '#ff4444',
        });
        candlestickSeries.setData(ohlcv.map((d: any) => ({
          time: typeof d.time === 'number' ? d.time : d.time,
          open: d.open, high: d.high, low: d.low, close: d.close,
        })));

        const volumeSeries = chart.addSeries(HistogramSeries, {
          color: '#4a4a6a', priceFormat: { type: 'volume' },
          priceScaleId: 'volume',
        });
        volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
        volumeSeries.setData(ohlcv.map((d: any) => ({
          time: typeof d.time === 'number' ? d.time : d.time,
          value: d.volume,
          color: d.close >= d.open ? '#00ff8833' : '#ff444433',
        })));

        chart.timeScale().fitContent();
        chartRef.current = chart;
      }

      // Load backtest for first detected pattern
      if (Array.isArray(pats) && pats.length > 0) {
        const bt = await apiService.getBacktest(ticker, pats[0].pattern);
        setBacktest(bt);
      } else {
        setBacktest(null);
      }
    } catch (e) {
      console.error('Chart load failed:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadChart(); }, [ticker, period]);
  useEffect(() => { setTicker(currentTicker || 'RELIANCE'); }, [currentTicker]);

  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); if (chartRef.current) chartRef.current.remove(); };
  }, []);

  return (
    <div className="space-y-4">
      {/* Controls */}
      <Card className="glass-card p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <BarChart2 className="h-5 w-5 text-primary" />
          <Input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && loadChart()}
            className="w-32 font-mono bg-secondary/50"
            placeholder="TICKER"
          />
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <Button key={p} variant={period === p ? 'default' : 'outline'} size="sm"
                className="text-xs h-7 px-2" onClick={() => setPeriod(p)}>
                {p.toUpperCase()}
              </Button>
            ))}
          </div>
          {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Chart */}
        <Card className="glass-card p-4 lg:col-span-2">
          <div ref={chartContainerRef} className="w-full" style={{ minHeight: 400 }} />
        </Card>

        {/* Patterns + Backtest */}
        <div className="space-y-4">
          <Card className="glass-card p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" /> Detected Patterns
            </h3>
            {patterns.length === 0 ? (
              <p className="text-xs text-muted-foreground">No patterns detected on {ticker} currently.</p>
            ) : (
              <div className="space-y-3">
                {patterns.map((p, i) => (
                  <div key={i} className="p-2 rounded-lg bg-secondary/30 border border-border/30">
                    <div className="flex items-center justify-between mb-1">
                      <Badge variant="outline" className={p.direction === 'bullish' ? 'text-emerald-400 border-emerald-500/30' : 'text-red-400 border-red-500/30'}>
                        {p.direction === 'bullish' ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                        {p.pattern.replace(/_/g, ' ')}
                      </Badge>
                      <span className="text-xs font-mono text-muted-foreground">{(p.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{p.explanation}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {backtest && backtest.instances_found > 0 && (
            <Card className="glass-card p-4">
              <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
                <Clock className="h-4 w-4 text-primary" /> Backtest Results
              </h3>
              <p className="text-xs text-muted-foreground mb-2">
                {backtest.pattern.replace(/_/g, ' ')} on {backtest.ticker}: {backtest.instances_found} historical instances
              </p>
              <div className="space-y-2">
                {Object.entries(backtest.results).map(([horizon, stats]) => (
                  <div key={horizon} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{horizon}</span>
                    <div className="flex gap-3">
                      <span className={stats.win_rate >= 0.5 ? 'text-emerald-400' : 'text-red-400'}>
                        Win: {(stats.win_rate * 100).toFixed(0)}%
                      </span>
                      <span className={stats.avg_return >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                        Avg: {stats.avg_return >= 0 ? '+' : ''}{stats.avg_return.toFixed(2)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
