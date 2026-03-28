import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';
import { useAppStore } from '@/store/appStore';

const DAYS_OPTIONS = [7, 30, 90];

// Categorize filing based on category name
const getFilingType = (category: string = '') => {
    const cat = category.toLowerCase();
    if (cat.includes('result') || cat.includes('financial')) return { label: 'Results', color: 'bg-blue-500/20 text-blue-400' };
    if (cat.includes('agm') || cat.includes('egm') || cat.includes('general meeting')) return { label: 'AGM/EGM', color: 'bg-amber-500/20 text-amber-400' };
    if (cat.includes('board') || cat.includes('meeting')) return { label: 'Board', color: 'bg-purple-500/20 text-purple-400' };
    if (cat.includes('dividend')) return { label: 'Dividend', color: 'bg-emerald-500/20 text-emerald-400' };
    if (cat.includes('bonus') || cat.includes('split')) return { label: 'Bonus/Split', color: 'bg-pink-500/20 text-pink-400' };
    return { label: 'Filing', color: 'bg-secondary/50 text-muted-foreground' };
};

export function CorporateFilings() {
    const { currentTicker } = useAppStore();
    const [filings, setFilings] = useState<any[]>([]);
    const [days, setDays] = useState(30);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);

    useEffect(() => {
        setLoading(true);
        setError(false);
        apiService.getFilings(currentTicker, days)
            .then(data => {
                // Handle both array and {data: [...]} shapes
                const arr = Array.isArray(data) ? data : (data?.data || data?.filings || []);
                setFilings(arr);
            })
            .catch(() => setError(true))
            .finally(() => setLoading(false));
    }, [currentTicker, days]);

    return (
        <Card className="glass-card">
            <CardHeader className="pb-1">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <FileText className="h-4 w-4 text-primary" />
                        Corporate Filings — {currentTicker}
                    </CardTitle>
                    <div className="flex gap-1">
                        {DAYS_OPTIONS.map(d => (
                            <button key={d} onClick={() => setDays(d)}
                                className={cn("text-[10px] px-2 py-0.5 rounded transition-colors",
                                    days === d ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground")}>
                                {d}d
                            </button>
                        ))}
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                {loading && <div className="text-xs text-muted-foreground text-center py-4 animate-pulse">Loading filings...</div>}
                {error && <div className="text-xs text-muted-foreground text-center py-4">Filings data unavailable</div>}
                {!loading && !error && filings.length === 0 && (
                    <div className="text-xs text-muted-foreground text-center py-4">No filings in last {days} days</div>
                )}
                {!loading && !error && filings.length > 0 && (
                    <div className="space-y-2 max-h-72 overflow-y-auto scrollbar-hide">
                        {filings.slice(0, 20).map((f: any, i: number) => {
                            // BSE field names — from data["Table"] in BSE API response
                            const subject = f.NEWSSUB || f.HEADLINE || f.subject || f.title || 'Filing';
                            const category = f.CATEGORYNAME || f.category || '';
                            const dateStr = f.DT_TM || f.date || f.DATETIME;
                            const { label, color } = getFilingType(category);

                            const date = dateStr ? new Date(dateStr).toLocaleDateString('en-IN', {
                                timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short'
                            }) : '—';

                            return (
                                <div key={i} className="flex items-start gap-2 text-xs group">
                                    <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0 mt-0.5", color)}>
                                        {label}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-foreground line-clamp-2 leading-tight">{subject}</p>
                                        <span className="text-muted-foreground text-[10px]">{date}</span>
                                    </div>
                                    {(f.NSURL || f.url) && (
                                        <a href={f.NSURL || f.url} target="_blank" rel="noopener noreferrer"
                                            className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <ExternalLink className="h-3 w-3 text-muted-foreground hover:text-primary" />
                                        </a>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
