import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAppStore } from '@/store/appStore';
import { cn } from '@/lib/utils';
import { BarChart2, Loader2 } from 'lucide-react';
import { apiService } from '@/services/api';

export function MarketHeatmap() {
    const { marketHeatmap } = useAppStore();
    const [loading, setLoading] = useState(true);

    // Fetch initial heatmap data on mount
    useEffect(() => {
        const fetchInitialHeatmap = async () => {
            try {
                const response = await apiService.getMarketHeatmap();
                if (response.data && response.data.length > 0) {
                    useAppStore.setState({ marketHeatmap: response.data });
                }
            } catch {
                // Will show empty state; WebSocket may populate later
            } finally {
                setLoading(false);
            }
        };
        fetchInitialHeatmap();
    }, []);

    // Sort by score
    const sortedData = [...marketHeatmap].sort((a, b) => b.score - a.score);

    return (
        <Card className="glass-card h-full">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <BarChart2 className="h-4 w-4 text-primary" />
                    Live Market Sentiment
                </CardTitle>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="flex items-center justify-center py-8 gap-2 text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-xs">Loading market data...</span>
                    </div>
                ) : sortedData.length === 0 ? (
                    <div className="text-xs text-muted-foreground text-center py-4">
                        Waiting for live market data...
                    </div>
                ) : (
                    <ScrollArea className="h-[300px] pr-4">
                        <div className="grid grid-cols-2 gap-2">
                            {sortedData.map((item) => (
                                <div
                                    key={item.ticker}
                                    className={cn(
                                        "p-3 rounded-md flex justify-between items-center transition-all duration-500",
                                        item.score > 0 ? "bg-emerald-500/10 border border-emerald-500/20" :
                                            item.score < 0 ? "bg-red-500/10 border border-red-500/20" :
                                                "bg-secondary/50 border border-secondary"
                                    )}
                                >
                                    <span className="font-mono font-bold text-sm">{item.ticker}</span>
                                    <span className={cn(
                                        "text-xs font-medium",
                                        item.score > 0 ? "text-emerald-400" :
                                            item.score < 0 ? "text-red-400" : "text-muted-foreground"
                                    )}>
                                        {(item.score * 100).toFixed(0)}%
                                    </span>
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                )}
            </CardContent>
        </Card>
    );
}
