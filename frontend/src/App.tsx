import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Zap } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import {
  TickerSearch,
  RecommendationCard,
  ArticlesList,
  HistoryPanel,
  SystemStatus,
} from '@/components/trading';
import { MarketHeatmap } from '@/components/trading/MarketHeatmap';
import { NetworkGraph } from '@/components/trading/NetworkGraph';
import { useAppStore } from '@/store/appStore';

function App() {
  const { error, clearError } = useAppStore();

  return (
    <div className="min-h-screen terminal-bg">
      {/* Header */}
      <header className="glass border-b border-border/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20 glow-primary">
              <Zap className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">AlphaStream</h1>
              <p className="text-xs text-muted-foreground">Live AI Trading Agent</p>
            </div>
          </div>
          <SystemStatus />
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Error alert */}
        {error && (
          <Alert variant="destructive" className="mb-4 glass-card">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <button onClick={clearError} className="text-xs underline hover:no-underline">
                Dismiss
              </button>
            </AlertDescription>
          </Alert>
        )}

        {/* Search bar */}
        <div className="mb-6">
          <TickerSearch />
        </div>

        {/* Dashboard grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main column - Recommendation */}
          <div className="lg:col-span-2 space-y-6">
            <RecommendationCard />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <MarketHeatmap />
              <NetworkGraph />
            </div>
            <HistoryPanel />
          </div>

          {/* Sidebar - Articles */}
          <div className="lg:col-span-1">
            <ArticlesList />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/30 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between text-xs text-muted-foreground">
          <div>
            Powered by <span className="text-primary font-medium">Pathway</span> Real-Time RAG
          </div>
          <div>DataQuest 2026</div>
        </div>
      </footer>
    </div>
  );
}

export default App;
