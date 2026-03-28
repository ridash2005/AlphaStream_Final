import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

interface HotspotAlert {
  name: string;
  impact: string;
  escalation_score: number;
}

interface GeoRisk {
  score: number;
  level: string;
  baseline: number;
  event_boost: number;
  recent_events: number;
  hotspot_alerts: HotspotAlert[];
  summary: string;
}

const LEVEL_COLORS: Record<string, { text: string; bg: string }> = {
  LOW: { text: 'text-emerald-400', bg: 'bg-emerald-500/20' },
  MODERATE: { text: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  ELEVATED: { text: 'text-orange-400', bg: 'bg-orange-500/20' },
  HIGH: { text: 'text-red-400', bg: 'bg-red-500/20' },
};

export function GeoRiskPanel() {
  const [risk, setRisk] = useState<GeoRisk | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchRisk = async () => {
      try {
        const data = await apiService.getGeoRisk();
        setRisk(data?.data || data);
        setError(false);
      } catch (e) {
        console.warn('Geo risk fetch failed:', e);
        setError(true);
      }
    };
    fetchRisk();
    const interval = setInterval(fetchRisk, 30 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const levelStyle = risk ? LEVEL_COLORS[risk.level] || { text: 'text-gray-400', bg: 'bg-gray-500/20' } : null;

  return (
    <Card className="glass-card">
      <CardHeader className="pb-1">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Shield className="h-4 w-4 text-primary" />
          India Geo-Risk
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!risk ? (
          <div className="text-xs text-muted-foreground text-center py-4">
            <Shield className="h-6 w-6 mx-auto mb-2 opacity-20 animate-pulse" />
            {error ? 'Geo-risk data unavailable' : 'Loading geo-risk...'}
          </div>
        ) : (
          <div>
            {/* Score + Level */}
            <div className="flex items-baseline gap-2 mb-2">
              <span className={cn('text-3xl font-bold font-mono', levelStyle?.text)}>
                {risk.score}
              </span>
              <span className="text-xs text-muted-foreground">/100</span>
              <span className={cn(
                'text-[10px] px-2 py-0.5 rounded-full font-medium',
                levelStyle?.text,
                levelStyle?.bg,
              )}>
                {risk.level}
              </span>
            </div>

            {/* Stats row */}
            <div className="flex gap-4 text-xs text-muted-foreground mb-3">
              <span>{risk.recent_events} event{risk.recent_events !== 1 ? 's' : ''} (24h)</span>
              <span>{risk.hotspot_alerts.length} hotspot{risk.hotspot_alerts.length !== 1 ? 's' : ''}</span>
            </div>

            {/* Score bar */}
            <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden mb-3">
              <div
                className={cn('h-full rounded-full transition-all', {
                  'bg-emerald-400': risk.score <= 25,
                  'bg-yellow-400': risk.score > 25 && risk.score <= 50,
                  'bg-orange-400': risk.score > 50 && risk.score <= 75,
                  'bg-red-400': risk.score > 75,
                })}
                style={{ width: `${Math.min(risk.score, 100)}%` }}
              />
            </div>

            {/* Hotspot Alerts */}
            {risk.hotspot_alerts.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-border/30">
                {risk.hotspot_alerts.map((h) => (
                  <div key={h.name} className="flex items-center gap-2 text-xs group">
                    <span className="text-orange-400 shrink-0">●</span>
                    <span className="text-foreground truncate">{h.name}</span>
                    <span className="text-muted-foreground ml-auto shrink-0 hidden group-hover:inline text-[10px]">
                      {h.impact}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
