import { create } from 'zustand';

// Types
export interface Recommendation {
    ticker: string;
    timestamp: string;
    recommendation: 'BUY' | 'HOLD' | 'SELL';
    confidence: number;
    sentiment_score: number;
    sentiment_label: 'BEARISH' | 'NEUTRAL' | 'BULLISH';
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
}

export const useAppStore = create<AppState>((set) => ({
    // Initial state
    recommendation: null,
    articles: [],
    health: null,
    currentTicker: 'AAPL',
    isLoading: false,
    error: null,
    recommendationHistory: [],

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
}));
