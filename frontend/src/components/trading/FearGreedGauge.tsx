import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Gauge, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

interface FearGreedData {
  score: number;
  label: string;
  previous: number;
  timestamp: string;
}

interface VixData {
  value: number | null;
  change: number;
  status: string;
}

export function FearGreedGauge() {
  const [data, setData] = useState<FearGreedData | null>(null);
  const [vix, setVix] = useState<VixData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const [fgRes, vixRes] = await Promise.allSettled([
        apiService.getFearGreed(),
        apiService.getVix(),
      ]);
      if (fgRes.status === 'fulfilled') setData(fgRes.value?.data || fgRes.value);
      if (vixRes.status === 'fulfilled') setVix(vixRes.value?.data || vixRes.value);
      setLoading(false);
    };
    load();
    const interval = setInterval(load, 10 * 60 * 1000); // 10min
    return () => clearInterval(interval);
  }, []);

  const score = data?.score ?? 50;
  const label = data?.label ?? 'Neutral';
  const delta = data ? score - data.previous : 0;

  // SVG arc for semicircular gauge
  const radius = 60;
  const cx = 70;
  const cy = 65;
  const scoreAngle = Math.PI - (score / 100) * Math.PI;

  const arcX = cx + radius * Math.cos(scoreAngle);
  const arcY = cy - radius * Math.sin(scoreAngle);

  const getScoreInfo = (s: number) => {
    if (s <= 25) return { color: '#ef4444', className: 'text-red-400' };
    if (s <= 45) return { color: '#f97316', className: 'text-orange-400' };
    if (s <= 55) return { color: '#eab308', className: 'text-yellow-400' };
    if (s <= 75) return { color: '#84cc16', className: 'text-lime-400' };
    return { color: '#22c55e', className: 'text-emerald-400' };
  };

  const getVixColor = (status: string) => {
    switch (status) {
      case 'LOW': return 'text-emerald-400';
      case 'MODERATE': return 'text-yellow-400';
      case 'HIGH': return 'text-orange-400';
      case 'EXTREME': return 'text-red-400';
      default: return 'text-muted-foreground';
    }
  };

  return (
    <Card className="glass-card">
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Gauge className="h-4 w-4 text-primary" />
          Fear & Greed
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8 gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-xs">Loading...</span>
          </div>
        ) : (
        <div className="flex flex-col items-center">
          <svg width="140" height="80" viewBox="0 0 140 80">
            {/* Background arc */}
            <path
              d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
              fill="none"
              stroke="oklch(0.25 0.01 270)"
              strokeWidth="10"
              strokeLinecap="round"
            />
            {/* Score arc */}
            {score > 0 && (
              <path
                d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 ${score > 50 ? 1 : 0} 1 ${arcX.toFixed(1)} ${arcY.toFixed(1)}`}
                fill="none"
                stroke={getScoreInfo(score).color}
                strokeWidth="10"
                strokeLinecap="round"
              />
            )}
            {/* Needle dot */}
            <circle cx={arcX} cy={arcY} r="4" fill="white" />
            {/* Labels */}
            <text x="10" y={cy + 15} fill="oklch(0.5 0 0)" fontSize="8" textAnchor="start">Fear</text>
            <text x="130" y={cy + 15} fill="oklch(0.5 0 0)" fontSize="8" textAnchor="end">Greed</text>
          </svg>

          {/* Score display */}
          <div className="text-center -mt-2">
            <div className={cn("text-2xl font-bold font-mono", getScoreInfo(score).className)}>
              {score.toFixed(0)}
            </div>
            <div className="text-xs text-muted-foreground">{label}</div>
            {delta !== 0 && (
              <div className={cn("text-[10px] font-mono", delta > 0 ? "text-emerald-400" : "text-red-400")}>
                {delta > 0 ? '+' : ''}{delta.toFixed(1)} from prev
              </div>
            )}
          </div>

          {/* VIX indicator below gauge */}
          {vix && vix.value != null && (
            <div className="mt-2 pt-2 border-t border-border/30 w-full flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground">VIX</span>
              <div className="flex items-center gap-1.5">
                <span className={cn("text-xs font-mono font-bold", getVixColor(vix.status))}>
                  {vix.value.toFixed(1)}
                </span>
                <span className={cn(
                  "text-[10px] font-mono",
                  vix.change > 0 ? "text-red-400" : vix.change < 0 ? "text-emerald-400" : "text-muted-foreground"
                )}>
                  {vix.change > 0 ? '+' : ''}{vix.change.toFixed(1)}%
                </span>
                <span className={cn("text-[10px] px-1 py-0.5 rounded", {
                  "bg-emerald-500/20 text-emerald-400": vix.status === 'LOW',
                  "bg-yellow-500/20 text-yellow-400": vix.status === 'MODERATE',
                  "bg-orange-500/20 text-orange-400": vix.status === 'HIGH',
                  "bg-red-500/20 text-red-400": vix.status === 'EXTREME',
                })}>
                  {vix.status}
                </span>
              </div>
            </div>
          )}
        </div>
        )}
      </CardContent>
    </Card>
  );
}
