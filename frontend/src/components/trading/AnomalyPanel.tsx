import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import { useAppStore } from '@/store/appStore';

interface Anomaly {
  type: string;
  score: number;
  direction?: string;
  detail?: string;
  ticker?: string;
}

interface AnomalyData {
  ticker: string;
  anomalies: Anomaly[];
  fed_ticks: number;
  error?: string;
}

const TYPE_STYLE: Record<string, { label: string; color: string }> = {
  price_anomaly: { label: 'Price', color: 'bg-red-500/20 text-red-400' },
  volume_anomaly: { label: 'Volume', color: 'bg-amber-500/20 text-amber-400' },
  sentiment_drift: { label: 'Sentiment', color: 'bg-blue-500/20 text-blue-400' },
};

export function AnomalyPanel() {
  const { currentTicker } = useAppStore();
  const [data, setData] = useState<AnomalyData | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  const fetch = () => {
    setLoading(true);
    setHasError(false);
    apiService.getAnomalies(currentTicker)
      .then(d => setData(d))
      .catch(() => { setHasError(true); setData(null); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, [currentTicker]);

  const anomalies = data?.anomalies || [];
  const count = anomalies.length;

  return (
    <Card className="glass-card">
      <CardHeader className="pb-1">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Anomaly Detection
            {count > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 font-mono">
                {count}
              </span>
            )}
          </CardTitle>
          <button onClick={fetch} disabled={loading}
            className="p-1 rounded hover:bg-secondary/50 text-muted-foreground transition-colors">
            <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="text-xs text-muted-foreground text-center py-4 animate-pulse">
            Analysing {currentTicker}...
          </div>
        )}

        {!loading && hasError && (
          <div className="text-xs text-muted-foreground text-center py-4">
            <AlertCircle className="h-4 w-4 mx-auto mb-1 text-red-400 opacity-60" />
            Failed to load anomalies
          </div>
        )}

        {!loading && !hasError && (data?.error && count === 0) && (
          <div className="text-xs text-muted-foreground text-center py-4">
            <AlertTriangle className="h-5 w-5 mx-auto mb-1 opacity-20" />
            {data.error.includes('No OHLCV') ? 'No market data available' : 'Anomaly detection unavailable'}
          </div>
        )}

        {!loading && !hasError && !data?.error && count === 0 && (
          <div className="text-xs text-muted-foreground text-center py-4">
            <div className="text-emerald-400 text-sm font-mono mb-1">✓ Normal</div>
            No anomalies detected - price action within normal bounds
            {data?.fed_ticks ? (
              <div className="text-[10px] mt-1">Analysed {data.fed_ticks} ticks (3mo NSE data)</div>
            ) : null}
          </div>
        )}

        {!loading && !hasError && count > 0 && (
          <div className="space-y-2">
            {anomalies.map((a, i) => {
              const style = TYPE_STYLE[a.type] || { label: a.type, color: 'bg-secondary/50 text-muted-foreground' };
              return (
                <div key={i} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0", style.color)}>
                      {style.label}
                    </span>
                    {a.direction && (
                      <span className={cn(
                        "text-[10px]",
                        a.direction === 'bullish' ? 'text-emerald-400' :
                        a.direction === 'bearish' ? 'text-red-400' :
                        'text-muted-foreground'
                      )}>
                        {a.direction}
                      </span>
                    )}
                    <div className="flex-1 h-1 bg-secondary rounded-full overflow-hidden">
                      <div
                        className="h-full bg-amber-400/70 rounded-full transition-all"
                        style={{ width: `${Math.min(100, (a.score ?? 0) * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {((a.score ?? 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  {a.detail && (
                    <p className="text-[10px] text-muted-foreground pl-2">{a.detail}</p>
                  )}
                </div>
              );
            })}
            {data?.fed_ticks && (
              <div className="text-[10px] text-muted-foreground pt-1">
                Based on {data.fed_ticks} ticks (3mo NSE data)
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
