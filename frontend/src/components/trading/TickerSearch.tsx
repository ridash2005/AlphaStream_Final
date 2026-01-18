import { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/store/appStore';
import { apiService } from '@/services/api';

export function TickerSearch() {
    const [inputValue, setInputValue] = useState('');
    const { setTicker, setRecommendation, setArticles, setLoading, setError, isLoading } = useAppStore();

    const handleSearch = async () => {
        const ticker = inputValue.trim().toUpperCase();
        if (!ticker) return;

        setTicker(ticker);
        setLoading(true);
        setError(null);

        try {
            // Fetch recommendation and articles in parallel
            const [recommendation, articlesData] = await Promise.all([
                apiService.getRecommendation(ticker),
                apiService.getArticles(ticker, 5),
            ]);

            setRecommendation(recommendation);
            setArticles(articlesData.articles);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch data';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    };

    const popularTickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN'];

    return (
        <div className="space-y-3">
            <div className="flex gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Enter ticker symbol (e.g., AAPL)"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value.toUpperCase())}
                        onKeyDown={handleKeyDown}
                        className="pl-10 bg-secondary/50 border-border/50 font-mono text-lg uppercase"
                        disabled={isLoading}
                    />
                </div>
                <Button onClick={handleSearch} disabled={isLoading || !inputValue.trim()} className="px-6">
                    {isLoading ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Analyzing
                        </>
                    ) : (
                        'Analyze'
                    )}
                </Button>
            </div>

            {/* Quick access buttons */}
            <div className="flex flex-wrap gap-2">
                <span className="text-xs text-muted-foreground mr-2 self-center">Quick:</span>
                {popularTickers.map((ticker) => (
                    <Button
                        key={ticker}
                        variant="outline"
                        size="sm"
                        onClick={() => {
                            setInputValue(ticker);
                        }}
                        className="font-mono text-xs h-7 px-2 bg-secondary/30 hover:bg-secondary/50"
                    >
                        {ticker}
                    </Button>
                ))}
            </div>
        </div>
    );
}
