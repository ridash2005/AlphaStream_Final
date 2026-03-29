import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Globe } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface Quote {
  symbol: string;
  name: string;
  display: string;
  price: number;
  change: number;
  sparkline?: number[];
}

// Mini sparkline component
function MiniSparkline({ data, positive }: { data?: number[]; positive: boolean }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 60; const h = 24;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ');
  return (
    <svg width={w} height={h} className="opacity-70">
      <polyline points={pts} fill="none" stroke={positive ? '#22c55e' : '#ef4444'} strokeWidth="1.5" />
    </svg>
  );
}

// Sector name abbreviations for display
const SECTOR_SHORT: Record<string, string> = {
  'XLK': 'Tech', 'XLF': 'Finance', 'XLE': 'Energy', 'XLV': 'Health',
  'XLY': 'Consumer', 'XLI': 'Industrial', 'XLP': 'Staples', 'XLU': 'Utilities',
  'XLB': 'Materials', 'XLRE': 'Real Est.', 'XLC': 'Comm', 'SMH': 'Semis',
};

// India impact notes for sectors
const INDIA_IMPACT: Record<string, string> = {
  'XLE': 'Impacts Indian oil import costs',
  'XLK': 'IT sector bellwether for TCS/Infy',
  'XLF': 'Global banking sentiment',
  'SMH': 'Chip supply chain - impacts Indian tech',
};

// Crypto India rupee equivalent note
function CryptoCard({ q, usdInr }: { q: Quote; usdInr: number }) {
  const pos = q.change >= 0;
  const inrPrice = usdInr > 0 ? `₹${(q.price * usdInr).toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : null;
  return (
    <div className="bg-secondary/20 rounded-lg p-2.5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold font-mono">{q.display || q.symbol.replace('-USD', '')}</span>
        <span className={cn("text-[10px] font-mono px-1.5 py-0.5 rounded", pos ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400")}>
          {pos ? '+' : ''}{q.change?.toFixed(2)}%
        </span>
      </div>
      <div className="text-sm font-mono font-bold">${q.price?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: q.price > 100 ? 0 : 4 })}</div>
      {inrPrice && <div className="text-[10px] text-muted-foreground">{inrPrice}</div>}
      <MiniSparkline data={q.sparkline} positive={pos} />
    </div>
  );
}

type TabType = 'crypto' | 'currencies' | 'sectors';

export function GlobalMarketsPanel() {
  const [activeTab, setActiveTab] = useState<TabType>('crypto');
  const [crypto, setCrypto] = useState<Quote[]>([]);
  const [currencies, setCurrencies] = useState<Quote[]>([]);
  const [sectors, setSectors] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);

  const usdInr = currencies.find(c => c.symbol === 'INR=X' || c.symbol?.includes('INR'))?.price || 0;

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      apiService.getCryptoQuotes(),
      apiService.getCurrencyQuotes(),
      apiService.getSectorPerformance(),
    ]).then(([cryptoRes, fxRes, sectorRes]) => {
      if (cryptoRes.status === 'fulfilled') {
        const d = cryptoRes.value;
        setCrypto(d?.data || (Array.isArray(d) ? d : []));
      }
      if (fxRes.status === 'fulfilled') {
        const d = fxRes.value;
        setCurrencies(d?.data || (Array.isArray(d) ? d : []));
      }
      if (sectorRes.status === 'fulfilled') {
        const d = sectorRes.value;
        setSectors(d?.data || (Array.isArray(d) ? d : []));
      }
      setLoading(false);
    });
  }, []);

  const sectorChartData = sectors.map(s => ({
    name: SECTOR_SHORT[s.symbol] || s.symbol,
    symbol: s.symbol,
    change: s.change ?? 0,
  })).sort((a, b) => b.change - a.change);

  const tabs: { key: TabType; label: string }[] = [
    { key: 'crypto', label: 'Crypto' },
    { key: 'currencies', label: 'Currencies' },
    { key: 'sectors', label: 'US Sectors' },
  ];

  return (
    <Card className="glass-card">
      <CardHeader className="pb-1">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Globe className="h-4 w-4 text-primary" />
            Global Markets
          </CardTitle>
          <div className="flex gap-1">
            {tabs.map(t => (
              <button key={t.key} onClick={() => setActiveTab(t.key)}
                className={cn("text-[10px] px-2 py-0.5 rounded transition-colors",
                  activeTab === t.key ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground")}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading && <div className="text-xs text-muted-foreground text-center py-6 animate-pulse">Loading market data...</div>}

        {!loading && activeTab === 'crypto' && (
          <div>
            <div className="grid grid-cols-2 gap-2">
              {crypto.slice(0, 4).map(q => <CryptoCard key={q.symbol} q={q} usdInr={usdInr} />)}
            </div>
            {crypto.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">Crypto data unavailable</p>}
          </div>
        )}

        {!loading && activeTab === 'currencies' && (
          <div className="space-y-2">
            {currencies.map(c => {
              const pos = c.change >= 0;
              const isInr = c.symbol === 'INR=X' || c.symbol?.includes('INR');
              return (
                <div key={c.symbol} className="flex items-center justify-between bg-secondary/20 rounded-lg p-2.5">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold font-mono">{c.display || c.name}</span>
                      <span className={cn("text-[10px] px-1.5 py-0.5 rounded", pos ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400")}>
                        {pos ? '+' : ''}{c.change?.toFixed(3)}%
                      </span>
                    </div>
                    {isInr && <div className="text-[10px] text-muted-foreground mt-0.5">
                      {pos ? 'Rupee weakening → higher import costs' : 'Rupee strengthening → lower import costs'}
                    </div>}
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-mono font-bold">{c.price?.toFixed(4)}</div>
                    <MiniSparkline data={c.sparkline} positive={pos} />
                  </div>
                </div>
              );
            })}
            {currencies.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">Currency data unavailable</p>}
          </div>
        )}

        {!loading && activeTab === 'sectors' && (
          <div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={sectorChartData} layout="vertical" margin={{ top: 0, right: 40, left: 0, bottom: 0 }}>
                <XAxis type="number" tick={{ fontSize: 9, fill: '#666' }} tickFormatter={(v: number) => `${v}%`} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: '#888' }} width={55} />
                <Tooltip
                  formatter={(v: number, _name: string, props: { payload?: { symbol?: string } }) => {
                    const note = INDIA_IMPACT[props.payload?.symbol ?? ''] || '';
                    return [`${v.toFixed(2)}%${note ? ` - ${note}` : ''}`, 'Change'];
                  }}
                  contentStyle={{ background: '#0a0a1a', border: '1px solid #333', fontSize: 11 }}
                />
                <Bar dataKey="change" radius={2}>
                  {sectorChartData.map((entry, i) => (
                    <Cell key={i} fill={entry.change >= 0 ? '#22c55e' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
