import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { MiniSparkline } from '@/utils/sparkline';
import { apiService } from '@/services/api';

interface CommodityQuote {
  symbol: string;
  name: string;
  display: string;
  price: number | null;
  change: number;
  sparkline: number[];
}

export function CommodityStrip() {
  const [data, setData] = useState<CommodityQuote[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiService.getCommodityQuotes();
        setData(res.data || []);
      } catch {}
    };
    load();
    const interval = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className="glass-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-primary" />
          Commodities
        </CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <div className="text-xs text-muted-foreground text-center py-4">
            <BarChart3 className="h-6 w-6 mx-auto mb-2 opacity-20" />
            Loading commodities...
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-1.5">
            {data.map((item) => (
              <div
                key={item.symbol}
                className={cn(
                  "flex items-center justify-between px-2 py-1.5 rounded-md border",
                  item.change > 0
                    ? "border-emerald-500/20 bg-emerald-500/5"
                    : item.change < 0
                    ? "border-red-500/20 bg-red-500/5"
                    : "border-border/30 bg-secondary/20"
                )}
              >
                <div className="min-w-0">
                  <div className="text-[10px] text-muted-foreground truncate">{item.display}</div>
                  <div className="text-xs font-mono text-foreground">
                    {item.price != null
                      ? item.price.toLocaleString(undefined, { maximumFractionDigits: 2 })
                      : '—'}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {item.sparkline?.length > 1 && (
                    <MiniSparkline data={item.sparkline} change={item.change} width={32} height={14} />
                  )}
                  <span className={cn(
                    "text-[10px] font-mono",
                    item.change > 0 ? "text-emerald-400" : item.change < 0 ? "text-red-400" : "text-muted-foreground"
                  )}>
                    {item.change > 0 ? '+' : ''}{item.change.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
