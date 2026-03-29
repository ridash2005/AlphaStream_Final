import { useAppStore } from '@/store/appStore';
import { cn } from '@/lib/utils';

/**
 * Bloomberg-style scrolling ticker strip showing recent analysis results.
 * Sits below the header as a live data ribbon.
 */
export function PerformanceTicker() {
    const { recommendationHistory, marketHeatmap } = useAppStore();

    // Combine data from history and heatmap
    const items: { ticker: string; label: string; value: string; positive: boolean }[] = [];

    for (const rec of recommendationHistory.slice(0, 6)) {
        items.push({
            ticker: rec.ticker,
            label: rec.recommendation,
            value: `${(rec.confidence ?? 0).toFixed(0)}%`,
            positive: rec.recommendation === 'BUY',
        });
    }

    for (const h of marketHeatmap.slice(0, 8)) {
        if (!items.find((i) => i.ticker === h.ticker)) {
            items.push({
                ticker: h.ticker,
                label: h.score > 0 ? 'BULL' : h.score < 0 ? 'BEAR' : 'FLAT',
                value: `${((h.score ?? 0) * 100).toFixed(0)}%`,
                positive: h.score > 0,
            });
        }
    }

    if (items.length === 0) return null;

    // Duplicate for seamless scroll
    const doubled = [...items, ...items];

    return (
        <div className="w-full overflow-hidden bg-black/30 border-b border-border/30 h-7 flex items-center shrink-0">
            <div className="flex animate-scroll-left whitespace-nowrap gap-6 px-4">
                {doubled.map((item, i) => (
                    <span key={i} className="inline-flex items-center gap-1.5 text-[11px] font-mono">
                        <span className="font-bold text-foreground/90">{item.ticker}</span>
                        <span className={cn(
                            'font-semibold',
                            item.positive ? 'text-emerald-400' : 'text-red-400'
                        )}>
                            {item.label}
                        </span>
                        <span className="text-muted-foreground">{item.value}</span>
                        <span className="text-border/40 mx-1">|</span>
                    </span>
                ))}
            </div>
        </div>
    );
}
