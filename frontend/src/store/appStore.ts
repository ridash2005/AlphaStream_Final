import { create } from 'zustand';

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

// Store state
interface AppState {
    // Data
    recommendation: Recommendation | null;
    articles: Article[];
    health: HealthStatus | null;
    marketHeatmap: { ticker: string; score: number; updated: string }[];
    indexingLatency: number | null;
    documentCount: number | null;  // Real-time doc count from WebSocket

    // UI State
    currentTicker: string;
    isLoading: boolean;
    error: string | null;

    // History
    recommendationHistory: Recommendation[];

    // Actions
    setTicker: (ticker: string) => void;
    setRecommendation: (rec: Recommendation) => void;
    setArticles: (articles: Article[]) => void;
    setHealth: (health: HealthStatus) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    addToHistory: (rec: Recommendation) => void;
    clearError: () => void;
    setDocumentCount: (count: number) => void;
    connectStream: (ticker: string) => void;
    disconnectStream: () => void;
    socket: WebSocket | null;
}



export const useAppStore = create<AppState>((set, get) => ({
    // Initial state
    recommendation: null,
    articles: [],
    health: null,
    marketHeatmap: [],
    indexingLatency: null,
    documentCount: null,
    currentTicker: 'AAPL',
    isLoading: false,
    error: null,
    recommendationHistory: [],
    socket: null,

    // Actions
    setTicker: (ticker) => set({ currentTicker: ticker.toUpperCase() }),

    setRecommendation: (rec) => set((state) => ({
        recommendation: rec,
        recommendationHistory: [rec, ...state.recommendationHistory].slice(0, 10),
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
    }
}));
