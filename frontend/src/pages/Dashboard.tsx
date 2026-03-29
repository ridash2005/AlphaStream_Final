import { useNavigate } from 'react-router-dom';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { AlertCircle, Zap, LogOut, User, LayoutDashboard, Globe, Building2, Briefcase } from 'lucide-react';
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
  GeoRiskPanel,
  StockFundamentals,
  AnomalyPanel,
  GlobalMarketsPanel,
  StockScreener,
  CorporateFilings,
  PortfolioManager,
  WatchlistPanel,
} from '@/components/trading';
import { MarketHeatmap } from '@/components/trading/MarketHeatmap';
import { AgentRadar } from '@/components/trading/AgentRadar';
import { Footer } from '@/components/Footer';
import NLQPanel from '@/components/trading/NLQPanel';
import NLQButton from '@/components/trading/NLQButton';

export default function Dashboard() {
  const { error, clearError, user, logout, setActiveTab } = useAppStore();
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

      {/* Error alert — between GlobalMarketBar and Tabs */}
      {error && (
        <div className="max-w-[1600px] mx-auto px-4 pt-3 w-full shrink-0">
          <Alert variant="destructive" className="glass-card">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <button onClick={clearError} className="text-xs underline hover:no-underline">Dismiss</button>
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* 5-tab layout */}
      <Tabs defaultValue="overview" onValueChange={setActiveTab} className="flex flex-col flex-1 overflow-hidden">
        <TabsList className="w-full justify-start rounded-none border-b border-border/30 bg-secondary/20 h-10 px-2 gap-0.5 shrink-0">
          <TabsTrigger value="overview" className="rounded-md border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-primary/15 data-[state=active]:text-primary text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors text-xs font-medium px-3 h-8 gap-1.5 mx-0.5">
            <LayoutDashboard className="h-3.5 w-3.5" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="signals" className="rounded-md border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-primary/15 data-[state=active]:text-primary text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors text-xs font-medium px-3 h-8 gap-1.5 mx-0.5">
            <Zap className="h-3.5 w-3.5" />
            Signals
          </TabsTrigger>
          <TabsTrigger value="global" className="rounded-md border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-primary/15 data-[state=active]:text-primary text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors text-xs font-medium px-3 h-8 gap-1.5 mx-0.5">
            <Globe className="h-3.5 w-3.5" />
            Global Intel
          </TabsTrigger>
          <TabsTrigger value="company" className="rounded-md border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-primary/15 data-[state=active]:text-primary text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors text-xs font-medium px-3 h-8 gap-1.5 mx-0.5">
            <Building2 className="h-3.5 w-3.5" />
            Company
          </TabsTrigger>
          <TabsTrigger value="portfolio" className="rounded-md border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-primary/15 data-[state=active]:text-primary text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors text-xs font-medium px-3 h-8 gap-1.5 mx-0.5">
            <Briefcase className="h-3.5 w-3.5" />
            Portfolio
          </TabsTrigger>
        </TabsList>

        {/* Overview tab */}
        <TabsContent value="overview" className="flex-1 overflow-y-auto scrollbar-hide mt-0 border-0 p-0">
          <div className="max-w-[1600px] mx-auto px-4 pt-4 pb-40">
            <div className="mb-4">
              <TickerSearch />
            </div>

            {/* Row 1: Chart — full width */}
            <div className="mb-4">
              <ChartView />
            </div>

            {/* Row 2: Recommendation + AgentRadar + Fundamentals + Anomaly */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4">
              <div className="lg:col-span-4">
                <RecommendationCard />
              </div>
              <div className="lg:col-span-2">
                <AgentRadar />
              </div>
              <div className="lg:col-span-4">
                <StockFundamentals />
              </div>
              <div className="lg:col-span-2">
                <AnomalyPanel />
              </div>
            </div>

            {/* Row 2: Opportunity signals + Flow chart + Signal history */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <OpportunityRadar />
              <FlowChart />
              <HistoryChart />
            </div>
          </div>
        </TabsContent>

        {/* Signals tab */}
        <TabsContent value="signals" className="flex-1 overflow-y-auto scrollbar-hide mt-0 border-0 p-0">
          <div className="max-w-[1600px] mx-auto px-4 pt-4 pb-40">
            {/* Stock Screener — full width */}
            <div className="mb-4">
              <StockScreener />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <SectorHeatmap />
              <MarketHeatmap />
              <InsiderActivity />
              <NetworkGraph />
            </div>
          </div>
        </TabsContent>

        {/* Global Intel tab */}
        <TabsContent value="global" className="flex-1 overflow-y-auto scrollbar-hide mt-0 border-0 p-0">
          <div className="max-w-[1600px] mx-auto px-4 pt-4 pb-40">
            <ErrorBoundary section="Global Intelligence">
              {/* Global Markets Panel — Crypto / FX / Sectors */}
              <div className="mb-4">
                <GlobalMarketsPanel />
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
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
              <div className="mt-4">
                <GeoRiskPanel />
              </div>
            </ErrorBoundary>
          </div>
        </TabsContent>

        {/* Company tab */}
        <TabsContent value="company" className="flex-1 overflow-y-auto scrollbar-hide mt-0 border-0 p-0">
          <div className="max-w-[1600px] mx-auto px-4 pt-4 pb-40">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2">
                <ArticlesList />
              </div>
              <div className="space-y-4">
                <CorporateFilings />
                <WatchlistPanel />
                <ReportDownload />
                <HistoryPanel />
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Portfolio tab */}
        <TabsContent value="portfolio" className="flex-1 overflow-y-auto scrollbar-hide mt-0 border-0 p-0">
          <div className="max-w-[1600px] mx-auto px-4 pt-4 pb-40">
            <PortfolioManager />
          </div>
        </TabsContent>
      </Tabs>

      <NLQPanel />
      <NLQButton />
      <Footer />
    </div>
  );
}
