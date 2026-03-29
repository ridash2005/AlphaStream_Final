import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Star, Plus, X, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/store/appStore';

type SortMode = 'alpha' | 'score';

export function WatchlistPanel() {
  const { watchlist, addToWatchlist, removeFromWatchlist, setTicker, marketHeatmap } = useAppStore();
  const [input, setInput] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('score');

  const add = () => {
    const t = input.trim().toUpperCase();
    if (t.length >= 2 && t.length <= 20) {
      addToWatchlist(t);
      setInput('');
    }
  };

  const getScore = (ticker: string): number | null => {
    if (!marketHeatmap || !Array.isArray(marketHeatmap)) return null;
    const entry = marketHeatmap.find((h: any) => h.ticker === ticker || h.ticker === `${ticker}.NS`);
    return entry?.score ?? null;
  };

  const sorted = [...watchlist].sort((a, b) => {
    if (sortMode === 'alpha') return a.localeCompare(b);
    const sa = getScore(a) ?? -1;
    const sb = getScore(b) ?? -1;
    return sb - sa;
  });

  return (
    <Card className="glass-card">
      <CardHeader className="pb-1">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Star className="h-4 w-4 text-amber-400" />
            Watchlist
            <span className="text-[10px] text-muted-foreground">{watchlist.length}/20</span>
          </CardTitle>
          <div className="flex gap-1">
            <button onClick={() => setSortMode('alpha')}
              className={cn("text-[10px] px-2 py-0.5 rounded transition-colors",
                sortMode === 'alpha' ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground")}>
              A-Z
            </button>
            <button onClick={() => setSortMode('score')}
              className={cn("text-[10px] px-2 py-0.5 rounded transition-colors",
                sortMode === 'score' ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground")}>
              Score
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Add ticker input */}
        <div className="flex gap-1.5 mb-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && add()}
            placeholder="Add ticker (e.g. WIPRO)"
            className="flex-1 bg-secondary/30 border border-border/30 rounded px-2 py-1 text-xs font-mono uppercase placeholder:normal-case placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50"
          />
          <button onClick={add} disabled={watchlist.length >= 20}
            className="p-1.5 rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors disabled:opacity-40">
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Watchlist */}
        {sorted.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">
            Add up to 20 tickers to your watchlist
          </p>
        ) : (
          <div className="space-y-1 max-h-64 overflow-y-auto scrollbar-hide">
            {sorted.map(ticker => {
              const score = getScore(ticker);
              const isPositive = score != null && score >= 50;
              const isNeutral = score != null && score >= 40 && score < 50;
              const Icon = score == null ? Minus : isPositive ? TrendingUp : isNeutral ? Minus : TrendingDown;
              const scoreColor = score == null ? 'text-muted-foreground' : isPositive ? 'text-emerald-400' : isNeutral ? 'text-yellow-400' : 'text-red-400';

              return (
                <div key={ticker} className="flex items-center gap-2 group hover:bg-secondary/20 rounded px-1.5 py-1 transition-colors">
                  {/* Score indicator */}
                  <Icon className={cn("h-3 w-3 shrink-0", scoreColor)} />

                  {/* Ticker */}
                  <span className="font-mono font-semibold text-xs flex-1">{ticker}</span>

                  {/* Score badge */}
                  {score != null && (
                    <span className={cn("text-[10px] font-mono", scoreColor)}>
                      {score.toFixed(0)}
                    </span>
                  )}

                  {/* Analyze button */}
                  <button
                    onClick={() => setTicker(ticker)}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary hover:bg-primary/20 opacity-0 group-hover:opacity-100 transition-all"
                  >
                    Analyze
                  </button>

                  {/* Remove button */}
                  <button
                    onClick={() => removeFromWatchlist(ticker)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-destructive/20"
                  >
                    <X className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
