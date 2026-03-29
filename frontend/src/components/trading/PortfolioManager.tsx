import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Briefcase, Plus, Trash2, Save, RefreshCw, AlertCircle, Download } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import { useAppStore } from '@/store/appStore';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface Holding {
  ticker: string;
  quantity: number;
  buy_price: number;
}

interface PortfolioSummary {
  total_invested: number;
  total_current: number;
  total_pnl: number;
  total_pnl_pct: number;
  holdings: Array<{
    ticker: string;
    quantity: number;
    buy_price: number;
    current_price?: number;
    invested?: number;
    current_value?: number;
    pnl?: number;
    pnl_pct?: number;
  }>;
}

const formatINR = (v: number) => `₹${Math.abs(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

export function PortfolioManager() {
  const { portfolio, setPortfolio } = useAppStore();
  const [holdings, setHoldings] = useState<Holding[]>(portfolio || []);
  const [ticker, setTicker] = useState('');
  const [qty, setQty] = useState('');
  const [buyPrice, setBuyPrice] = useState('');
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addHolding = () => {
    if (!ticker || !qty || !buyPrice) return;
    setHoldings(prev => [...prev, {
      ticker: ticker.toUpperCase().trim(),
      quantity: Number(qty),
      buy_price: Number(buyPrice),
    }]);
    setTicker(''); setQty(''); setBuyPrice('');
  };

  const removeHolding = (i: number) => setHoldings(prev => prev.filter((_, idx) => idx !== i));

  const savePortfolio = async () => {
    setSaving(true);
    setError(null);
    try {
      await apiService.setPortfolio(holdings);
      setPortfolio(holdings);
      const s = await apiService.getPortfolioSummary();
      setSummary(s);
    } catch (e) {
      setError('Failed to save portfolio. Check backend connection.');
    } finally {
      setSaving(false);
    }
  };

  const importFromGroww = async () => {
    setImporting(true);
    setError(null);
    try {
      const result = await apiService.importGrowwPortfolio();
      if (result.error) {
        setError(result.error);
        return;
      }
      const imported = (result.holdings || []).map((h: { ticker: string; quantity: number; buy_price: number }) => ({
        ticker: h.ticker,
        quantity: h.quantity,
        buy_price: h.buy_price,
      }));
      setHoldings(imported);
      setPortfolio(imported);
      setSummary(result);
    } catch {
      setError('Failed to import from Groww. Ensure GROWW_API_TOKEN is set in backend/.env.');
    } finally {
      setImporting(false);
    }
  };

  useEffect(() => {
    if (holdings.length > 0) {
      setLoadingSummary(true);
      apiService.getPortfolioSummary()
        .then(s => setSummary(s))
        .catch(() => setError('Failed to load portfolio data'))
        .finally(() => setLoadingSummary(false));
    }
  }, []);

  const chartData = summary?.holdings?.map(h => ({
    name: h.ticker,
    pnl: h.pnl_pct ?? 0,
  })) || [];

  return (
    <Card className="glass-card">
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Briefcase className="h-4 w-4 text-primary" />
          Portfolio Manager
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-1.5 mb-3 p-2 rounded bg-amber-500/10 border border-amber-500/20">
          <AlertCircle className="h-3 w-3 text-amber-400 shrink-0" />
          <p className="text-[10px] text-amber-400">Portfolio is session-based - re-enter holdings after server restart</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Left: Add Holdings */}
          <div>
            <p className="text-xs font-medium mb-2 text-muted-foreground">Add Holdings</p>
            <div className="flex gap-1.5 mb-2">
              <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())}
                placeholder="TICKER" className="flex-1 bg-secondary/30 border border-border/30 rounded px-2 py-1 text-xs font-mono uppercase placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/50" />
              <input value={qty} onChange={e => setQty(e.target.value)}
                type="number" min="1" placeholder="Qty"
                className="w-16 bg-secondary/30 border border-border/30 rounded px-2 py-1 text-xs focus:outline-none focus:border-primary/50" />
              <input value={buyPrice} onChange={e => setBuyPrice(e.target.value)}
                type="number" min="0" placeholder="₹ Price"
                className="w-20 bg-secondary/30 border border-border/30 rounded px-2 py-1 text-xs focus:outline-none focus:border-primary/50" />
              <button onClick={addHolding}
                className="p-1.5 rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors">
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>

            {holdings.length > 0 && (
              <div className="space-y-1 mb-3 max-h-40 overflow-y-auto scrollbar-hide">
                {holdings.map((h, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs bg-secondary/20 rounded px-2 py-1">
                    <span className="font-mono font-semibold w-24 truncate">{h.ticker}</span>
                    <span className="text-muted-foreground">{h.quantity} @ ₹{h.buy_price.toLocaleString('en-IN')}</span>
                    <button onClick={() => removeHolding(i)} className="ml-auto text-muted-foreground hover:text-destructive">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-1.5">
              <button onClick={savePortfolio} disabled={saving || holdings.length === 0}
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors text-xs font-medium disabled:opacity-50">
                {saving ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button onClick={importFromGroww} disabled={importing}
                title="Import holdings from your Groww account (requires GROWW_API_TOKEN in backend/.env)"
                className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors text-xs font-medium disabled:opacity-50">
                {importing ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                {importing ? 'Importing...' : 'Groww'}
              </button>
            </div>
            {error && <p className="text-xs text-destructive mt-1">{error}</p>}
          </div>

          {/* Right: Summary */}
          <div>
            {loadingSummary ? (
              <div className="flex items-center justify-center h-full min-h-[80px]">
                <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : summary ? (
              <div>
                <div className="grid grid-cols-3 gap-1.5 mb-3">
                  {[
                    { label: 'Invested', value: formatINR(summary.total_invested) },
                    { label: 'Current', value: formatINR(summary.total_current) },
                    { label: 'P&L', value: `${summary.total_pnl >= 0 ? '+' : ''}${formatINR(summary.total_pnl)}`, isPN: true, positive: summary.total_pnl >= 0 },
                  ].map(m => (
                    <div key={m.label} className="bg-secondary/20 rounded p-1.5 text-center">
                      <div className="text-[10px] text-muted-foreground">{m.label}</div>
                      <div className={cn("text-xs font-mono font-semibold", m.isPN && (m.positive ? 'text-emerald-400' : 'text-red-400'))}>
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>

                {chartData.length > 0 && (
                  <ResponsiveContainer width="100%" height={80}>
                    <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                      <XAxis type="number" tick={{ fontSize: 9, fill: '#666' }} tickFormatter={v => `${v}%`} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: '#888', fontFamily: 'monospace' }} width={50} />
                      <Tooltip formatter={(v: number | undefined) => [`${(v ?? 0).toFixed(2)}%`, 'P&L']} contentStyle={{ background: '#0a0a1a', border: '1px solid #333', fontSize: 11 }} />
                      <Bar dataKey="pnl" radius={2}>
                        {chartData.map((entry, i) => (
                          <Cell key={i} fill={entry.pnl >= 0 ? '#22c55e' : '#ef4444'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground text-center py-8">Add holdings and save to see P&amp;L summary</div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
