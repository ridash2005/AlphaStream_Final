import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { useAppStore } from '@/store/appStore';
import {
    RecommendationBadge,
    SentimentBadge,
    ConfidenceBar,
    LatencyIndicator,
} from './Indicators';
import { Clock, TrendingUp, Shield, Newspaper } from 'lucide-react';

export function RecommendationCard() {
    const { recommendation, isLoading, currentTicker } = useAppStore();

    if (isLoading) {
        return (
            <Card className="glass-card">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Skeleton className="h-6 w-20" />
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <Skeleton className="h-12 w-32" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-8 w-full" />
                </CardContent>
            </Card>
        );
    }

    if (!recommendation) {
        return (
            <Card className="glass-card">
                <CardHeader>
                    <CardTitle className="text-muted-foreground">No Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground">
                        Enter a ticker symbol above to get real-time trading recommendations.
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="glass-card animate-slide-up">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-3">
                        <span className="text-2xl font-mono font-bold tracking-tight">
                            {recommendation.ticker}
                        </span>
                        <LatencyIndicator latency={recommendation.latency_ms} />
                    </CardTitle>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {new Date(recommendation.timestamp).toLocaleTimeString()}
                    </div>
                </div>
            </CardHeader>

            <CardContent className="space-y-6">
                {/* Main recommendation */}
                <div className="flex items-center justify-between">
                    <RecommendationBadge recommendation={recommendation.recommendation} size="lg" />
                    <SentimentBadge
                        sentiment={recommendation.sentiment_label}
                        score={recommendation.sentiment_score}
                    />
                </div>

                {/* Confidence bar */}
                <ConfidenceBar
                    confidence={recommendation.confidence}
                    recommendation={recommendation.recommendation}
                />

                <Separator className="bg-border/50" />

                {/* Key factors */}
                <div className="space-y-2">
                    <h4 className="text-sm font-medium flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        Key Drivers
                    </h4>
                    <div className="h-[150px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-primary/20 scrollbar-track-transparent">
                        <ul className="space-y-1">
                            {recommendation.key_factors.map((factor, i) => (
                                <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                                    <span className="text-primary mt-1">•</span>
                                    {factor}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                <Separator className="bg-border/50" />

                {/* Sources */}
                <div className="space-y-2">
                    <h4 className="text-sm font-medium flex items-center gap-2">
                        <Newspaper className="h-4 w-4 text-primary" />
                        Sources ({recommendation.sources.length})
                    </h4>
                    <div className="flex flex-wrap gap-1">
                        {recommendation.sources.map((source, i) => (
                            <span
                                key={i}
                                className="text-xs px-2 py-0.5 rounded-full bg-secondary/50 text-muted-foreground"
                            >
                                {source}
                            </span>
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
