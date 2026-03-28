import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAppStore } from '@/store/appStore';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, ComposedChart } from 'recharts';
import { Activity } from 'lucide-react';

export function HistoryChart() {
    const { recommendationHistory } = useAppStore();

    const data = [...recommendationHistory].reverse().map((rec, i) => ({
        idx: i + 1,
        time: new Date(rec.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        confidence: rec.confidence,
        sentiment: ((rec.sentiment_score + 1) / 2) * 100, // normalize -1..1 → 0..100
        technical: ((rec.technical_score + 1) / 2) * 100,
        signal: rec.recommendation === 'BUY' ? 80 : rec.recommendation === 'SELL' ? 20 : 50,
    }));

    if (data.length < 2) {
        return (
            <Card className="glass-card">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Activity className="h-4 w-4 text-primary" />
                        Signal History
                    </CardTitle>
                </CardHeader>
                <CardContent className="h-[180px] flex items-center justify-center text-xs text-muted-foreground">
                    Analyze 2+ tickers to see trend
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="glass-card">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Activity className="h-4 w-4 text-primary" />
                    Signal History ({data.length} analyses)
                </CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={180}>
                    <ComposedChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -15 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 9 }} />
                        <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 9 }} />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333', borderRadius: 8, fontSize: 11 }}
                            formatter={(v: number, name: string) => [`${v.toFixed(0)}%`, name.charAt(0).toUpperCase() + name.slice(1)]}
                        />
                        <Area type="monotone" dataKey="confidence" fill="#8b5cf6" fillOpacity={0.1} stroke="none" />
                        <Line type="monotone" dataKey="confidence" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3 }} name="Confidence" />
                        <Line type="monotone" dataKey="sentiment" stroke="#10b981" strokeWidth={1.5} dot={{ r: 2 }} strokeDasharray="4 2" name="Sentiment" />
                        <Line type="monotone" dataKey="technical" stroke="#3b82f6" strokeWidth={1.5} dot={{ r: 2 }} strokeDasharray="4 2" name="Technical" />
                    </ComposedChart>
                </ResponsiveContainer>
                <div className="flex justify-center gap-4 mt-1 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500 inline-block" />Confidence</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />Sentiment</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />Technical</span>
                </div>
            </CardContent>
        </Card>
    );
}
