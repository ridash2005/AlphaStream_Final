import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAppStore } from '@/store/appStore';
import { RecommendationBadge, LatencyIndicator } from './Indicators';
import { History, Clock } from 'lucide-react';

export function HistoryPanel() {
    const { recommendationHistory } = useAppStore();

    if (recommendationHistory.length === 0) {
        return (
            <Card className="glass-card h-full">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                        <History className="h-4 w-4" />
                        Analysis History
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground">
                        Your recent analyses will appear here.
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="glass-card h-full">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                    <History className="h-4 w-4 text-primary" />
                    Analysis History
                </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                <ScrollArea className="h-[200px] px-4 pb-4">
                    <div className="space-y-2">
                        {recommendationHistory.map((rec, i) => (
                            <div
                                key={`${rec.ticker}-${rec.timestamp}-${i}`}
                                className="flex items-center justify-between p-2 rounded-lg bg-secondary/20 hover:bg-secondary/40 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <span className="font-mono font-bold text-sm">{rec.ticker}</span>
                                    <RecommendationBadge recommendation={rec.recommendation} size="sm" />
                                </div>
                                <div className="flex items-center gap-3">
                                    <LatencyIndicator latency={rec.latency_ms} />
                                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                                        <Clock className="h-3 w-3" />
                                        {new Date(rec.timestamp).toLocaleTimeString()}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
