import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { apiService } from '@/services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { ArrowRightLeft, RefreshCw, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FlowDay {
    date: string;
    fii_net: number;
    dii_net: number;
}

export function FlowChart() {
    const [data, setData] = useState<FlowDay[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const fetchFlows = async () => {
        setLoading(true);
        setError(false);
        try {
            const resp = await apiService.getFlows(30);
            const flows = resp.flows || resp.data || resp;
            if (Array.isArray(flows)) {
                // API may return per-category rows (one DII row + one FII row per date)
                // or pre-merged rows with fii_net_cr / dii_net_cr fields.
                const isSplit = flows.length > 0 && ('category' in flows[0] || 'netValue' in flows[0]);

                // NSE returns dates as "DD-Mon-YYYY" (e.g. "29-Mar-2026") or ISO "YYYY-MM-DD".
                // Numbers may be comma-formatted strings like "1,234.56".
                const fmtDate = (raw: string): string => {
                    if (!raw) return raw;
                    if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(5);    // ISO → "MM-DD"
                    if (/^\d{2}-[A-Za-z]{3}-\d{4}/.test(raw)) return raw.slice(0, 6); // NSE → "DD-Mon"
                    return raw.slice(0, 5) || raw;
                };
                const parseNum = (v: any): number => parseFloat(String(v ?? 0).replace(/,/g, '')) || 0;

                let merged: FlowDay[];
                if (isSplit) {
                    // Group by date, merge FII and DII into a single row
                    const byDate: Record<string, FlowDay> = {};
                    for (const f of flows) {
                        const date = fmtDate(f.date || f.Date || '');
                        if (!date) continue;
                        if (!byDate[date]) byDate[date] = { date, fii_net: 0, dii_net: 0 };
                        const net = parseNum(f.netValue ?? f.net);
                        const cat: string = (f.category || '').toLowerCase();
                        if (cat.includes('fii') || cat.includes('fpi')) {
                            byDate[date].fii_net = net;
                        } else if (cat.includes('dii')) {
                            byDate[date].dii_net = net;
                        }
                    }
                    merged = Object.values(byDate);
                } else {
                    merged = flows.map((f: any) => ({
                        date: fmtDate(f.date || f.Date || ''),
                        fii_net: f.fii_net_cr != null ? parseNum(f.fii_net_cr)
                            : parseNum(f.fii_buy_cr) - parseNum(f.fii_sell_cr),
                        dii_net: f.dii_net_cr != null ? parseNum(f.dii_net_cr)
                            : parseNum(f.dii_buy_cr) - parseNum(f.dii_sell_cr),
                    })).filter((r: FlowDay) => r.date);
                }
                setData(merged.slice(-20));
            }
        } catch {
            setError(true);
        }
        setLoading(false);
    };

    useEffect(() => { fetchFlows(); }, []);

    return (
        <Card className="glass-card">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <ArrowRightLeft className="h-4 w-4 text-primary" />
                        FII / DII Net Flows (₹ Cr)
                    </div>
                    <button onClick={fetchFlows} className="p-1 hover:bg-white/10 rounded transition-colors" disabled={loading}>
                        <RefreshCw className={cn("h-3 w-3", loading && "animate-spin")} />
                    </button>
                </CardTitle>
            </CardHeader>
            <CardContent>
                {data.length === 0 ? (
                    <div className="h-[200px] flex items-center justify-center text-xs text-muted-foreground">
                        {loading ? 'Loading flow data...' : error ? (
                            <div className="flex flex-col items-center gap-1">
                                <AlertCircle className="h-4 w-4 text-red-400 opacity-60" />
                                Failed to load FII/DII data
                            </div>
                        ) : 'No FII/DII data available'}
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={data} barGap={1} margin={{ top: 5, right: 5, bottom: 0, left: -10 }}>
                            <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 9 }} interval="preserveStartEnd" />
                            <YAxis tick={{ fill: '#64748b', fontSize: 9 }} tickFormatter={(v) => `${v > 0 ? '+' : ''}${(v / 1000).toFixed(1)}k`} />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333', borderRadius: 8, fontSize: 11 }}
                                formatter={(v: number | undefined, name: string | undefined) => [`₹${(v ?? 0).toFixed(0)} Cr`, name === 'fii_net' ? 'FII Net' : 'DII Net']}
                            />
                            <ReferenceLine y={0} stroke="#333" strokeDasharray="3 3" />
                            <Bar dataKey="fii_net" name="FII Net" radius={[2, 2, 0, 0]} maxBarSize={12}>
                                {data.map((entry, i) => (
                                    <Cell key={i} fill={entry.fii_net >= 0 ? '#10b981' : '#ef4444'} fillOpacity={0.8} />
                                ))}
                            </Bar>
                            <Bar dataKey="dii_net" name="DII Net" radius={[2, 2, 0, 0]} maxBarSize={12}>
                                {data.map((entry, i) => (
                                    <Cell key={i} fill={entry.dii_net >= 0 ? '#3b82f6' : '#f59e0b'} fillOpacity={0.6} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                )}
                <div className="flex justify-center gap-4 mt-1 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-emerald-500 inline-block" />FII Buy</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-500 inline-block" />FII Sell</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-blue-500 inline-block" />DII Buy</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-amber-500 inline-block" />DII Sell</span>
                </div>
            </CardContent>
        </Card>
    );
}
