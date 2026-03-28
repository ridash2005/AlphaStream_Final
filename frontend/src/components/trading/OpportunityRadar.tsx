import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, RefreshCw, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiService } from '@/services/api';

interface Signal {
  signal_id: string;
  ticker: string;
  alpha_score: number;
  direction: string;
  top_signals: { type: string; score: number; detail: string; evidence: string[] }[];
  timestamp: string;
}

function DirectionBadge({ direction }: { direction: string }) {
  const config: Record<string, { color: string; icon: JSX.Element; label: string }> = {
    STRONG_BUY:  { color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: <TrendingUp className="h-3 w-3" />, label: 'Strong Buy' },
    BUY:         { color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: <TrendingUp className="h-3 w-3" />, label: 'Buy' },
    HOLD:        { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: <Minus className="h-3 w-3" />, label: 'Hold' },
    SELL:        { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: <TrendingDown className="h-3 w-3" />, label: 'Sell' },
    STRONG_SELL: { color: 'bg-red-600/20 text-red-300 border-red-600/30', icon: <TrendingDown className="h-3 w-3" />, label: 'Strong Sell' },
  };
  const c = config[direction] || config.HOLD;
  return (
    <Badge variant="outline" className={`${c.color} flex items-center gap-1 text-xs`}>
      {c.icon} {c.label}
    </Badge>
  );
}

function AlphaScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-secondary/50 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-sm font-bold tabular-nums w-10 text-right">{score.toFixed(0)}</span>
    </div>
  );
}

function SignalCard({ signal }: { signal: Signal }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <Card
      className="glass-card p-4 cursor-pointer hover:border-primary/30 transition-all"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="font-mono font-bold text-lg">{signal.ticker}</span>
        </div>
        <DirectionBadge direction={signal.direction} />
      </div>
      <AlphaScoreBar score={signal.alpha_score} />
      {expanded && signal.top_signals && (
        <div className="mt-3 pt-3 border-t border-border/30 space-y-2">
          {signal.top_signals.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <Badge variant="outline" className="text-[10px] px-1.5">{s.type}</Badge>
              <span className="text-muted-foreground flex-1">{s.detail}</span>
              <span className="font-mono tabular-nums text-muted-foreground">{s.score.toFixed(0)}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// Group signals by sector theme
function groupByTheme(signals: Signal[]): Record<string, Signal[]> {
  const groups: Record<string, Signal[]> = {};
  for (const s of signals) {
    // Extract sector from top_signals evidence if available
    const sector = (s as any).sector || 'Other';
    if (!groups[sector]) groups[sector] = [];
    groups[sector].push(s);
  }
  return groups;
}

function ThemeBadge({ sector, signals }: { sector: string; signals: Signal[] }) {
  const bullish = signals.filter(s => ['BUY', 'STRONG_BUY'].includes(s.direction)).length;
  const bearish = signals.filter(s => ['SELL', 'STRONG_SELL'].includes(s.direction)).length;
  const color = bullish > bearish ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    : bearish > bullish ? 'text-red-400 bg-red-500/10 border-red-500/20'
    : 'text-amber-400 bg-amber-500/10 border-amber-500/20';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${color}`}>
      {sector}: {bullish}B {bearish}S
    </span>
  );
}

export function OpportunityRadar() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchRadar = async () => {
    setLoading(true);
    try {
      const data = await apiService.getRadar(15);
      setSignals(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Radar fetch failed:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRadar(); }, []);

  const themes = groupByTheme(signals);

  return (
    <Card className="glass-card p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Opportunity Radar
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">Top signals by Alpha Score</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchRadar} disabled={loading}>
          {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
        </Button>
      </div>

      {/* Sector themes */}
      {Object.keys(themes).length > 1 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {Object.entries(themes).map(([sector, sigs]) => (
            <ThemeBadge key={sector} sector={sector} signals={sigs} />
          ))}
        </div>
      )}

      {signals.length === 0 && !loading && (
        <p className="text-sm text-muted-foreground text-center py-8">No signals detected. Try refreshing.</p>
      )}
      <div className="space-y-3">
        {signals.map((s) => (
          <SignalCard key={s.signal_id || s.ticker} signal={s} />
        ))}
      </div>
    </Card>
  );
}
