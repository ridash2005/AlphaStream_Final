import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Filter } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import { useAppStore } from '@/store/appStore';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface Stock {
  ticker: string;
  company_name?: string;
  sector?: string;
  market_cap_cr?: number;
  last_close?: number;
  latest_signal_type?: string;
  latest_signal_dir?: string;
  latest_alpha_score?: number;
}

const formatMktCap = (cr?: number) => {
  if (!cr) return 'N/A';
  if (cr >= 100000) return `₹${(cr / 100000).toFixed(1)}L Cr`;
  if (cr >= 1000) return `₹${(cr / 1000).toFixed(1)}K Cr`;
  return `₹${cr.toFixed(0)} Cr`;
};

export function StockScreener() {
  const { setTicker } = useAppStore();
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [sectorFilter, setSectorFilter] = useState('');
  const [dirFilter, setDirFilter] = useState('');
  const [minAlpha, setMinAlpha] = useState(0);

  const fetchScreener = useCallback(() => {
    setFetchError(false);
    setLoading(true);
    apiService
      .getScreener({ sector: sectorFilter, direction: dirFilter, minAlpha, limit: 20 })
      .then((d) => {
        setStocks(d?.stocks || []);
        setSectors(d?.sectors || []);
      })
      .catch(() => {
        setFetchError(true);
        setStocks([]);
      })
      .finally(() => setLoading(false));
  }, [sectorFilter, dirFilter, minAlpha]);

  useEffect(() => {
    fetchScreener();
  }, [fetchScreener]);

  const chartData = stocks.slice(0, 10).map((s) => ({
    name: s.ticker,
    alpha: s.latest_alpha_score ?? 0,
    dir: s.latest_signal_dir,
  }));

  return (
    <Card className="glass-card">
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Filter className="h-4 w-4 text-primary" />
          Stock Screener
          {stocks.length > 0 && (
            <span className="text-[10px] text-muted-foreground ml-1">{stocks.length} results</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-3">
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="text-xs bg-secondary/30 border border-border/30 rounded px-2 py-1 focus:outline-none focus:border-primary/50"
          >
            <option value="">All Sectors</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <div className="flex gap-1">
            {(['', 'bullish', 'bearish'] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDirFilter(d)}
                className={cn(
                  'text-[10px] px-2 py-1 rounded transition-colors',
                  dirFilter === d
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {d === '' ? 'All' : d === 'bullish' ? '↑ Bullish' : '↓ Bearish'}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-muted-foreground">Min α:</span>
            <input
              type="range"
              min="0"
              max="80"
              step="10"
              value={minAlpha}
              onChange={(e) => setMinAlpha(Number(e.target.value))}
              className="w-20 accent-primary"
            />
            <span className="text-[10px] font-mono text-muted-foreground">{minAlpha}</span>
          </div>
        </div>

        {/* Mini chart */}
        {chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={60}>
            <BarChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <YAxis hide />
              <Tooltip
                formatter={(v: number | string | undefined) => [`α: ${Number(v ?? 0).toFixed(1)}`, '']}
                contentStyle={{ background: '#0a0a1a', border: '1px solid #333', fontSize: 10 }}
              />
              <Bar dataKey="alpha" radius={2}>
                {chartData.map((e, i) => (
                  <Cell
                    key={i}
                    fill={
                      e.dir === 'bullish'
                        ? '#22c55e'
                        : e.dir === 'bearish'
                        ? '#ef4444'
                        : '#6366f1'
                    }
                  />
                ))}
              </Bar>
              <XAxis
                dataKey="name"
                tick={{ fontSize: 8, fill: '#666', fontFamily: 'monospace' }}
              />
            </BarChart>
          </ResponsiveContainer>
        )}

        {/* Table */}
        {loading && (
          <div className="text-xs text-muted-foreground text-center py-4 animate-pulse">
            Scanning market...
          </div>
        )}
        {!loading && stocks.length === 0 && (
          fetchError ? (
            <div className="text-xs text-destructive text-center py-4">
              Failed to fetch signals — <button onClick={fetchScreener} className="underline">retry</button>
            </div>
          ) : (
            <div className="text-xs text-muted-foreground text-center py-4">
              No signals match filters - try reducing the alpha threshold
            </div>
          )
        )}
        {!loading && stocks.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/30">
                  <th className="text-left font-medium text-muted-foreground pb-1">Ticker</th>
                  <th className="text-left font-medium text-muted-foreground pb-1 hidden sm:table-cell">
                    Sector
                  </th>
                  <th className="text-right font-medium text-muted-foreground pb-1">Mkt Cap</th>
                  <th className="text-right font-medium text-muted-foreground pb-1">Signal</th>
                  <th className="text-right font-medium text-muted-foreground pb-1">Alpha</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map((s, i) => (
                  <tr
                    key={i}
                    onClick={() => setTicker(s.ticker)}
                    className="border-b border-border/10 hover:bg-secondary/20 cursor-pointer transition-colors"
                  >
                    <td className="py-1.5 font-mono font-semibold text-primary">{s.ticker}</td>
                    <td className="py-1.5 text-muted-foreground hidden sm:table-cell truncate max-w-[100px]">
                      {s.sector || 'N/A'}
                    </td>
                    <td className="py-1.5 text-right text-muted-foreground">
                      {formatMktCap(s.market_cap_cr)}
                    </td>
                    <td className="py-1.5 text-right">
                      <span
                        className={cn(
                          'px-1.5 py-0.5 rounded text-[10px]',
                          s.latest_signal_dir === 'bullish'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : s.latest_signal_dir === 'bearish'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-secondary/50 text-muted-foreground'
                        )}
                      >
                        {s.latest_signal_dir || s.latest_signal_type || 'N/A'}
                      </span>
                    </td>
                    <td className="py-1.5 text-right font-mono text-foreground">
                      {s.latest_alpha_score != null ? s.latest_alpha_score.toFixed(1) : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
