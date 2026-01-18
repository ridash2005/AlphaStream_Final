import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAppStore } from '@/store/appStore';
import { Users, TrendingUp, TrendingDown, AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InsiderData {
    ticker: string;
    period_days: number;
    insider_score: number;
    sentiment: 'BEARISH' | 'NEUTRAL' | 'BULLISH';
    total_buy_value: number;
    total_sell_value: number;
    key_transactions: string[];
    summary: string;
}

export function InsiderActivity() {
    const { currentTicker } = useAppStore();
    const [data, setData] = useState<InsiderData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchInsiderData = async () => {
        if (!currentTicker) return;

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`http://localhost:8000/insider/${currentTicker}`);
            if (!response.ok) throw new Error('Failed to fetch insider data');
            const result = await response.json();
            setData(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInsiderData();
    }, [currentTicker]);

    const getSentimentColor = (sentiment: string) => {
        switch (sentiment) {
            case 'BULLISH': return 'text-emerald-400 bg-emerald-500/20';
            case 'BEARISH': return 'text-red-400 bg-red-500/20';
            default: return 'text-yellow-400 bg-yellow-500/20';
        }
    };

    const getScoreColor = (score: number) => {
        if (score > 0.3) return 'text-emerald-400';
        if (score < -0.3) return 'text-red-400';
        return 'text-yellow-400';
    };

    return (
        <Card className="glass-card">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-primary" />
                        Insider Activity
                    </div>
                    <button
                        onClick={fetchInsiderData}
                        className="p-1 hover:bg-white/10 rounded transition-colors"
                        disabled={loading}
                    >
                        <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
                    </button>
                </CardTitle>
            </CardHeader>
            <CardContent>
                {loading && (
                    <div className="text-xs text-muted-foreground text-center py-4">
                        <RefreshCw className="h-4 w-4 animate-spin mx-auto mb-2" />
                        Analyzing SEC Form 4 filings...
                    </div>
                )}

                {error && (
                    <div className="text-xs text-red-400 text-center py-4 flex flex-col items-center">
                        <AlertCircle className="h-4 w-4 mb-2" />
                        {error}
                    </div>
                )}

                {!loading && !error && data && (
                    <div className="space-y-3">
                        {/* Sentiment Badge */}
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-muted-foreground">Insider Sentiment</span>
                            <Badge className={cn("text-xs", getSentimentColor(data.sentiment))}>
                                {data.sentiment === 'BULLISH' && <TrendingUp className="h-3 w-3 mr-1" />}
                                {data.sentiment === 'BEARISH' && <TrendingDown className="h-3 w-3 mr-1" />}
                                {data.sentiment}
                            </Badge>
                        </div>

                        {/* Score */}
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-muted-foreground">Insider Score</span>
                            <span className={cn("font-mono text-sm font-bold", getScoreColor(data.insider_score))}>
                                {data.insider_score > 0 ? '+' : ''}{data.insider_score.toFixed(2)}
                            </span>
                        </div>

                        {/* Buy/Sell Values */}
                        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10">
                            <div className="text-center">
                                <div className="text-xs text-muted-foreground">Total Buys</div>
                                <div className="text-sm font-bold text-emerald-400">
                                    ${(data.total_buy_value / 1000000).toFixed(2)}M
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-xs text-muted-foreground">Total Sells</div>
                                <div className="text-sm font-bold text-red-400">
                                    ${(data.total_sell_value / 1000000).toFixed(2)}M
                                </div>
                            </div>
                        </div>

                        {/* Key Transactions */}
                        {data.key_transactions.length > 0 && (
                            <div className="pt-2 border-t border-white/10">
                                <div className="text-xs text-muted-foreground mb-1">Recent Activity</div>
                                <div className="space-y-1">
                                    {data.key_transactions.slice(0, 3).map((trans, i) => (
                                        <div key={i} className="text-xs text-slate-300 truncate">
                                            • {trans}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {!loading && !error && !data && (
                    <div className="text-xs text-muted-foreground text-center py-4">
                        <Users className="h-8 w-8 mx-auto mb-2 opacity-20" />
                        No insider data available
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
