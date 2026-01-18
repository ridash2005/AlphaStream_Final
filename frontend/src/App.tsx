import { useRef } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Zap, ArrowUp, ArrowDown } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import {
  TickerSearch,
  RecommendationCard,
  ArticlesList,
  HistoryPanel,
  SystemStatus,
  InsiderActivity,
  ReportDownload,
} from '@/components/trading';
import { MarketHeatmap } from '@/components/trading/MarketHeatmap';
import { AgentRadar } from '@/components/trading/AgentRadar';
import { Footer } from '@/components/Footer';

function App() {
  const { error, clearError } = useAppStore();
  const mainRef = useRef<HTMLElement>(null);

  return (
    <div className="h-screen w-full overflow-hidden terminal-bg flex flex-col relative">
      {/* Header */}
      <header className="glass border-b border-border/50 shrink-0 z-50">
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

      {/* Main content - Scrollable */}
      <main ref={mainRef} className="flex-1 overflow-y-auto scrollbar-hide w-full relative">
        <div className="max-w-7xl mx-auto px-4 pt-6 pb-40">
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
                <AgentRadar />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <InsiderActivity />
                <ReportDownload />
              </div>
              <HistoryPanel />
            </div>

            {/* Sidebar - Articles */}
            <div className="lg:col-span-1">
              <ArticlesList />
            </div>
          </div>
        </div>
      </main>

      {/* Floating Navigation Buttons */}
      <div className="fixed bottom-20 right-6 flex flex-col gap-2 z-50">
        <button
          onClick={() => mainRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}
          className="p-2 rounded-full glass hover:bg-primary/20 transition-all duration-300 border border-border/50 shadow-lg hover:scale-110 active:scale-95 group"
          title="Scroll to Top"
        >
          <ArrowUp className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
        </button>
        <button
          onClick={() => mainRef.current?.scrollTo({ top: mainRef.current.scrollHeight, behavior: 'smooth' })}
          className="p-2 rounded-full glass hover:bg-primary/20 transition-all duration-300 border border-border/50 shadow-lg hover:scale-110 active:scale-95 group"
          title="Scroll to Bottom"
        >
          <ArrowDown className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
        </button>
      </div>

      {/* Footer - Pinned */}
      <Footer />
    </div>
  );
}

export default App;
