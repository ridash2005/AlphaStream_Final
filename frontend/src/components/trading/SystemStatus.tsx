import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { apiService } from '@/services/api';
import { Activity, Database, Bot, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SystemStatus() {
    // Subscribe to store state reactively
    const health = useAppStore((state) => state.health);
    const indexingLatency = useAppStore((state) => state.indexingLatency);
    const documentCount = useAppStore((state) => state.documentCount);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const healthData = await apiService.getHealth();
                useAppStore.getState().setHealth(healthData);
                // Also update document count from health API
                if (healthData.document_count) {
                    useAppStore.getState().setDocumentCount(healthData.document_count);
                }
                setIsConnected(true);
            } catch {
                setIsConnected(false);
            }
        };

        // Check immediately
        checkHealth();

        // Then check every 15 seconds (more frequent updates)
        const interval = setInterval(checkHealth, 15000);
        return () => clearInterval(interval);
    }, []);

    // Use the real-time document count from WebSocket, falling back to health
    const displayDocCount = documentCount || health?.document_count || 0;
    const displayLatency = indexingLatency !== null ? `${indexingLatency.toFixed(2)}ms ingest` : 'Waiting...';

    return (
        <div className="flex items-center gap-4 text-xs">
            {/* Connection status */}
            <div className="flex items-center gap-1.5">
                {isConnected ? (
                    <>
                        <Wifi className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Connected</span>
                    </>
                ) : (
                    <>
                        <WifiOff className="h-3.5 w-3.5 text-red-400" />
                        <span className="text-red-400">Disconnected</span>
                    </>
                )}
            </div>

            <div className="h-3 w-px bg-border" />

            {/* Document count - always show with real-time updates */}
            <div className="flex items-center gap-1.5">
                <Database className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-muted-foreground">
                    {displayDocCount} docs
                </span>
            </div>

            <div className="h-3 w-px bg-border" />

            {/* RAG Pipeline */}
            <div className="flex items-center gap-1.5">
                <Activity
                    className={cn(
                        'h-3.5 w-3.5',
                        health?.components?.rag_pipeline ? 'text-emerald-400' : 'text-red-400'
                    )}
                />
                <span
                    className={cn(
                        health?.components?.rag_pipeline ? 'text-emerald-400' : 'text-red-400'
                    )}
                >
                    RAG
                </span>
            </div>

            {/* Sentiment Agent */}
            <div className="flex items-center gap-1.5">
                <Bot
                    className={cn(
                        'h-3.5 w-3.5',
                        health?.components?.sentiment_agent ? 'text-emerald-400' : 'text-red-400'
                    )}
                />
                <span
                    className={cn(
                        health?.components?.sentiment_agent ? 'text-emerald-400' : 'text-red-400'
                    )}
                >
                    Agent
                </span>
            </div>

            {/* Indexing Latency */}
            <div className="h-3 w-px bg-border" />
            <div className="flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-blue-400" />
                <span className="text-blue-400">
                    {displayLatency}
                </span>
            </div>
        </div>
    );
}
