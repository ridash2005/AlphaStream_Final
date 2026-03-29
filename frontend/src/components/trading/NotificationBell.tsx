import React, { useState, useEffect, useRef } from 'react';
import { Bell, X, AlertTriangle, TrendingUp, Info } from 'lucide-react';
import { apiService } from '@/services/api';

interface Insight {
  id: string;
  type: string;
  severity: string;
  title: string;
  body: string;
  ticker: string;
  created_at: string;
  read: boolean;
}

const SEVERITY_CONFIG: Record<string, { icon: React.ReactElement; color: string }> = {
  warning: { icon: <AlertTriangle className="h-3.5 w-3.5" />, color: 'text-amber-400' },
  success: { icon: <TrendingUp className="h-3.5 w-3.5" />, color: 'text-emerald-400' },
  info:    { icon: <Info className="h-3.5 w-3.5" />, color: 'text-blue-400' },
};

export function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchCount = async () => {
    try {
      const data = await apiService.getInsightsCount();
      setUnread(data.unread || 0);
    } catch {}
  };

  const fetchInsights = async () => {
    try {
      const data = await apiService.getInsights(10, true);
      setInsights(Array.isArray(data) ? data : []);
    } catch {}
  };

  const handleDismiss = async (id: string) => {
    try {
      await apiService.dismissInsight(id);
      setInsights((prev) => prev.filter((i) => i.id !== id));
      setUnread((prev) => Math.max(0, prev - 1));
    } catch {}
  };

  const handleMarkAllRead = async () => {
    try {
      await apiService.markInsightRead();
      setUnread(0);
      setInsights((prev) => prev.map((i) => ({ ...i, read: true })));
    } catch {}
  };

  // Poll every 60s
  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, 60000);
    return () => clearInterval(interval);
  }, []);

  // Fetch on open
  useEffect(() => { if (open) fetchInsights(); }, [open]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-secondary/50 transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5 text-muted-foreground" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-red-500 text-[10px] font-bold text-white flex items-center justify-center animate-pulse">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto rounded-lg border border-border/50 bg-background/95 backdrop-blur-xl shadow-2xl z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border/30">
            <span className="text-sm font-semibold">Notifications</span>
            <div className="flex items-center gap-2">
              {unread > 0 && (
                <button onClick={handleMarkAllRead} className="text-[10px] text-primary hover:underline">
                  Mark all read
                </button>
              )}
              <button onClick={() => setOpen(false)}><X className="h-4 w-4 text-muted-foreground" /></button>
            </div>
          </div>

          {insights.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <Bell className="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">No notifications</p>
            </div>
          ) : (
            <div className="divide-y divide-border/20">
              {insights.map((ins) => {
                const cfg = SEVERITY_CONFIG[ins.severity] || SEVERITY_CONFIG.info;
                return (
                  <div key={ins.id} className={`px-4 py-3 hover:bg-secondary/20 transition-colors ${!ins.read ? 'bg-primary/5' : ''}`}>
                    <div className="flex items-start gap-2">
                      <span className={`mt-0.5 ${cfg.color}`}>{cfg.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate">{ins.title}</p>
                        <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">{ins.body}</p>
                      </div>
                      <button onClick={() => handleDismiss(ins.id)} className="text-muted-foreground/50 hover:text-muted-foreground">
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
