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
    // Respect actual backend data - avoid fake defaults unless necessary for rendering safety

    const rawSentiment = recommendation.sentiment_score ?? 0; // -1 to 1
    const rawTechnical = recommendation.technical_score ?? 0; // -1 to 1
    const rawRisk = recommendation.risk_score ?? 0; // 0 to 1
    const rawConfidence = recommendation.confidence ?? 0; // 0 to 100

    const sentimentNorm = Math.round(((rawSentiment + 1) / 2) * 100);
    const technicalNorm = Math.round(((rawTechnical + 1) / 2) * 100);
    const riskNorm = Math.round(rawRisk * 100);
    const confidence = Math.round(rawConfidence);

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
