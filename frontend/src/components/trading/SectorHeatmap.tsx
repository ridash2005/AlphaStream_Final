import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { apiService } from '@/services/api';
import { LayoutGrid } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SectorData {
    sector: string;
    tickers: string[];
    avgScore: number;
}

export function SectorHeatmap() {
    const [sectors, setSectors] = useState<SectorData[]>([]);

    useEffect(() => {
        const load = async () => {
            try {
                // Use screener (has sector field) rather than radar (no sector field)
                const res = await apiService.getScreener({ limit: 50 });
                const stocks: any[] = res?.stocks || [];
                if (stocks.length === 0) return;

                // Group by sector
                const map = new Map<string, { scores: number[]; tickers: string[] }>();
                for (const stock of stocks) {
                    const sector = stock.sector || 'Other';
                    if (!map.has(sector)) map.set(sector, { scores: [], tickers: [] });
                    const entry = map.get(sector)!;
                    entry.scores.push(stock.latest_alpha_score ?? 50);
                    entry.tickers.push(stock.ticker);
                }

                const result: SectorData[] = [];
                map.forEach((v, k) => {
                    result.push({
                        sector: k,
                        tickers: v.tickers.slice(0, 4),
                        avgScore: v.scores.reduce((a, b) => a + b, 0) / v.scores.length,
                    });
                });
                result.sort((a, b) => b.avgScore - a.avgScore);
                setSectors(result.slice(0, 8));
            } catch { /* graceful */ }
        };
        load();
    }, []);

    const getColor = (score: number) => {
        if (score >= 70) return 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400';
        if (score >= 50) return 'bg-blue-500/15 border-blue-500/25 text-blue-400';
        if (score >= 30) return 'bg-amber-500/15 border-amber-500/25 text-amber-400';
        return 'bg-red-500/15 border-red-500/25 text-red-400';
    };

    return (
        <Card className="glass-card">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <LayoutGrid className="h-4 w-4 text-primary" />
                    Sector Heatmap
                </CardTitle>
            </CardHeader>
            <CardContent>
                {sectors.length === 0 ? (
                    <div className="h-[200px] flex items-center justify-center text-xs text-muted-foreground">
                        Loading sector data...
                    </div>
                ) : (
                    <div className="grid grid-cols-2 gap-2">
                        {sectors.map((s) => (
                            <div
                                key={s.sector}
                                className={cn(
                                    "p-2.5 rounded-lg border transition-all hover:scale-[1.02]",
                                    getColor(s.avgScore)
                                )}
                            >
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-[11px] font-semibold truncate">{s.sector}</span>
                                    <span className="text-[10px] font-mono font-bold">{s.avgScore.toFixed(0)}</span>
                                </div>
                                <div className="flex flex-wrap gap-1">
                                    {s.tickers.map((t) => (
                                        <span key={t} className="text-[9px] px-1 py-0.5 rounded bg-black/20 font-mono">{t}</span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
