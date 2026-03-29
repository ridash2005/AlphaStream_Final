import { useNavigate } from 'react-router-dom';
import { Zap, TrendingUp, BarChart2, MessageCircle, Shield, Globe, ChevronRight, ArrowRight } from 'lucide-react';

const FEATURES = [
  {
    icon: <TrendingUp className="h-6 w-6" />,
    title: 'Opportunity Radar',
    desc: 'AI scans NSE/BSE filings, insider trades, FII/DII flows — surfaces signals with Alpha Score (0-100)',
  },
  {
    icon: <BarChart2 className="h-6 w-6" />,
    title: 'Chart Pattern Intelligence',
    desc: 'RSI divergence, MACD crossover, Bollinger breakouts — with historical backtested success rates',
  },
  {
    icon: <MessageCircle className="h-6 w-6" />,
    title: 'Market ChatGPT Next Gen',
    desc: 'Ask anything in plain English — grounded in real data via Text2SQL, not LLM hallucination',
  },
  {
    icon: <Shield className="h-6 w-6" />,
    title: 'Portfolio-Aware Alerts',
    desc: 'Ambient AI alerts when signals affect YOUR holdings. Insider cluster buying, FII streaks, material filings',
  },
  {
    icon: <Globe className="h-6 w-6" />,
    title: 'Real-Time Streaming',
    desc: 'Pathway streaming engine ingests news from 6+ Indian sources in <2 seconds',
  },
  {
    icon: <Zap className="h-6 w-6" />,
    title: 'Backtested Confidence',
    desc: '"This pattern worked 78% of the time on THIS stock over 5 years" — Bloomberg-grade, free',
  },
];

const STATS = [
  { value: '50+', label: 'Nifty Stocks Tracked' },
  { value: '13', label: 'AI Agents' },
  { value: '<2s', label: 'Signal Latency' },
  { value: '6+', label: 'Data Sources' },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#050510] text-white overflow-x-hidden">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-[#050510]/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20">
              <Zap className="h-5 w-5 text-purple-400" />
            </div>
            <span className="text-lg font-bold">AlphaStream India</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="https://github.com/wildcraft958/AlphaStream_India" target="_blank" rel="noreferrer"
              className="text-sm text-gray-400 hover:text-white transition-colors">GitHub</a>
            <button onClick={() => navigate('/login')}
              className="text-sm px-4 py-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
              Sign In
            </button>
            <button onClick={() => navigate('/login')}
              className="text-sm px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 transition-colors font-medium">
              Get Started <ChevronRight className="inline h-4 w-4" />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs font-medium mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
            ET AI Hackathon 2026 — Problem Statement 6
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-[1.1] mb-6">
            AI-Powered Investment
            <br />
            <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-orange-400 bg-clip-text text-transparent">
              Intelligence for India
            </span>
          </h1>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-8 leading-relaxed">
            14 crore+ demat accounts. Most retail investors flying blind.
            AlphaStream turns ET Markets data into actionable, backtested signals —
            powered by multi-agent AI, real-time streaming, and natural language queries.
          </p>
          <div className="flex items-center justify-center gap-4">
            <button onClick={() => navigate('/login')}
              className="px-6 py-3 rounded-xl bg-purple-600 hover:bg-purple-500 font-semibold text-base transition-all hover:shadow-[0_0_30px_rgba(168,85,247,0.4)] flex items-center gap-2">
              Launch Dashboard <ArrowRight className="h-5 w-5" />
            </button>
            <button onClick={() => window.open('mailto:team@alphastream.in', '_blank')}
              className="px-6 py-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 font-semibold text-base transition-colors">
              Book a Demo
            </button>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 border-y border-white/5">
        <div className="max-w-4xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
          {STATS.map((s, i) => (
            <div key={i} className="text-center">
              <p className="text-3xl font-extrabold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                {s.value}
              </p>
              <p className="text-sm text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">Everything You Need to Beat the Market</h2>
          <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
            Multi-agent signal detection, NLQ analytics, backtested patterns — the intelligence layer ET Markets deserves.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f, i) => (
              <div key={i} className="p-6 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-purple-500/20 hover:bg-white/[0.04] transition-all group">
                <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 w-fit mb-4 text-purple-400 group-hover:text-purple-300 transition-colors">
                  {f.icon}
                </div>
                <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture */}
      <section className="py-20 px-6 border-t border-white/5">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-3">Production-Grade Architecture</h2>
          <p className="text-gray-400 mb-10">Not a ChatGPT wrapper. A real-time intelligence platform built layer by layer.</p>
          <div className="space-y-2">
            {[
              {
                label: 'Data Sources',
                desc: 'NSE · BSE · FII/DII · Groww · ET Markets RSS · WorldMonitor · FRED',
                color: 'border-purple-500/30 bg-purple-500/5',
                dot: 'bg-purple-400',
              },
              {
                label: 'Pathway Streaming Engine',
                desc: 'Real-time news ingestion → Chunking → Embedding → Adaptive RAG  (<2s latency)',
                color: 'border-blue-500/30 bg-blue-500/5',
                dot: 'bg-blue-400',
              },
              {
                label: '13 AI Agents',
                desc: 'Sentiment · Technical (RSI/SMA) · Risk · Pattern · Backtest · Flow · Filing · Anomaly (River ML) · Decision',
                color: 'border-cyan-500/30 bg-cyan-500/5',
                dot: 'bg-cyan-400',
              },
              {
                label: 'NLQ Agent (LangGraph 8-node)',
                desc: 'Guardrail → Web Enrich → Route → Text2SQL → Narrate · Portfolio-aware · Source-cited',
                color: 'border-emerald-500/30 bg-emerald-500/5',
                dot: 'bg-emerald-400',
              },
              {
                label: 'Fusion Engine',
                desc: 'Alpha Score = weighted composite of all agent signals (0–100)',
                color: 'border-amber-500/30 bg-amber-500/5',
                dot: 'bg-amber-400',
              },
              {
                label: 'Bloomberg Terminal (5 tabs)',
                desc: 'Overview · Signals · Global Intel · Company · Portfolio — React + WebSocket + SSE',
                color: 'border-pink-500/30 bg-pink-500/5',
                dot: 'bg-pink-400',
              },
            ].map((layer, i, arr) => (
              <div key={i} className="flex flex-col items-center">
                <div className={`w-full rounded-xl border px-6 py-4 text-left flex items-center gap-4 ${layer.color}`}>
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${layer.dot}`} />
                  <div>
                    <span className="text-white font-semibold text-sm">{layer.label}</span>
                    <p className="text-gray-400 text-xs mt-0.5">{layer.desc}</p>
                  </div>
                </div>
                {i < arr.length - 1 && (
                  <div className="w-px h-4 bg-white/10" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to See It in Action?</h2>
          <p className="text-gray-400 mb-8">
            Free access for hackathon judges. Sign in with the test account to explore the full platform.
          </p>
          <button onClick={() => navigate('/login')}
            className="px-8 py-4 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 font-semibold text-lg transition-all hover:shadow-[0_0_40px_rgba(168,85,247,0.4)]">
            Get Started Free
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 px-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between text-sm text-gray-500">
          <span>AlphaStream India - ET AI Hackathon 2026</span>
          <span>Built with Pathway, LangGraph, Gemini, React</span>
        </div>
      </footer>
    </div>
  );
}
