import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { MiniSparkline } from '@/utils/sparkline';
import { apiService } from '@/services/api';

interface GlobalQuote {
  symbol: string;
  name: string;
  display: string;
  price: number | null;
  change: number;
  sparkline: number[];
}

export function GlobalMarketBar() {
  const [indices, setIndices] = useState<GlobalQuote[]>([]);
  const [commodities, setCommodities] = useState<GlobalQuote[]>([]);
  const [crypto, setCrypto] = useState<GlobalQuote[]>([]);
  const [currencies, setCurrencies] = useState<GlobalQuote[]>([]);
  const [fearGreed, setFearGreed] = useState<{ score: number; label: string } | null>(null);
  const [vix, setVix] = useState<{ value: number | null; status: string } | null>(null);

  useEffect(() => {
    const load = async () => {
      const [idxRes, comRes, fgRes, vixRes, cryptoRes, currRes] = await Promise.allSettled([
        apiService.getGlobalIndices(),
        apiService.getCommodityQuotes(),
        apiService.getFearGreed(),
        apiService.getVix(),
        apiService.getCryptoQuotes(),
        apiService.getCurrencyQuotes(),
      ]);
      if (idxRes.status === 'fulfilled') setIndices(idxRes.value.data || []);
      if (comRes.status === 'fulfilled') setCommodities(comRes.value.data || []);
      if (fgRes.status === 'fulfilled') setFearGreed(fgRes.value?.data || fgRes.value);
      if (vixRes.status === 'fulfilled') setVix(vixRes.value?.data || vixRes.value);
      if (cryptoRes.status === 'fulfilled') setCrypto(cryptoRes.value.data || []);
      if (currRes.status === 'fulfilled') setCurrencies(currRes.value.data || []);
    };
    load();
    const interval = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Combine: indices + key commodities (Gold, Oil, Brent) + crypto + currencies
  const allItems = [
    ...indices,
    ...commodities.filter(c => ['GOLD', 'OIL', 'BRENT', 'SILVER'].includes(c.display)),
    ...crypto,
    ...currencies,
  ];

  if (allItems.length === 0) return null;

  return (
    <div className="glass border-b border-border/30 shrink-0 overflow-hidden relative">
      <div className="flex items-center">
        {/* Badges */}
        <div className="shrink-0 flex items-center border-r border-border/30">
          {/* Fear & Greed badge */}
          {fearGreed && (
            <div className="px-2.5 py-1 border-r border-border/20 flex items-center gap-1">
              <span className="text-[9px] text-muted-foreground">F&G</span>
              <span className={cn(
                "text-xs font-bold font-mono",
                (fearGreed.score ?? 50) > 55 ? "text-emerald-400" :
                (fearGreed.score ?? 50) < 45 ? "text-red-400" : "text-yellow-400"
              )}>
                {(fearGreed.score ?? 50).toFixed(0)}
              </span>
            </div>
          )}
          {/* VIX badge */}
          {vix && vix.value != null && (
            <div className="px-2.5 py-1 flex items-center gap-1">
              <span className="text-[9px] text-muted-foreground">VIX</span>
              <span className={cn(
                "text-xs font-bold font-mono",
                vix.status === 'LOW' ? "text-emerald-400" :
                vix.status === 'MODERATE' ? "text-yellow-400" :
                vix.status === 'HIGH' ? "text-orange-400" : "text-red-400"
              )}>
                {vix.value.toFixed(1)}
              </span>
            </div>
          )}
        </div>

        {/* Scrolling ticker */}
        <div className="overflow-hidden flex-1">
          <div className="flex animate-scroll-left whitespace-nowrap py-1.5">
            {[...allItems, ...allItems].map((item, i) => (
              <div key={`${item.symbol}-${i}`} className="inline-flex items-center gap-1.5 px-3 border-r border-border/20">
                <span className="text-[10px] text-muted-foreground">{item.display}</span>
                <span className="text-xs font-mono text-foreground">
                  {item.price != null ? item.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : 'N/A'}
                </span>
                <span className={cn(
                  "text-[10px] font-mono",
                  item.change > 0 ? "text-emerald-400" : item.change < 0 ? "text-red-400" : "text-muted-foreground"
                )}>
                  {(item.change ?? 0) > 0 ? '+' : ''}{(item.change ?? 0).toFixed(2)}%
                </span>
                {item.sparkline?.length > 1 && (
                  <MiniSparkline data={item.sparkline} change={item.change} width={36} height={12} />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
