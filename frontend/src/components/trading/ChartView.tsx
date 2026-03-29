import { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { BarChart2, TrendingUp, TrendingDown, Loader2, Clock, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import { useAppStore } from '@/store/appStore';
import { createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts';

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
  const [error, setError] = useState<string | null>(null);
  const [noData, setNoData] = useState(false);
  const [showIndicators, setShowIndicators] = useState(false);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const rsiContainerRef = useRef<HTMLDivElement>(null);
  const rsiChartRef = useRef<any>(null);

  const loadChart = async () => {
    setError(null);
    setNoData(false);
    setLoading(true);
    try {
      const [data, pats] = await Promise.all([
        apiService.getOHLCV(ticker, period, showIndicators),
        apiService.getPatterns(ticker),
      ]);
      setPatterns(Array.isArray(pats) ? pats : []);

      // Detect extended vs flat response format
      const isExtended = data && data.candles && Array.isArray(data.candles);
      const ohlcv: any[] = isExtended ? data.candles : (Array.isArray(data) ? data : []);

      // Dispose previous RSI chart
      if (rsiChartRef.current) {
        rsiChartRef.current.remove();
        rsiChartRef.current = null;
      }

      // Render TradingView chart
      if (ohlcv.length === 0) {
        setNoData(true);
      }
      if (chartContainerRef.current && ohlcv.length > 0) {
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

        // Indicator overlays
        if (isExtended && showIndicators) {
          const sma20Series = chart.addSeries(LineSeries, {
            color: '#06b6d4', lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: 'SMA20',
          });
          sma20Series.setData(data.sma20 || []);

          const sma50Series = chart.addSeries(LineSeries, {
            color: '#f59e0b', lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: 'SMA50',
          });
          sma50Series.setData(data.sma50 || []);

          // RSI sub-chart
          if (rsiContainerRef.current) {
            const rsiChart = createChart(rsiContainerRef.current, {
              height: 100,
              layout: { background: { type: ColorType.Solid, color: '#0a0a1a' }, textColor: '#888' },
              grid: { vertLines: { color: '#1a1a2e' }, horzLines: { color: '#1a1a2e' } },
              rightPriceScale: { scaleMargins: { top: 0.1, bottom: 0.1 } },
              timeScale: { visible: false },
              width: rsiContainerRef.current.clientWidth,
            });
            const rsiSeries = rsiChart.addSeries(LineSeries, {
              color: '#a855f7', lineWidth: 1, lastValueVisible: true, title: 'RSI',
            });
            rsiSeries.setData(data.rsi || []);
            rsiSeries.createPriceLine({ price: 30, color: '#ef4444', lineWidth: 1, lineStyle: 2, title: '30' });
            rsiSeries.createPriceLine({ price: 70, color: '#22c55e', lineWidth: 1, lineStyle: 2, title: '70' });

            // Sync time scales
            chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
              if (range) rsiChart.timeScale().setVisibleLogicalRange(range);
            });

            rsiChartRef.current = rsiChart;
          }
        }

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
      setError('Failed to load chart data. The backend may be unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadChart(); }, [ticker, period, showIndicators]);
  useEffect(() => { setError(null); setTicker(currentTicker || 'RELIANCE'); }, [currentTicker]);

  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) chartRef.current.remove();
      if (rsiChartRef.current) rsiChartRef.current.remove();
    };
  }, []);

  return (
    <div className="space-y-3">
      {/* Controls */}
      <Card className="glass-card p-3">
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
          <button
            onClick={() => setShowIndicators((v) => !v)}
            className={cn(
              'px-2 py-1 rounded text-xs',
              showIndicators ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Activity className="h-3 w-3 inline mr-1" />Indicators
          </button>
          {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        </div>
      </Card>

      {/* Chart — full width */}
      <Card className="glass-card p-4 w-full">
        {loading && (
          <div className="flex items-center justify-center h-[480px]">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}
        {!loading && error && (
          <div className="flex flex-col items-center justify-center h-[480px] text-slate-400 gap-2">
            <span className="text-sm">{error}</span>
            <button
              onClick={() => loadChart()}
              className="text-xs text-cyan-400 hover:text-cyan-300 underline"
            >
              Retry
            </button>
          </div>
        )}
        {!loading && !error && (
          <>
            {/* chartContainerRef stays mounted so lightweight-charts can attach;
                the "no data" overlay sits on top when ohlcv is empty */}
            <div className="relative">
              <div ref={chartContainerRef} className="w-full" style={{ height: 480 }} />
              {/* Overlay shown when ohlcv was empty */}
              {noData && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <BarChart2 className="h-10 w-10 opacity-20" />
                  <p className="text-sm">No OHLCV data for <span className="font-mono font-semibold">{ticker}</span></p>
                  <p className="text-xs opacity-60">The symbol may be delisted or the backend data feed is unavailable.</p>
                  <button onClick={() => loadChart()} className="text-xs text-cyan-400 hover:text-cyan-300 underline mt-1">Retry</button>
                </div>
              )}
            </div>
            {showIndicators && (
              <div ref={rsiContainerRef} className="w-full border-t border-border/20" style={{ height: 110 }} />
            )}
          </>
        )}
      </Card>

      {/* Patterns + Backtest — below chart in a row */}
      {(patterns.length > 0 || (backtest && backtest.instances_found > 0)) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {patterns.length > 0 && (
            <Card className="glass-card p-4">
              <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" /> Detected Patterns
              </h3>
              <div className="space-y-2">
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
            </Card>
          )}

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
      )}
    </div>
  );
}
