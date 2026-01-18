import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/store/appStore';
import { FileText, Download, Loader2, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ReportResult {
    report_path: string;
    ticker: string;
    generated_at: string;
    recommendation: string;
    confidence: number;
}

export function ReportDownload() {
    const { currentTicker } = useAppStore();
    const [generating, setGenerating] = useState(false);
    const [result, setResult] = useState<ReportResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    const generateReport = async () => {
        if (!currentTicker) return;

        setGenerating(true);
        setError(null);
        setResult(null);

        try {
            const response = await fetch(`http://localhost:8000/report/${currentTicker}`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('Failed to generate report');

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            setResult(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Report generation failed');
        } finally {
            setGenerating(false);
        }
    };

    const getRecommendationColor = (rec: string) => {
        switch (rec) {
            case 'BUY': return 'text-emerald-400';
            case 'SELL': return 'text-red-400';
            default: return 'text-yellow-400';
        }
    };

    return (
        <Card className="glass-card">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    Full Analysis Report
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-3">
                    {/* Generate Button */}
                    <Button
                        onClick={generateReport}
                        disabled={generating || !currentTicker}
                        className={cn(
                            "w-full transition-all duration-300",
                            generating
                                ? "bg-primary/50"
                                : "bg-gradient-to-r from-primary to-purple-600 hover:from-primary/80 hover:to-purple-500"
                        )}
                    >
                        {generating ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Generating PDF...
                            </>
                        ) : (
                            <>
                                <Download className="h-4 w-4 mr-2" />
                                Generate Report for {currentTicker}
                            </>
                        )}
                    </Button>

                    {/* Error State */}
                    {error && (
                        <div className="text-xs text-red-400 text-center py-2 px-3 bg-red-500/10 rounded-md">
                            {error}
                        </div>
                    )}

                    {/* Success State */}
                    {result && (
                        <div className="p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                            <div className="flex items-center gap-2 text-emerald-400 mb-2">
                                <CheckCircle className="h-4 w-4" />
                                <span className="text-sm font-medium">Report Generated!</span>
                            </div>

                            <div className="space-y-1 text-xs">
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Ticker:</span>
                                    <span className="font-mono">{result.ticker}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Recommendation:</span>
                                    <span className={cn("font-bold", getRecommendationColor(result.recommendation))}>
                                        {result.recommendation}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Confidence:</span>
                                    <span>{result.confidence.toFixed(1)}%</span>
                                </div>
                            </div>

                            <div className="mt-3 pt-2 border-t border-emerald-500/20">
                                <div className="text-xs text-muted-foreground mb-1">File saved to:</div>
                                <code className="text-xs text-slate-300 break-all bg-black/30 px-2 py-1 rounded block">
                                    {result.report_path}
                                </code>
                            </div>
                        </div>
                    )}

                    {/* Description */}
                    <div className="text-xs text-muted-foreground text-center">
                        Generates a comprehensive PDF report with:
                        <ul className="mt-1 space-y-0.5">
                            <li>• Trading recommendation & confidence</li>
                            <li>• Price chart with 24h highlight</li>
                            <li>• Insider trading activity</li>
                            <li>• Technical & risk analysis</li>
                        </ul>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
