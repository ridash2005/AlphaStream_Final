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
import { Clock, TrendingUp, Shield, Newspaper, Bot, Cpu } from 'lucide-react';

export function RecommendationCard() {
    const { recommendation, isLoading, currentTicker, agentStatus } = useAppStore();

    if (isLoading) {
        return (
            <Card className="glass-card">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Skeleton className="h-6 w-20" />
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 py-8">
                    {agentStatus ? (
                        <div className="flex flex-col items-center justify-center space-y-4 text-center animate-pulse">
                            <div className="p-3 rounded-full bg-primary/10 border border-primary/20">
                                <Bot className="h-8 w-8 text-primary" />
                            </div>
                            <div className="space-y-1">
                                <h3 className="text-lg font-medium text-primary">{agentStatus.agent}</h3>
                                <p className="text-sm text-muted-foreground">{agentStatus.status}</p>
                            </div>
                            <div className="w-full max-w-xs h-1.5 bg-secondary rounded-full overflow-hidden mt-4">
                                <div className="h-full bg-primary animate-progress-indeterminate" />
                            </div>
                        </div>
                    ) : (
                        <>
                            <Skeleton className="h-12 w-32" />
                            <Skeleton className="h-4 w-full" />
                            <Skeleton className="h-4 w-3/4" />
                            <Skeleton className="h-8 w-full" />
                        </>
                    )}
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
                    <div className="flex items-center gap-2">
                        {recommendation.rag_engine && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 flex items-center gap-1">
                                <Cpu className="h-2.5 w-2.5" />
                                {recommendation.rag_engine === 'adaptive' ? 'Adaptive RAG' : 'Manual RAG'}
                            </span>
                        )}
                        <SentimentBadge
                            sentiment={recommendation.sentiment_label}
                            score={recommendation.sentiment_score}
                        />
                    </div>
                </div>

                {/* Confidence bar */}
                <ConfidenceBar
                    confidence={recommendation.confidence}
                    recommendation={recommendation.recommendation}
                />

                {/* Technical & Risk scores */}
                {(recommendation.technical_score !== undefined || recommendation.risk_score !== undefined) && (
                    <div className="flex gap-4 text-xs">
                        {recommendation.technical_score !== undefined && (
                            <div className="flex items-center gap-1.5">
                                <TrendingUp className="h-3 w-3 text-blue-400" />
                                <span className="text-muted-foreground">Technical:</span>
                                <span className={recommendation.technical_score > 0 ? 'text-green-400' : recommendation.technical_score < 0 ? 'text-red-400' : 'text-muted-foreground'}>
                                    {recommendation.technical_score > 0 ? '+' : ''}{recommendation.technical_score.toFixed(2)}
                                </span>
                            </div>
                        )}
                        {recommendation.risk_score !== undefined && (
                            <div className="flex items-center gap-1.5">
                                <Shield className="h-3 w-3 text-amber-400" />
                                <span className="text-muted-foreground">Risk:</span>
                                <span className={recommendation.risk_score < 3 ? 'text-green-400' : recommendation.risk_score > 7 ? 'text-red-400' : 'text-amber-400'}>
                                    {recommendation.risk_score.toFixed(1)}/10
                                </span>
                            </div>
                        )}
                    </div>
                )}

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
