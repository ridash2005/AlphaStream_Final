import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { apiService } from '@/services/api';
import { Activity, Database, Bot, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SystemStatus() {
    const { health } = useAppStore();
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const healthData = await apiService.getHealth();
                useAppStore.getState().setHealth(healthData);
                setIsConnected(true);
            } catch {
                setIsConnected(false);
            }
        };

        // Check immediately
        checkHealth();

        // Then check every 30 seconds
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, []);

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

            {health && (
                <>
                    <div className="h-3 w-px bg-border" />

                    {/* Document count */}
                    <div className="flex items-center gap-1.5">
                        <Database className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-muted-foreground">
                            {health.document_count} docs
                        </span>
                    </div>

                    <div className="h-3 w-px bg-border" />

                    {/* RAG Pipeline */}
                    <div className="flex items-center gap-1.5">
                        <Activity
                            className={cn(
                                'h-3.5 w-3.5',
                                health.components.rag_pipeline ? 'text-emerald-400' : 'text-red-400'
                            )}
                        />
                        <span
                            className={cn(
                                health.components.rag_pipeline ? 'text-emerald-400' : 'text-red-400'
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
                                health.components.sentiment_agent ? 'text-emerald-400' : 'text-red-400'
                            )}
                        />
                        <span
                            className={cn(
                                health.components.sentiment_agent ? 'text-emerald-400' : 'text-red-400'
                            )}
                        >
                            Agent
                        </span>
                    </div>
                </>
            )}

            {/* Indexing Latency */}
            <div className="h-3 w-px bg-border" />
            <div className="flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-blue-400" />
                <span className="text-blue-400">
                    {useAppStore.getState().indexingLatency ? `${useAppStore.getState().indexingLatency}ms ingest` : 'Waiting...'}
                </span>
            </div>
        </div>
    );
}
