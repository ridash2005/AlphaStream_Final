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
};

export default api;
