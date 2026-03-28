import axios from 'axios';
import type { Recommendation, Article, HealthStatus } from '@/store/appStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const apiService = {
    /**
     * Get trading recommendation for a ticker
     */
    async getRecommendation(ticker: string, query?: string): Promise<Recommendation> {
        const response = await api.post<Recommendation>('/recommend', {
            ticker,
            query,
        });
        return response.data;
    },

    /**
     * Get articles for a ticker
     */
    async getArticles(ticker: string, limit = 10): Promise<{ articles: Article[]; count: number }> {
        const response = await api.get<{ ticker: string; count: number; articles: Article[] }>(
            `/articles/${ticker}`,
            { params: { limit } }
        );
        return response.data;
    },

    /**
     * Check system health
     */
    async getHealth(): Promise<HealthStatus> {
        const response = await api.get<HealthStatus>('/health');
        return response.data;
    },

    /**
     * Ingest a new article (for demo purposes)
     */
    async ingestArticle(article: { title: string; content: string; source?: string }) {
        const response = await api.post('/ingest', article);
        return response.data;
    },

    /**
     * Get market heatmap data
     */
    async getMarketHeatmap(): Promise<{ data: { ticker: string; score: number; updated: string }[] }> {
        const response = await api.get<{ data: { ticker: string; score: number; updated: string }[] }>('/market/heatmap');
        return response.data;
    },

    // ── NLQ endpoints ──────────────────────────────

    async nlqQuery(question: string, sessionId = 'default', portfolioContext?: string) {
        const response = await api.post('/api/nlq', { question, session_id: sessionId, portfolio_context: portfolioContext });
        return response.data;
    },

    openNLQStream(question: string, sessionId = 'default', onEvent: (event: any) => void) {
        const url = `${API_BASE_URL}/api/nlq/stream?question=${encodeURIComponent(question)}&session_id=${sessionId}`;
        const source = new EventSource(url);
        source.onmessage = (e) => {
            try { onEvent(JSON.parse(e.data)); } catch {}
        };
        source.onerror = () => { source.close(); };
        return source;
    },

    // ── Market endpoints ──────────────────────────

    async getRadar(topN = 10) {
        const response = await api.get('/api/radar', { params: { top_n: topN } });
        return response.data;
    },

    async getPatterns(ticker: string) {
        const response = await api.get(`/api/patterns/${ticker}`);
        return response.data;
    },

    async getBacktest(ticker: string, pattern: string, years = 3) {
        const response = await api.get(`/api/backtest/${ticker}/${pattern}`, { params: { years } });
        return response.data;
    },

    async getPopularTickers(): Promise<{ tickers: string[] }> {
        const response = await api.get('/api/tickers/popular');
        return response.data;
    },

    async getFlows(days = 30) {
        const response = await api.get('/api/flows', { params: { days } });
        return response.data;
    },

    async setPortfolio(holdings: { ticker: string; quantity: number; buy_price: number }[]) {
        const response = await api.post('/api/portfolio', { holdings });
        return response.data;
    },

    async getOHLCV(ticker: string, period = '6mo') {
        const response = await api.get(`/api/ohlcv/${ticker}`, { params: { period } });
        return response.data;
    },

    // ── Insights endpoints ────────────────────────

    async getInsights(limit = 20, unreadOnly = false) {
        const response = await api.get('/api/insights', { params: { limit, unread_only: unreadOnly } });
        return response.data;
    },

    async getInsightsCount() {
        const response = await api.get('/api/insights/count');
        return response.data;
    },

    async markInsightRead(id?: string) {
        const response = await api.post('/api/insights/mark-read', { id });
        return response.data;
    },

    async dismissInsight(id: string) {
        const response = await api.post(`/api/insights/dismiss/${id}`);
        return response.data;
    },

    // ── Global Market endpoints (WorldMonitor) ───────────

    async getGlobalIndices() {
        const response = await api.get('/api/global/indices');
        return response.data;
    },

    async getCommodityQuotes() {
        const response = await api.get('/api/global/commodities');
        return response.data;
    },

    async getCryptoQuotes() {
        const response = await api.get('/api/global/crypto');
        return response.data;
    },

    async getVix() {
        const response = await api.get('/api/global/vix');
        return response.data;
    },

    async getFearGreed() {
        const response = await api.get('/api/global/fear-greed');
        return response.data;
    },

    async getSectorPerformance() {
        const response = await api.get('/api/global/sectors');
        return response.data;
    },

    async getMacroSignals() {
        const response = await api.get('/api/global/macro');
        return response.data;
    },

    async getCurrencyQuotes() {
        const response = await api.get('/api/global/currencies');
        return response.data;
    },

    async getGeoRisk() {
        const response = await api.get('/api/global/geo-risk');
        return response.data;
    },

    async getGlobalContext() {
        const response = await api.get('/api/global/context');
        return response.data;
    },
};

export default api;
