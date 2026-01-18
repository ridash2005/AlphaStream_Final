import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { useAppStore } from '@/store/appStore';
import { ExternalLink, FileText } from 'lucide-react';

export function ArticlesList() {
    const { articles, isLoading, currentTicker } = useAppStore();

    if (isLoading) {
        return (
            <Card className="glass-card h-full">
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
            <Card className="glass-card h-full">
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

    return (
        <Card className="glass-card h-full animate-slide-up">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    Related News
                    <span className="text-muted-foreground font-normal">({articles.length})</span>
                </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                <ScrollArea className="h-[300px] px-4 pb-4">
                    <div className="space-y-3">
                        {articles.map((article, i) => (
                            <div
                                key={i}
                                className="p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors cursor-pointer group"
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <h4 className="text-sm font-medium leading-snug group-hover:text-primary transition-colors">
                                        {article.title}
                                    </h4>
                                    <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                                <div className="flex items-center gap-2 mt-1.5">
                                    <span className="text-xs text-muted-foreground">{article.source}</span>
                                    <span className="text-xs text-muted-foreground">•</span>
                                    <span className="text-xs font-mono text-primary/70">
                                        {(article.similarity * 100).toFixed(1)}% match
                                    </span>
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
