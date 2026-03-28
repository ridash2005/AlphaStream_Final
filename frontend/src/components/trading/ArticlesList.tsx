import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { useAppStore } from '@/store/appStore';
import { ExternalLink, FileText, AlertTriangle, ShieldAlert } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip } from 'recharts';

const THREAT_STYLES = {
    critical: { color: 'bg-red-500/20 text-red-400', icon: ShieldAlert },
    warning: { color: 'bg-amber-500/20 text-amber-400', icon: AlertTriangle },
    info: { color: 'bg-secondary/50 text-muted-foreground', icon: null },
} as const;

export function ArticlesList() {
    const { articles, isLoading } = useAppStore();

    if (isLoading) {
        return (
            <Card className="glass-card">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Related News
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="space-y-2">
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-3 w-3/4" />
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (articles.length === 0) {
        return (
            <Card className="glass-card">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Related News
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground">
                        No articles found. Search for a ticker to see related news.
                    </p>
                </CardContent>
            </Card>
        );
    }

    const sentimentBuckets = [
        { name: 'Bullish', value: articles.filter(a => (a.similarity ?? 0) >= 0.65).length, color: '#22c55e' },
        { name: 'Neutral', value: articles.filter(a => (a.similarity ?? 0) >= 0.40 && (a.similarity ?? 0) < 0.65).length, color: '#eab308' },
        { name: 'Bearish', value: articles.filter(a => (a.similarity ?? 0) < 0.40).length, color: '#ef4444' },
    ].filter(b => b.value > 0);

    const sortedArticles = [...articles].sort((a, b) => {
        const threatOrder: Record<string, number> = { critical: 0, warning: 1, info: 2 };
        const ta = threatOrder[a.threat_level ?? 'info'];
        const tb = threatOrder[b.threat_level ?? 'info'];
        if (ta !== tb) return ta - tb;
        return (b.similarity ?? 0) - (a.similarity ?? 0);
    });

    return (
        <Card className="glass-card animate-slide-up">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    Related News
                    <span className="text-muted-foreground font-normal">({articles.length})</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                {articles.length > 0 && sentimentBuckets.length > 0 && (
                    <div className="flex items-center gap-3 mb-3 px-4">
                        <PieChart width={80} height={60}>
                            <Pie data={sentimentBuckets} dataKey="value" outerRadius={28} innerRadius={14} startAngle={90} endAngle={-270} strokeWidth={0}>
                                {sentimentBuckets.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                            </Pie>
                            <Tooltip formatter={(v: number, name: string) => [v, name]} contentStyle={{ background: '#0a0a1a', border: '1px solid #333', fontSize: 10 }} />
                        </PieChart>
                        <div className="text-[10px] space-y-0.5">
                            {sentimentBuckets.map(b => (
                                <div key={b.name} className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: b.color }} />
                                    <span className="text-muted-foreground">{b.name}: {b.value}</span>
                                </div>
                            ))}
                        </div>
                        <div className="text-[10px] text-muted-foreground ml-auto">Sentiment Mix</div>
                    </div>
                )}
                <ScrollArea className="h-[500px] px-4 pb-4">
                    <div className="space-y-3">
                        {sortedArticles.map((article, i) => (
                            <div
                                key={i}
                                className="p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors cursor-pointer group"
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <h4 className="text-sm font-medium leading-snug group-hover:text-primary transition-colors">
                                        {article.title}
                                    </h4>
                                    <div className="flex items-center gap-1 shrink-0">
                                        {article.threat_level && article.threat_level !== 'info' && (() => {
                                            const style = THREAT_STYLES[article.threat_level] || THREAT_STYLES.info;
                                            const Icon = style.icon;
                                            return (
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded flex items-center gap-0.5 shrink-0 ${style.color}`}>
                                                    {Icon && <Icon className="h-2.5 w-2.5" />}
                                                    {article.threat_level}
                                                </span>
                                            );
                                        })()}
                                        <ExternalLink className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                </div>
                                {article.threat_category && article.threat_category !== 'general' && (
                                    <span className="text-[10px] text-muted-foreground/70 block mt-0.5">{article.threat_category}</span>
                                )}
                                <div className="flex items-center gap-2 mt-1.5">
                                    <span className="text-xs text-muted-foreground">{article.source}</span>
                                    <span className="text-xs text-muted-foreground">•</span>
                                    <span className="text-xs font-mono text-primary/70">
                                        {(article.similarity * 100).toFixed(1)}% match
                                    </span>
                                    {article.published_at && (
                                        <>
                                            <span className="text-xs text-muted-foreground">•</span>
                                            <span className="text-xs text-muted-foreground">
                                                {new Date(article.published_at).toLocaleString('en-IN', {
                                                    timeZone: 'Asia/Kolkata',
                                                    day: '2-digit', month: 'short',
                                                    hour: '2-digit', minute: '2-digit'
                                                })}
                                            </span>
                                        </>
                                    )}
                                </div>
                                <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                                    {article.snippet}
                                </p>
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
