import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

interface MacroSignal {
  name: string;
  value: number | null;
  status: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  description: string;
}

interface MacroData {
  verdict: string;
  bullish_count: number;
  bearish_count: number;
  total_signals: number;
  signals: MacroSignal[];
}

export function MacroSignalPanel() {
  const [data, setData] = useState<MacroData | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiService.getMacroSignals();
        setData(res?.data || res);
      } catch {}
    };
    load();
    const interval = setInterval(load, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'BULLISH': return <TrendingUp className="h-3 w-3 text-emerald-400" />;
      case 'BEARISH': return <TrendingDown className="h-3 w-3 text-red-400" />;
      default: return <Minus className="h-3 w-3 text-yellow-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'BULLISH': return 'text-emerald-400 bg-emerald-500/20';
      case 'BEARISH': return 'text-red-400 bg-red-500/20';
      default: return 'text-yellow-400 bg-yellow-500/20';
    }
  };

  return (
    <Card className="glass-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Macro Signals
          </div>
          {data && (
            <Badge className={cn(
              "text-[10px]",
              data.verdict === 'RISK-ON' ? 'text-emerald-400 bg-emerald-500/20' :
              data.verdict === 'RISK-OFF' ? 'text-red-400 bg-red-500/20' :
              'text-yellow-400 bg-yellow-500/20'
            )}>
              {data.verdict}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!data ? (
          <div className="text-xs text-muted-foreground text-center py-4">
            <Activity className="h-6 w-6 mx-auto mb-2 opacity-20 animate-pulse" />
            Loading macro signals...
          </div>
        ) : (
          <div className="space-y-1.5">
            {/* Score bar */}
            <div className="flex items-center gap-2 mb-2">
              <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden flex">
                <div
                  className="h-full bg-emerald-400 transition-all"
                  style={{ width: `${(data.bullish_count / data.total_signals) * 100}%` }}
                />
                <div
                  className="h-full bg-red-400 transition-all"
                  style={{ width: `${(data.bearish_count / data.total_signals) * 100}%` }}
                />
              </div>
              <span className="text-[10px] text-muted-foreground font-mono">
                {data.bullish_count}/{data.total_signals}
              </span>
            </div>

            {/* Signal list */}
            {data.signals.map((signal) => (
              <div key={signal.name} className="flex items-center justify-between py-0.5 group" title={signal.description}>
                <div className="flex items-center gap-1.5 min-w-0">
                  {getStatusIcon(signal.status)}
                  <div className="min-w-0">
                    <span className="text-xs text-foreground">{signal.name}</span>
                    <span className="text-[9px] text-muted-foreground ml-1 hidden group-hover:inline">
                      {signal.description}
                    </span>
                  </div>
                </div>
                <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0 shrink-0", getStatusColor(signal.status))}>
                  {signal.status}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
