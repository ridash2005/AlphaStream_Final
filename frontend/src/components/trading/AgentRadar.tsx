import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAppStore } from '@/store/appStore';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { BrainCircuit } from 'lucide-react';

export function AgentRadar() {
    const { recommendation } = useAppStore();

    if (!recommendation) {
        return (
            <Card className="glass-card h-full">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <BrainCircuit className="h-4 w-4 text-primary" />
                        Multi-Agent Consensus
                    </CardTitle>
                </CardHeader>
                <CardContent className="h-[200px] flex items-center justify-center text-xs text-muted-foreground">
                    Waiting for analysis...
                </CardContent>
            </Card>
        );
    }

    // Normalize scores to 0-100 scale for chart
    // Sentiment: -1 to 1 -> 0 to 100 (.5 + s/2) * 100
    // Technical: -1 to 1 -> 0 to 100
    // Risk: 0 to 1 -> 0 to 100 (assuming it comes normalized, but risk_agent usually returns low/med/high or 0-1. Let's assume 0-1 or we normalize)
    // Actually our backend returns raw scores. Let's assume standard normalization.

    const sentimentNorm = Math.round(((recommendation.sentiment_score + 1) / 2) * 100);
    const technicalNorm = Math.round(((recommendation.technical_score + 1) / 2) * 100);
    // Risk is usually "Risk Level". If score is high (risky) -> we might want to plot "Safety"? 
    // Let's plot "Risk Score" directly (0-100). If low risk = 0, high = 100.
    const riskNorm = Math.round(recommendation.risk_score * 100);
    const confidence = Math.round(recommendation.confidence);

    const data = [
        { subject: 'Sentiment', A: sentimentNorm, fullMark: 100 },
        { subject: 'Technical', A: technicalNorm, fullMark: 100 },
        { subject: 'Risk', A: riskNorm, fullMark: 100 },
        { subject: 'Confidence', A: confidence, fullMark: 100 },
    ];

    return (
        <Card className="glass-card h-full">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <BrainCircuit className="h-4 w-4 text-primary" />
                    Multi-Agent Consensus
                </CardTitle>
            </CardHeader>
            <CardContent className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
                        <PolarGrid stroke="rgba(255,255,255,0.1)" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                        <Radar
                            name="Agent Score"
                            dataKey="A"
                            stroke="#8b5cf6"
                            strokeWidth={2}
                            fill="#8b5cf6"
                            fillOpacity={0.3}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e1e2d', borderColor: '#333' }}
                            itemStyle={{ color: '#fff' }}
                        />
                    </RadarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
