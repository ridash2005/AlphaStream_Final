import { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Zap, ArrowUp, ArrowDown, LogOut, User } from 'lucide-react';
import { useAppStore } from '@/store/appStore';
import {
  TickerSearch,
  RecommendationCard,
  ArticlesList,
  HistoryPanel,
  SystemStatus,
  InsiderActivity,
  ReportDownload,
  OpportunityRadar,
  ChartView,
  NotificationBell,
  NetworkGraph,
  FlowChart,
  HistoryChart,
  SectorHeatmap,
  GlobalMarketBar,
  FearGreedGauge,
  MacroSignalPanel,
  CommodityStrip,
  ErrorBoundary,
} from '@/components/trading';
import { MarketHeatmap } from '@/components/trading/MarketHeatmap';
import { AgentRadar } from '@/components/trading/AgentRadar';
import { Footer } from '@/components/Footer';
import NLQPanel from '@/components/trading/NLQPanel';
import NLQButton from '@/components/trading/NLQButton';

export default function Dashboard() {
  const { error, clearError, user, logout } = useAppStore();
  const mainRef = useRef<HTMLElement>(null);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="h-screen w-full overflow-hidden terminal-bg flex flex-col relative">
      {/* Header */}
      <header className="glass border-b border-border/50 shrink-0 z-50">
        <div className="max-w-[1600px] mx-auto px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20 glow-primary">
              <Zap className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight leading-none">AlphaStream India</h1>
              <p className="text-[10px] text-muted-foreground">AI Investment Intelligence</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <NotificationBell />
            <SystemStatus />
            {user && (
              <div className="flex items-center gap-2 ml-2 pl-2 border-l border-border/30">
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-secondary/30">
                  <User className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">{user.name}</span>
                </div>
                <button onClick={handleLogout} title="Sign out"
                  className="p-1.5 rounded-lg hover:bg-secondary/50 text-muted-foreground hover:text-white transition-colors">
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Bloomberg-style scrolling global market ticker */}
      <ErrorBoundary section="Global Market Bar">
        <GlobalMarketBar />
      </ErrorBoundary>

      {/* Main content — dense Bloomberg layout */}
      <main ref={mainRef} className="flex-1 overflow-y-auto scrollbar-hide w-full relative">
        <div className="max-w-[1600px] mx-auto px-4 pt-4 pb-40">
          {error && (
            <Alert variant="destructive" className="mb-3 glass-card">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>{error}</span>
                <button onClick={clearError} className="text-xs underline hover:no-underline">Dismiss</button>
              </AlertDescription>
            </Alert>
          )}

          <div className="mb-4">
            <TickerSearch />
          </div>

          {/* Row 1: Chart + Recommendation + Agent Radar (primary data) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4">
            <div className="lg:col-span-7">
              <ChartView />
            </div>
            <div className="lg:col-span-3">
              <RecommendationCard />
            </div>
            <div className="lg:col-span-2">
              <AgentRadar />
            </div>
          </div>

          {/* Row 2: Opportunity signals + Flow chart + Signal history */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
            <OpportunityRadar />
            <FlowChart />
            <HistoryChart />
          </div>

          {/* Row 2.5: Global Intelligence (WorldMonitor) */}
          <ErrorBoundary section="Global Intelligence">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4">
              <div className="lg:col-span-3">
                <FearGreedGauge />
              </div>
              <div className="lg:col-span-4">
                <MacroSignalPanel />
              </div>
              <div className="lg:col-span-5">
                <CommodityStrip />
              </div>
            </div>
          </ErrorBoundary>

          {/* Row 3: Sector heatmap + Market sentiment + Insider + Network */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <SectorHeatmap />
            <MarketHeatmap />
            <InsiderActivity />
            <NetworkGraph />
          </div>

          {/* Row 4: News + Report + History */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <ArticlesList />
            </div>
            <div className="space-y-4">
              <ReportDownload />
              <HistoryPanel />
            </div>
          </div>
        </div>
      </main>

      {/* Floating buttons */}
      <div className="fixed bottom-20 right-6 flex flex-col gap-2 z-50">
        <button onClick={() => mainRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}
          className="p-2 rounded-full glass hover:bg-primary/20 transition-all border border-border/50 shadow-lg group" title="Top">
          <ArrowUp className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
        </button>
        <button onClick={() => mainRef.current?.scrollTo({ top: mainRef.current.scrollHeight, behavior: 'smooth' })}
          className="p-2 rounded-full glass hover:bg-primary/20 transition-all border border-border/50 shadow-lg group" title="Bottom">
          <ArrowDown className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
        </button>
      </div>

      <NLQPanel />
      <NLQButton />
      <Footer />
    </div>
  );
}
