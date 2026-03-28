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

        const wsUrl = `ws://${window.location.hostname}:8000/ws/stream/${ticker}`;
        console.log(`Connecting to stream: ${wsUrl}`);

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("WebSocket connected");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Handle different message types
                if (data.type === 'market_update') {
                    console.log("Market Heatmap update:", data.data);
                    set({ marketHeatmap: data.data });
                }
                else if (data.type === 'metrics_update') {
                    console.log("Metrics update:", data.data);
                    set({
                        indexingLatency: data.data.indexing_latency_ms,
                        documentCount: data.data.total_docs || null
                    });
                }
                else if (data.type === 'agent_update') {
                    console.log("Agent update:", data.data);
                    set({ agentStatus: data.data });
                }
                else {
                    // Assume default is recommendation
                    console.log("Stream update:", data);
                    setRecommendation(data);
                    setLoading(false);
                }
            } catch (e) {
                console.error("Failed to parse WS message", e);
            }
        };

        ws.onerror = (e) => {
            console.error("WebSocket error", e);
            // set({ error: "Stream connection failed" });
        };

        set({ socket: ws });
    },

    disconnectStream: () => {
        const { socket } = get();
        if (socket) {
            socket.close();
            set({ socket: null });
        }
    },

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
    }),
  }
));
