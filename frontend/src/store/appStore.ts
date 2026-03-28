import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Auth
export interface UserProfile {
    email: string;
    name: string;
    role: string;
    isLoggedIn: boolean;
}

// Portfolio
export interface Holding {
    ticker: string;
    quantity: number;
    buy_price: number;
}

// Types
export interface Recommendation {
    ticker: string;
    timestamp: string;
    recommendation: 'BUY' | 'HOLD' | 'SELL';
    confidence: number;
    sentiment_score: number;
    sentiment_label: 'BEARISH' | 'NEUTRAL' | 'BULLISH';
    technical_score: number;
    risk_score: number;
    key_factors: string[];
    sources: string[];
    latency_ms: number;
    rag_engine?: string;  // "adaptive" or "manual"
    // Global market context (WorldMonitor)
    global_verdict?: string;  // RISK-ON, RISK-OFF, MIXED
    vix?: number | null;
    fear_greed_score?: number | null;
}

export interface Article {
    title: string;
    source: string;
    similarity: number;
    snippet: string;
}

export interface HealthStatus {
    status: string;
    timestamp: string;
    document_count: number;
    components: {
        rag_pipeline: boolean;
        sentiment_agent: boolean;
    };
}

export interface AgentStatus {
    agent: string;
    status: string;
    timestamp: string;
}

// Store state
interface AppState {
    // Auth
    user: UserProfile | null;

    // Data
    recommendation: Recommendation | null;
    articles: Article[];
    health: HealthStatus | null;
    marketHeatmap: { ticker: string; score: number; updated: string }[];
    indexingLatency: number | null;
    documentCount: number | null;
    agentStatus: AgentStatus | null;

    // Portfolio
    portfolio: Holding[];

    // UI State
    currentTicker: string;
    isLoading: boolean;
    error: string | null;

    // History
    recommendationHistory: Recommendation[];

    // Global market (WorldMonitor)
    globalIndices: { symbol: string; name: string; display: string; price: number | null; change: number; sparkline: number[] }[];
    commodityQuotes: { symbol: string; name: string; display: string; price: number | null; change: number; sparkline: number[] }[];
    fearGreed: { score: number; label: string; previous: number } | null;
    macroSignals: { verdict: string; bullish_count: number; bearish_count: number; total_signals: number; signals: any[] } | null;

    // NLQ state
    nlqOpen: boolean;
    nlqSessionId: string;

    // Actions
    setUser: (user: UserProfile | null) => void;
    logout: () => void;
    setPortfolio: (holdings: Holding[]) => void;
    setTicker: (ticker: string) => void;
    setRecommendation: (rec: Recommendation) => void;
    setArticles: (articles: Article[]) => void;
    setHealth: (health: HealthStatus) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    addToHistory: (rec: Recommendation) => void;
    clearError: () => void;
    setDocumentCount: (count: number) => void;
    setAgentStatus: (status: AgentStatus | null) => void;
    connectStream: (ticker: string) => void;
    disconnectStream: () => void;
    socket: WebSocket | null;

    // Global market actions
    setGlobalIndices: (data: AppState['globalIndices']) => void;
    setCommodityQuotes: (data: AppState['commodityQuotes']) => void;
    setFearGreed: (data: AppState['fearGreed']) => void;
    setMacroSignals: (data: AppState['macroSignals']) => void;

    // NLQ actions
    setNlqOpen: (open: boolean) => void;
    setNlqSessionId: (id: string) => void;
}



export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
    // Auth
    user: null,

    // Initial state
    recommendation: null,
    articles: [],
    health: null,
    marketHeatmap: [],
    indexingLatency: null,
    documentCount: null,
    agentStatus: null,
    currentTicker: 'RELIANCE',
    isLoading: false,
    error: null,
    recommendationHistory: [],
    socket: null,
    nlqOpen: false,
    nlqSessionId: 'default',

    // Global market (WorldMonitor)
    globalIndices: [],
    commodityQuotes: [],
    fearGreed: null,
    macroSignals: null,

    // Portfolio
    portfolio: [],

    // Auth actions
    setUser: (user) => set({ user }),
    logout: () => set({ user: null, portfolio: [], recommendationHistory: [] }),
    setPortfolio: (holdings) => set({ portfolio: holdings }),

    // Actions
    setTicker: (ticker) => set({ currentTicker: ticker.toUpperCase() }),

    setRecommendation: (rec) => set((state) => ({
        recommendation: rec,
        recommendationHistory: [rec, ...state.recommendationHistory].slice(0, 10),
        agentStatus: null, // Clear status on final result
    })),

    setArticles: (articles) => set({ articles }),

    setHealth: (health) => set({ health }),

    setLoading: (loading) => set({ isLoading: loading }),

    setError: (error) => set({ error }),

    addToHistory: (rec) => set((state) => ({
        recommendationHistory: [rec, ...state.recommendationHistory].slice(0, 10),
    })),

    clearError: () => set({ error: null }),

    setDocumentCount: (count) => set({ documentCount: count }),

    setAgentStatus: (status) => set({ agentStatus: status }),

    connectStream: (ticker) => {
        const { socket, setRecommendation, setLoading } = get();

        // Close existing
        if (socket) {
            socket.close();
        }

        const apiBase = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;
        const wsBase = apiBase.replace(/^http/, 'ws');
        const wsUrl = `${wsBase}/ws/stream/${ticker}`;
        let retryCount = 0;
        const maxRetries = 5;

        const connect = () => {
            console.log(`Connecting to stream: ${wsUrl}`);
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log("WebSocket connected");
                retryCount = 0; // reset on success
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'market_update') {
                        set({ marketHeatmap: data.data });
                    } else if (data.type === 'metrics_update') {
                        set({
                            indexingLatency: data.data.indexing_latency_ms,
                            documentCount: data.data.total_docs || null,
                        });
                    } else if (data.type === 'agent_update') {
                        set({ agentStatus: data.data });
                    } else if (data.type === 'global_market_update') {
                        const gd = data.data;
                        if (gd.indices) set({ globalIndices: gd.indices });
                        if (gd.commodities) set({ commodityQuotes: gd.commodities });
                        if (gd.fear_greed) set({ fearGreed: gd.fear_greed });
                    } else if (data.type === 'recommendation' && data.data) {
                        setRecommendation(data.data);
                        setLoading(false);
                    } else if (data.ticker && data.recommendation) {
                        // Legacy: direct recommendation object (backwards compat)
                        setRecommendation(data);
                        setLoading(false);
                    } else {
                        console.warn('Unknown WebSocket message type:', data.type || 'none');
                    }
                } catch (e) {
                    console.error("Failed to parse WS message", e);
                }
            };

            ws.onerror = () => {
                console.error("WebSocket error");
            };

            ws.onclose = () => {
                // Auto-reconnect with exponential backoff
                if (retryCount < maxRetries && get().currentTicker === ticker) {
                    const delay = Math.min(1000 * Math.pow(2, retryCount), 16000);
                    retryCount++;
                    console.log(`WebSocket closed, reconnecting in ${delay}ms (attempt ${retryCount})`);
                    setTimeout(connect, delay);
                }
            };

            set({ socket: ws });
        };

        connect();
    },

    disconnectStream: () => {
        const { socket } = get();
        if (socket) {
            socket.close();
            set({ socket: null });
        }
    },

    // Global market actions
    setGlobalIndices: (data) => set({ globalIndices: data }),
    setCommodityQuotes: (data) => set({ commodityQuotes: data }),
    setFearGreed: (data) => set({ fearGreed: data }),
    setMacroSignals: (data) => set({ macroSignals: data }),

    // NLQ
    setNlqOpen: (open) => set({ nlqOpen: open }),
    setNlqSessionId: (id) => set({ nlqSessionId: id }),
  }),
  {
    name: 'alphastream-store',
    partialize: (state) => ({
      user: state.user,
      portfolio: state.portfolio,
      currentTicker: state.currentTicker,
      nlqSessionId: state.nlqSessionId,
      recommendationHistory: state.recommendationHistory,
    }),
  }
));
