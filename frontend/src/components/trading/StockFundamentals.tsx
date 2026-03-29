import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import { useAppStore } from '@/store/appStore';

interface Fundamentals {
  ticker: string;
  pe_ratio: number | null;
  pb_ratio: number | null;
  dividend_yield: number | null;
  roe: number | null;
  market_cap_cr: number | null;
  year_high: number | null;
  year_low: number | null;
  current_price: number | null;
  error?: string;
}

const formatMktCap = (cr: number | null) => {
  if (!cr) return 'N/A';
  if (cr >= 100000) return `₹${(cr / 100000).toFixed(1)}L Cr`;
  if (cr >= 1000) return `₹${(cr / 1000).toFixed(1)}K Cr`;
  return `₹${cr.toFixed(0)} Cr`;
};

export function StockFundamentals() {
  const { currentTicker } = useAppStore();
  const [data, setData] = useState<Fundamentals | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    apiService.getFundamentals(currentTicker)
      .then(d => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [currentTicker]);

  const metrics = data ? [
    { label: 'P/E Ratio', value: data.pe_ratio != null ? `${data.pe_ratio.toFixed(1)}x` : 'N/A' },
    { label: 'P/B Ratio', value: data.pb_ratio != null ? `${data.pb_ratio.toFixed(2)}x` : 'N/A' },
    { label: 'ROE', value: data.roe != null ? `${data.roe.toFixed(1)}%` : 'N/A' },
    { label: 'Div. Yield', value: data.dividend_yield != null ? `${data.dividend_yield.toFixed(2)}%` : 'N/A' },
    { label: 'Mkt Cap', value: formatMktCap(data.market_cap_cr), colSpan: true },
  ] : [];

  return (
    <Card className="glass-card">
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <BarChart2 className="h-4 w-4 text-primary" />
          Fundamentals: {currentTicker}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="text-xs text-muted-foreground text-center py-4 animate-pulse">Loading fundamentals...</div>
        )}
        {!loading && data?.error && (
          <div className="text-xs text-muted-foreground text-center py-4">{data.error}</div>
        )}
        {!loading && data && !data.error && (
          <div>
            <div className="grid grid-cols-2 gap-2 mb-3">
              {metrics.map(m => (
                <div key={m.label} className={cn("bg-secondary/20 rounded-lg p-2", m.colSpan && "col-span-2")}>
                  <div className="text-[10px] text-muted-foreground">{m.label}</div>
                  <div className="text-sm font-mono font-semibold text-foreground">{m.value}</div>
                </div>
              ))}
            </div>
            {/* 52-week range bar */}
            {data.year_high && data.year_low && (
              <div className="pt-2 border-t border-border/30">
                <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
                  <span>52W Low: ₹{data.year_low.toLocaleString('en-IN')}</span>
                  <span>52W High: ₹{data.year_high.toLocaleString('en-IN')}</span>
                </div>
                <div className="w-full h-2 bg-secondary rounded-full relative overflow-hidden">
                  <div className="absolute inset-y-0 left-0 bg-gradient-to-r from-red-500 to-emerald-500 rounded-full"
                    style={{ width: '100%' }} />
                  {data.current_price && (
                    <div className="absolute top-0 h-full w-0.5 bg-white"
                      style={{ left: `${Math.min(100, Math.max(0, ((data.current_price - data.year_low) / ((data.year_high - data.year_low) || 1)) * 100))}%` }} />
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
