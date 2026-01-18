import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAppStore } from '@/store/appStore';
import { Share2 } from 'lucide-react';

export function NetworkGraph() {
    const { currentTicker, marketHeatmap } = useAppStore();

    // Simple mock network visualization showing current ticker as central node
    // and others as satellites. Real implementation would use D3 or Recharts network logic.

    // Filter out current ticker from heatmap to show as related nodes
    const related = marketHeatmap.filter(t => t.ticker !== currentTicker).slice(0, 4);

    return (
        <Card className="glass-card h-full">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Share2 className="h-4 w-4 text-primary" />
                    Related Vectors
                </CardTitle>
            </CardHeader>
            <CardContent className="flex justify-center items-center py-4">
                <div className="relative w-48 h-48">
                    {/* Center Node (Current) */}
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 flex flex-col items-center">
                        <div className="w-16 h-16 rounded-full bg-primary/20 border-2 border-primary flex items-center justify-center shadow-[0_0_15px_rgba(var(--primary),0.3)] animate-pulse-slow">
                            <span className="font-bold text-xs">{currentTicker}</span>
                        </div>
                    </div>

                    {/* Satellite Nodes */}
                    {related.map((item, i) => {
                        const angle = (i * (360 / related.length)) * (Math.PI / 180);
                        const radius = 80;
                        const x = Math.cos(angle) * radius;
                        const y = Math.sin(angle) * radius;

                        return (
                            <div
                                key={item.ticker}
                                className="absolute top-1/2 left-1/2 transition-all duration-1000"
                                style={{ transform: `translate(${x}px, ${y}px) translate(-50%, -50%)` }}
                            >
                                {/* Connection Line */}
                                <svg className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 pointer-events-none" style={{ left: `${-x}px`, top: `${-y}px` }}>
                                    <line x1="50%" y1="50%" x2={96 + x} y2={96 + y} stroke="currentColor" className="text-border/40" strokeWidth="1" />
                                </svg>

                                <div className="w-10 h-10 rounded-full bg-secondary border border-border flex items-center justify-center text-[10px] font-mono hover:scale-110 transition-transform cursor-pointer">
                                    {item.ticker}
                                </div>
                            </div>
                        );
                    })}

                    {related.length === 0 && (
                        <div className="text-xs text-muted-foreground absolute top-10 left-10">
                            Loading graph...
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
