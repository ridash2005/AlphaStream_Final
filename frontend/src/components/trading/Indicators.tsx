import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface RecommendationBadgeProps {
    recommendation: 'BUY' | 'HOLD' | 'SELL';
    size?: 'sm' | 'md' | 'lg';
}

export function RecommendationBadge({ recommendation, size = 'md' }: RecommendationBadgeProps) {
    const sizeClasses = {
        sm: 'text-xs px-2 py-0.5',
        md: 'text-sm px-3 py-1',
        lg: 'text-lg px-4 py-2 font-bold',
    };

    const colorClasses = {
        BUY: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        HOLD: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
        SELL: 'bg-red-500/20 text-red-400 border-red-500/30',
    };

    const Icon = {
        BUY: TrendingUp,
        HOLD: Minus,
        SELL: TrendingDown,
    }[recommendation];

    return (
        <div
            className={cn(
                'inline-flex items-center gap-1.5 rounded-md border font-semibold uppercase tracking-wider',
                sizeClasses[size],
                colorClasses[recommendation]
            )}
        >
            <Icon className="h-4 w-4" />
            {recommendation}
        </div>
    );
}

interface SentimentBadgeProps {
    sentiment: 'BEARISH' | 'NEUTRAL' | 'BULLISH';
    score: number;
}

export function SentimentBadge({ sentiment, score }: SentimentBadgeProps) {
    const colorClasses = {
        BULLISH: 'text-emerald-400',
        NEUTRAL: 'text-amber-400',
        BEARISH: 'text-red-400',
    };

    return (
        <div className="flex items-center gap-2">
            <span className={cn('font-medium', colorClasses[sentiment])}>{sentiment}</span>
            <span className="text-muted-foreground">({score.toFixed(2)})</span>
        </div>
    );
}

interface ConfidenceBarProps {
    confidence: number;
    recommendation: 'BUY' | 'HOLD' | 'SELL';
}

export function ConfidenceBar({ confidence, recommendation }: ConfidenceBarProps) {
    const colorClasses = {
        BUY: 'bg-emerald-500',
        HOLD: 'bg-amber-500',
        SELL: 'bg-red-500',
    };

    return (
        <div className="w-full">
            <div className="flex justify-between text-xs mb-1">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-mono">{confidence.toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
                <div
                    className={cn('h-full rounded-full transition-all duration-500', colorClasses[recommendation])}
                    style={{ width: `${Math.min(100, confidence)}%` }}
                />
            </div>
        </div>
    );
}

interface LatencyIndicatorProps {
    latency: number;
}

export function LatencyIndicator({ latency }: LatencyIndicatorProps) {
    const getColor = () => {
        if (latency < 500) return 'text-emerald-400';
        if (latency < 1000) return 'text-amber-400';
        return 'text-red-400';
    };

    return (
        <div className="flex items-center gap-1 text-xs">
            <div className={cn('h-2 w-2 rounded-full animate-pulse', getColor().replace('text-', 'bg-'))} />
            <span className={cn('font-mono', getColor())}>{latency.toFixed(0)}ms</span>
        </div>
    );
}
