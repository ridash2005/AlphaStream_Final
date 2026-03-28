/**
 * NLQPanel - two-stage AI analytics panel
 *
 * Stage 1 (compact): floating bottom-right panel (NOT full-height sidebar)
 *   - No backdrop - page stays interactive
 *   - Positioned above the FAB button
 * Stage 2 (expanded): large centered modal with chart area + backdrop
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import Markdown from 'react-markdown'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Sparkles,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  Maximize2,
  Minimize2,
  Bot,
  User,
  Zap,
  BarChart2,
  TrendingUp,
} from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { apiService } from '@/services/api'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const QUICK_PROMPTS = [
  'What signals fired today?',
  'Show insider buying in IT sector',
  'What are FIIs doing this week?',
  'Top stocks by alpha score',
]

const CONTEXT_PROMPTS = {
  dashboard:       ['Show bullish signals', 'Sector heatmap', 'FII/DII divergence'],
  radar:           ['Compare top opportunities', 'Which sectors are strongest?', 'Backtest top signal'],
  charts:          ['What patterns do you see?', 'RSI divergence stocks', 'Volume breakout today'],
  default:         ['What signals fired today?', 'Insider buying activity', 'FII flow analysis'],
}

const THOUGHT_STEPS = ['Router', 'Interpret', 'Execute', 'Narrate']

// ---------------------------------------------------------------------------
// Typing indicator
// ---------------------------------------------------------------------------
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3 bg-[#1e1e1e] rounded-2xl rounded-bl-sm w-fit">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15, ease: 'easeInOut' }}
          className="block w-1.5 h-1.5 rounded-full bg-[#888]"
        />
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Thought process collapsible (completed)
// ---------------------------------------------------------------------------
function ThoughtProcess({ steps }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-2 border border-[#2a2a2a] rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center gap-2 px-3 py-2 text-[11px] font-medium text-[#555] hover:text-[#a0a0a0] hover:bg-[#1a1a1a] transition-colors text-left"
      >
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <Zap size={11} />
        Thought process
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 font-mono text-[10px] text-[#555] space-y-1 border-t border-[#252525] pt-2">
              {steps.map((step, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-[#e63946]">-&gt;</span>
                  <span>
                    <span className="text-[#a0a0a0]">{THOUGHT_STEPS[i] ?? `Step ${i + 1}`}:</span>{' '}
                    {step}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Live thought display (streaming - shows steps as they arrive)
// ---------------------------------------------------------------------------
function LiveThoughtDisplay({ steps }) {
  if (!steps || steps.length === 0) return null
  return (
    <div className="mt-1 border border-[#1e2a1e] rounded-lg overflow-hidden bg-[#0d130d]">
      <div className="px-3 py-2 flex items-center gap-2 border-b border-[#1a2a1a]">
        <motion.span
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
          className="block w-1.5 h-1.5 rounded-full bg-[#4caf50]"
        />
        <span className="text-[10px] font-medium text-[#4caf50]">Running agent…</span>
      </div>
      <div className="px-3 py-2 font-mono text-[10px] text-[#555] space-y-1 max-h-28 overflow-y-auto">
        {steps.map((step, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-start gap-2"
          >
            <span className="text-[#4caf50] flex-shrink-0">▶</span>
            <span>
              <span className="text-[#a0a0a0]">[{step.node}]</span>{' '}
              <span className="text-[#666]">{step.action}</span>
              {step.detail && <span className="text-[#444]"> - {step.detail}</span>}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Filter chip
// ---------------------------------------------------------------------------
function FilterChip({ label }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#e63946]/15 text-[#e63946] border border-[#e63946]/25">
      {label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Page context extraction
// ---------------------------------------------------------------------------
function extractVisibleText() {
  const headings = [...document.querySelectorAll('h1,h2,h3')].map((el) => el.innerText).slice(0, 10)
  const kpiCards = [...document.querySelectorAll('[data-kpi]')].map((el) => ({
    label: el.dataset.kpi,
    value: el.innerText.trim(),
  }))
  return { headings, kpiCards }
}

// ---------------------------------------------------------------------------
// Context banner
// ---------------------------------------------------------------------------
function ContextBanner({ pageContext, chartContext, onClearChart }) {
  if (!pageContext && !chartContext) return null
  const page = pageContext?.page || 'dashboard'
  const filterCount = Object.values(pageContext?.filters || {}).filter(
    (v) => v && (Array.isArray(v) ? v.length > 0 : true)
  ).length
  return (
    <div className="px-4 py-2 bg-[#0d130d] border-b border-[#1a2a1a] flex items-center gap-2 text-[11px]">
      <span className="text-[#4caf50]">&#x1f4cd;</span>
      <span className="text-[#a0a0a0]">
        Viewing: <span className="text-white font-medium capitalize">{page.replace(/_/g, ' ')}</span>
        {filterCount > 0 && <span className="text-[#666]"> &middot; {filterCount} filter{filterCount > 1 ? 's' : ''} active</span>}
      </span>
      {chartContext && (
        <span className="ml-auto flex items-center gap-1">
          <span className="text-[#64b5f6]">&#x1f4ca; Chart attached</span>
          <button onClick={onClearChart} className="text-[#555] hover:text-[#aaa] ml-1">&times;</button>
        </span>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Chart drop zone overlay
// ---------------------------------------------------------------------------
function ChartDropZone({ onDrop }) {
  const [dragging, setDragging] = useState(false)

  const handleDragOver = (e) => { e.preventDefault(); setDragging(true) }
  const handleDragLeave = () => setDragging(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)

    // Handle chart JSON dragged from dashboard chart wrappers
    const jsonStr = e.dataTransfer.getData('application/json')
    if (jsonStr) {
      try {
        const chartMeta = JSON.parse(jsonStr)
        if (chartMeta.title || chartMeta.data) {
          onDrop(chartMeta)
          return
        }
      } catch { /* fall through to file handling */ }
    }

    const file = e.dataTransfer.files?.[0]
    if (!file) return

    const reader = new FileReader()
    if (file.type.startsWith('image/')) {
      reader.onload = () => onDrop({ image_base64: reader.result, title: file.name })
      reader.readAsDataURL(file)
    } else if (file.name.endsWith('.csv')) {
      reader.onload = () => {
        const lines = reader.result.split('\n').filter(Boolean)
        const headers = lines[0].split(',').map((h) => h.trim())
        const data = lines.slice(1, 21).map((line) => {
          const vals = line.split(',')
          const row = {}
          headers.forEach((h, i) => { row[h] = vals[i]?.trim() ?? '' })
          return row
        })
        onDrop({ data, title: file.name })
      }
      reader.readAsText(file)
    }
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={[
        'mx-4 my-2 rounded-xl border-2 border-dashed transition-all text-center py-3',
        dragging
          ? 'border-[#e63946] bg-[#e63946]/5 text-[#e63946]'
          : 'border-[#2a2a2a] text-[#444] hover:border-[#555]',
      ].join(' ')}
    >
      <p className="text-[11px] font-medium">
        {dragging ? 'Drop chart here' : 'Drag a dashboard chart, image, or CSV for AI analysis'}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------
function MessageBubble({ msg }) {
  const isBot = msg.role === 'bot'

  if (isBot) {
    return (
      <div className="flex items-start gap-2.5">
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#e63946]/15 border border-[#e63946]/30 flex items-center justify-center">
          <Bot size={13} className="text-[#e63946]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="bg-[#1e1e1e] border border-[#2a2a2a] rounded-2xl rounded-tl-sm px-4 py-3">
            <div className="text-sm text-[#e8e8e8] leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-headings:my-2 prose-strong:text-white">
              <Markdown>{msg.text}</Markdown>
            </div>
            {msg.filters && msg.filters.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-[#2a2a2a]">
                <span className="text-[10px] text-[#555] mr-1">Filters:</span>
                {msg.filters.map((f, i) => <FilterChip key={i} label={f} />)}
              </div>
            )}
          </div>
          {msg.thoughts && msg.thoughts.length > 0 && <ThoughtProcess steps={msg.thoughts} />}
          {msg.ts && <p className="text-[10px] text-[#333] mt-1 ml-1">{msg.ts}</p>}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-end justify-end gap-2.5">
      <div className="max-w-[75%]">
        <div className="bg-[#e63946] rounded-2xl rounded-br-sm px-4 py-3">
          <p className="text-sm text-white leading-relaxed">{msg.text}</p>
        </div>
        {msg.ts && <p className="text-[10px] text-[#333] mt-1 mr-1 text-right">{msg.ts}</p>}
      </div>
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#222] border border-[#333] flex items-center justify-center">
        <User size={13} className="text-[#a0a0a0]" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Chart preview area (expanded mode only) - dynamic from agent response
// ---------------------------------------------------------------------------

// Render a dynamic bar chart from chart_spec.type === 'bar'
function DynamicBarChart({ spec }) {
  const { x, y, data } = spec
  const xKey = x
  const yKey = y[0]
  const maxVal = Math.max(...data.map((r) => Number(r[yKey] ?? 0)))
  if (maxVal === 0) return null
  return (
    <div className="space-y-2 mt-1">
      {data.slice(0, 12).map((row, i) => {
        const val = Number(row[yKey] ?? 0)
        const pct = maxVal > 0 ? (val / maxVal) * 100 : 0
        const color = pct >= 70 ? '#4caf50' : pct >= 40 ? '#ff9800' : '#e63946'
        const label = String(row[xKey] ?? '').replace('WS-', '').replace(/_/g, ' ')
        const displayVal = Number.isInteger(val)
          ? val.toLocaleString()
          : val.toFixed(2)
        return (
          <div key={i} className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-[#a0a0a0] font-medium truncate max-w-[60%]">{label}</span>
              <span className="font-bold tabular-nums" style={{ color }}>{displayVal}</span>
            </div>
            <div className="h-1.5 bg-[#0a0a0a] rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: color, opacity: 0.85 }}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.6, ease: 'easeOut', delay: i * 0.03 }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// Render a compact table for chart_spec.type === 'table'
function DynamicTable({ spec }) {
  const { data } = spec
  if (!data || data.length === 0) return <p className="text-xs text-[#555]">No data returned.</p>
  const cols = Object.keys(data[0]).slice(0, 5)
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="border-b border-[#1f1f1f]">
            {cols.map((c) => (
              <th key={c} className="text-left pb-2 pr-3 text-[#555] uppercase tracking-wide font-semibold">
                {c.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 10).map((row, i) => (
            <tr key={i} className="border-b border-[#111] hover:bg-[#111]">
              {cols.map((c) => (
                <td key={c} className="py-2 pr-3 text-[#a0a0a0] tabular-nums">
                  {String(row[c] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Render a single number card for chart_spec.type === 'number'
function DynamicNumber({ spec }) {
  const { label, value, data } = spec
  const displayVal = typeof value === 'number'
    ? (Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2))
    : String(value ?? '-')
  // If the single row has multiple numeric fields, show them as secondary stats
  const row = data?.[0] || {}
  const extras = Object.entries(row).filter(
    ([k, v]) => typeof v === 'number' && k.replace(/_/g, ' ').toLowerCase() !== label?.toLowerCase()
  ).slice(0, 4)
  return (
    <div className="flex flex-col items-center justify-center py-6 gap-2">
      <p className="text-[10px] text-[#555] uppercase tracking-wider font-semibold">{label || 'Result'}</p>
      <motion.p
        className="text-4xl font-black tabular-nums text-white"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      >
        {displayVal}
      </motion.p>
      {extras.length > 0 && (
        <div className="flex flex-wrap gap-3 mt-2 justify-center">
          {extras.map(([k, v]) => (
            <div key={k} className="text-center px-3 py-1.5 rounded-lg bg-[#0d0d0d] border border-[#1f1f1f]">
              <p className="text-xs font-bold tabular-nums text-[#a0a0a0]">
                {typeof v === 'number' ? (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2)) : String(v)}
              </p>
              <p className="text-[9px] text-[#444] uppercase tracking-wider mt-0.5">{k.replace(/_/g, ' ')}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Render a donut/pie chart for chart_spec.type === 'donut'
function DynamicDonut({ spec }) {
  const { x, y, data } = spec
  const total = data.reduce((s, r) => s + Number(r[y] ?? 0), 0)
  if (total === 0) return null
  const COLORS = ['#e63946', '#4caf50', '#ff9800', '#2196f3', '#ce93d8', '#64b5f6', '#81c784']
  let cumPct = 0
  return (
    <div className="flex flex-col items-center gap-4">
      {/* Simple CSS donut via conic-gradient */}
      <div className="relative w-36 h-36">
        <div
          className="w-full h-full rounded-full"
          style={{
            background: `conic-gradient(${data.map((row, i) => {
              const pct = (Number(row[y] ?? 0) / total) * 100
              const start = cumPct
              cumPct += pct
              return `${COLORS[i % COLORS.length]} ${start}% ${cumPct}%`
            }).join(', ')})`,
          }}
        />
        <div className="absolute inset-3 rounded-full bg-[#111] flex items-center justify-center flex-col">
          <p className="text-lg font-black text-white tabular-nums">{total.toLocaleString()}</p>
          <p className="text-[9px] text-[#555] uppercase">Total</p>
        </div>
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 justify-center">
        {data.map((row, i) => {
          const val = Number(row[y] ?? 0)
          const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0'
          const label = String(row[x] ?? '').replace('WS-', '').replace(/_/g, ' ')
          return (
            <div key={i} className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
              <span className="text-[10px] text-[#a0a0a0]">{label}</span>
              <span className="text-[10px] font-bold tabular-nums" style={{ color: COLORS[i % COLORS.length] }}>{pct}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Render a line chart for chart_spec.type === 'line'
function DynamicLine({ spec }) {
  const { x, y, data } = spec
  const yKey = y[0]
  const values = data.map((r) => Number(r[yKey] ?? 0))
  const maxVal = Math.max(...values, 1)
  const minVal = Math.min(...values, 0)
  const range = maxVal - minVal || 1
  const W = 400
  const H = 140
  const PAD = 20
  const points = values.map((v, i) => ({
    x: PAD + (i / Math.max(values.length - 1, 1)) * (W - PAD * 2),
    y: PAD + (1 - (v - minVal) / range) * (H - PAD * 2),
  }))
  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
  const areaD = `${pathD} L ${points[points.length - 1].x} ${H - PAD} L ${points[0].x} ${H - PAD} Z`
  // X-axis labels (first, middle, last)
  const xLabels = data.length > 2
    ? [
        { i: 0, label: String(data[0][x] ?? '').slice(-5) },
        { i: Math.floor(data.length / 2), label: String(data[Math.floor(data.length / 2)][x] ?? '').slice(-5) },
        { i: data.length - 1, label: String(data[data.length - 1][x] ?? '').slice(-5) },
      ]
    : data.map((r, i) => ({ i, label: String(r[x] ?? '').slice(-5) }))
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-[#888] uppercase tracking-wider">
          {String(yKey).replace(/_/g, ' ')} over time
        </p>
        <span className="text-[9px] text-[#333]">{data.length} points</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 160 }}>
        <defs>
          <linearGradient id="nlq-line-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e63946" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#e63946" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaD} fill="url(#nlq-line-grad)" />
        <path d={pathD} fill="none" stroke="#e63946" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="2.5" fill="#e63946" opacity={i === points.length - 1 ? 1 : 0.5} />
        ))}
        {xLabels.map(({ i, label }) => (
          <text key={i} x={points[i]?.x ?? 0} y={H - 4} textAnchor="middle" fill="#555" fontSize="8">{label}</text>
        ))}
      </svg>
    </div>
  )
}

// Render a scatter plot for chart_spec.type === 'scatter'
function DynamicScatter({ spec }) {
  const { x: xKey, y: yKey, label: labelKey, data } = spec
  const xVals = data.map((r) => Number(r[xKey] ?? 0))
  const yVals = data.map((r) => Number(r[yKey] ?? 0))
  const xMin = Math.min(...xVals)
  const xMax = Math.max(...xVals, xMin + 1)
  const yMin = Math.min(...yVals)
  const yMax = Math.max(...yVals, yMin + 1)
  const W = 400
  const H = 200
  const PAD = 30
  const scaleX = (v) => PAD + ((v - xMin) / (xMax - xMin)) * (W - PAD * 2)
  const scaleY = (v) => PAD + (1 - (v - yMin) / (yMax - yMin)) * (H - PAD * 2)
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-[#888] uppercase tracking-wider">
          {String(xKey).replace(/_/g, ' ')} vs {String(yKey).replace(/_/g, ' ')}
        </p>
        <span className="text-[9px] text-[#333]">{data.length} points</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 220 }}>
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={PAD} x2={W - PAD} y1={PAD + f * (H - PAD * 2)} y2={PAD + f * (H - PAD * 2)} stroke="#1f1f1f" strokeWidth="0.5" />
        ))}
        {/* Points */}
        {data.slice(0, 100).map((row, i) => {
          const cx = scaleX(Number(row[xKey] ?? 0))
          const cy = scaleY(Number(row[yKey] ?? 0))
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r="4" fill="#e63946" opacity="0.7" />
              {labelKey && (
                <text x={cx + 6} y={cy + 3} fill="#666" fontSize="7" className="select-none">
                  {String(row[labelKey] ?? '').slice(0, 12)}
                </text>
              )}
            </g>
          )
        })}
        {/* Axis labels */}
        <text x={W / 2} y={H - 2} textAnchor="middle" fill="#555" fontSize="8">{xKey.replace(/_/g, ' ')}</text>
        <text x={4} y={H / 2} textAnchor="middle" fill="#555" fontSize="8" transform={`rotate(-90, 8, ${H / 2})`}>{yKey.replace(/_/g, ' ')}</text>
      </svg>
    </div>
  )
}

// Static fallback - shown before any query is made
function StaticFallback() {
  return (
    <div className="flex-1 flex flex-col gap-3 min-h-0">
      <div className="bg-[#111] border border-[#222] rounded-xl p-4 flex-1">
        <p className="text-xs font-semibold text-[#888] mb-4 uppercase tracking-wider">PCR by Workspace</p>
        {[
          { name: 'WS-DIGITAL-NEWS',  pcr: 92, color: '#4caf50' },
          { name: 'WS-ENTERTAINMENT', pcr: 82, color: '#4caf50' },
          { name: 'WS-TECH-ANALYSIS', pcr: 68, color: '#ff9800' },
          { name: 'WS-LIFESTYLE',     pcr: 52, color: '#ff9800' },
          { name: 'WS-SPORTS-LIVE',   pcr: 38, color: '#e63946' },
        ].map((ws) => (
          <div key={ws.name} className="mb-3 last:mb-0">
            <div className="flex justify-between mb-1.5">
              <span className="text-[11px] text-[#a0a0a0] font-medium">{ws.name.replace('WS-', '')}</span>
              <span className="text-[11px] font-bold tabular-nums" style={{ color: ws.color }}>{ws.pcr}%</span>
            </div>
            <div className="h-2 bg-[#0a0a0a] rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: ws.color, opacity: 0.85 }}
                initial={{ width: 0 }}
                animate={{ width: `${ws.pcr}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="bg-[#111] border border-[#222] rounded-xl p-4">
        <p className="text-xs font-semibold text-[#888] mb-3 uppercase tracking-wider">Pipeline Summary</p>
        <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
          {[
            { label: 'Uploaded',  value: '4,179', color: '#64b5f6' },
            { label: 'Processed', value: '4,179', color: '#81c784' },
            { label: 'Published', value: '3,188', color: '#ce93d8' },
          ].map((s) => (
            <div key={s.label} className="text-center p-3 rounded-xl bg-[#0d0d0d] border border-[#1f1f1f]">
              <p className="text-base font-black tabular-nums" style={{ color: s.color }}>{s.value}</p>
              <p className="text-[9px] text-[#555] uppercase tracking-wider mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-1.5">
          <TrendingUp size={11} className="text-[#4caf50]" />
          <p className="text-[10px] text-[#a0a0a0]">Overall PCR: <span className="text-white font-bold">69.8%</span></p>
        </div>
      </div>
    </div>
  )
}

function ChartPreviewArea({ chartData, chartCtx }) {
  const hasData = chartData?.chart_spec && chartData.chart_spec.type !== 'none'
  const hasCtx = !hasData && chartCtx && (chartCtx.image_base64 || chartCtx.data || chartCtx.title)
  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center gap-2">
        <BarChart2 size={15} className="text-[#e63946]" />
        <span className="text-sm font-semibold text-white">Visual Analysis</span>
        {hasData && chartData.sql && (
          <span className="text-[9px] text-[#333] ml-auto font-mono truncate max-w-[160px]" title={chartData.sql}>
            {chartData.sql.trim().slice(0, 60)}…
          </span>
        )}
        {hasCtx && (
          <span className="text-[10px] text-[#64b5f6] ml-auto uppercase tracking-wider">Dropped chart loaded</span>
        )}
        {!hasData && !hasCtx && (
          <span className="text-[10px] text-[#333] ml-auto uppercase tracking-wider">Ask a question to see results</span>
        )}
      </div>

      {hasData ? (
        <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-y-auto">
          {/* Answer summary */}
          {chartData.answer && (
            <div className="bg-[#111] border border-[#1e2a1e] rounded-xl p-4">
              <p className="text-[10px] font-semibold text-[#4caf50] mb-1.5 uppercase tracking-wider">AI Insight</p>
              <div className="text-xs text-[#a0a0a0] leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-strong:text-white">
                <Markdown>{chartData.answer}</Markdown>
              </div>
            </div>
          )}

          {/* Chart — renders based on chart_spec.type */}
          <div className="bg-[#111] border border-[#222] rounded-xl p-4 flex-1">
            {chartData.chart_spec.type === 'number' && (
              <DynamicNumber spec={chartData.chart_spec} />
            )}
            {chartData.chart_spec.type === 'donut' && (
              <>
                <p className="text-xs font-semibold text-[#888] mb-3 uppercase tracking-wider">
                  {String(chartData.chart_spec.y ?? '').replace(/_/g, ' ')} by {String(chartData.chart_spec.x ?? '').replace(/_/g, ' ')}
                </p>
                <DynamicDonut spec={chartData.chart_spec} />
              </>
            )}
            {chartData.chart_spec.type === 'line' && (
              <DynamicLine spec={chartData.chart_spec} />
            )}
            {chartData.chart_spec.type === 'scatter' && (
              <DynamicScatter spec={chartData.chart_spec} />
            )}
            {chartData.chart_spec.type === 'bar' && (
              <>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold text-[#888] uppercase tracking-wider">
                    {String(chartData.chart_spec.y?.[0] ?? '').replace(/_/g, ' ')} by {String(chartData.chart_spec.x ?? '').replace(/_/g, ' ')}
                  </p>
                  <span className="text-[9px] text-[#333]">{chartData.chart_spec.data?.length ?? 0} rows</span>
                </div>
                <DynamicBarChart spec={chartData.chart_spec} />
              </>
            )}
            {chartData.chart_spec.type === 'table' && (
              <>
                <p className="text-xs font-semibold text-[#888] mb-3 uppercase tracking-wider">
                  Query Results ({chartData.chart_spec.data?.length ?? 0} rows)
                </p>
                <DynamicTable spec={chartData.chart_spec} />
              </>
            )}
          </div>
        </div>
      ) : hasCtx ? (
        <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-y-auto">
          {/* Dropped chart title */}
          {chartCtx.title && (
            <div className="bg-[#111] border border-[#1e2a1e] rounded-xl p-4">
              <p className="text-[10px] font-semibold text-[#64b5f6] mb-1.5 uppercase tracking-wider">Attached Chart</p>
              <p className="text-xs text-[#a0a0a0] leading-relaxed">{chartCtx.title}</p>
            </div>
          )}

          {/* Dropped chart image */}
          {chartCtx.image_base64 && (
            <div className="rounded-xl overflow-hidden border border-[#222]">
              <img src={chartCtx.image_base64} alt={chartCtx.title || 'Dropped chart'} className="max-h-60 w-full object-contain bg-[#111]" />
            </div>
          )}

          {/* Dropped chart data as table */}
          {chartCtx.data && Array.isArray(chartCtx.data) && chartCtx.data.length > 0 && (
            <div className="bg-[#111] border border-[#222] rounded-xl p-4 flex-1">
              <p className="text-xs font-semibold text-[#888] mb-3 uppercase tracking-wider">
                Attached Data ({chartCtx.data.length} rows)
              </p>
              <DynamicTable spec={{ data: chartCtx.data }} />
            </div>
          )}

          {/* Hint */}
          <p className="text-[10px] text-[#444] text-center mt-1">
            Ask a question about this data to get AI analysis
          </p>
        </div>
      ) : (
        <StaticFallback />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Guardrails
// ---------------------------------------------------------------------------

// Domain relevance is handled by the backend LLM guardrail.
// No client-side regex filtering - all queries go to the agent for classification.

function sanitizeAnswer(text) {
  if (!text || typeof text !== 'string') return 'No response received.'
  // Strip excessive whitespace
  return text.trim().replace(/\n{3,}/g, '\n\n').slice(0, 4000)
}

// ---------------------------------------------------------------------------
// Placeholder bot response
// ---------------------------------------------------------------------------
const FALLBACK_ERROR_TEXT =
  'Something went wrong - the analytics agent is unavailable. Please try again later.'

// ---------------------------------------------------------------------------
// Shared chat input bar
// ---------------------------------------------------------------------------
function ChatInput({ input, setInput, loading, onSend, inputRef }) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="flex-shrink-0 px-4 pb-4 pt-3 border-t border-[#222]">
      <div className="flex items-end gap-2 bg-[#111] border border-[#2a2a2a] rounded-2xl px-4 py-3 focus-within:border-[#e63946]/50 transition-colors">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about KPIs, workspaces, trends, videos…"
          rows={1}
          disabled={loading}
          className="flex-1 bg-transparent text-sm text-white placeholder-[#444] resize-none outline-none focus:outline-none focus:ring-0 leading-relaxed min-h-[22px] max-h-28 overflow-y-auto disabled:opacity-50"
          style={{ fieldSizing: 'content' }}
        />
        <button
          onClick={onSend}
          disabled={!input.trim() || loading}
          className={[
            'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all',
            input.trim() && !loading
              ? 'bg-[#e63946] text-white hover:bg-[#c62828] shadow-[0_0_12px_rgba(230,57,70,0.35)]'
              : 'bg-[#1f1f1f] text-[#333] cursor-not-allowed',
          ].join(' ')}
        >
          <ArrowRight size={14} />
        </button>
      </div>
      <p className="text-[10px] text-[#2a2a2a] mt-1.5 text-center">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// NLQPanel
// ---------------------------------------------------------------------------
// Stable per-browser session ID - persists across page reloads, unique per device
function getSessionId() {
  const KEY = 'nlq_session_id'
  let id = localStorage.getItem(KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(KEY, id)
  }
  return id
}

export default function NLQPanel({ className = '' }) {
  const nlqOpen    = useAppStore((s) => s.nlqOpen ?? false)
  const setNlqOpen = useAppStore((s) => s.setNlqOpen)
  const currentTicker = useAppStore((s) => s.currentTicker)

  // Stable session ID - wires multi-turn history in the backend agent
  const sessionId = useRef(getSessionId())

  // Sync session ID into store on mount
  useEffect(() => {
    const s = useAppStore.getState()
    if (s.setNlqSessionId) s.setNlqSessionId(sessionId.current)
  }, [])

  // expanded = large centered modal; compact = floating panel (no backdrop, no page block)
  const [expanded, setExpanded] = useState(false)

  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: "Hi! I'm AlphaStream India. Ask me anything about Indian stock signals, insider trades, FII/DII flows, or chart patterns.",
      ts: formatTime(new Date()),
    },
  ])
  const [input, setInput]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [liveThoughts, setLiveThoughts] = useState([])  // SSE thought steps (live)
  const [chartData, setChartData] = useState(null)       // latest chart_spec from agent
  const [chartCtx, setChartCtx]   = useState(null)       // dropped chart image/CSV context
  const messagesEndRef             = useRef(null)
  const inputRef                   = useRef(null)
  const activeSourceRef            = useRef(null)  // current EventSource / abort handle

  // ── Auto page context capture on panel open ──────────────────────────────
  const [currentPageCtx, setCurrentPageCtx] = useState(null)
  useEffect(() => {
    if (nlqOpen) {
      setCurrentPageCtx({ page: 'dashboard', ticker: currentTicker })
    }
  }, [nlqOpen, currentTicker])

  function formatTime(d) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (nlqOpen) setTimeout(() => inputRef.current?.focus(), 350)
  }, [nlqOpen])

  useEffect(() => {
    if (!nlqOpen) setExpanded(false)
  }, [nlqOpen])

  const sendMessage = useCallback(
    (text) => {
      const query = (text ?? input).trim()
      if (!query || loading) return

      setMessages((prev) => [...prev, { role: 'user', text: query, ts: formatTime(new Date()) }])
      setInput('')

      // Close any existing SSE connection
      if (activeSourceRef.current) {
        if (activeSourceRef.current.close) activeSourceRef.current.close()
        if (activeSourceRef.current.abort) activeSourceRef.current.abort()
        activeSourceRef.current = null
      }

      setLoading(true)
      setLiveThoughts([])

      // Common SSE event handler
      let finalReceived = false
      const handleSSEEvent = (event) => {
        if (event.type === 'thought_step') {
          setLiveThoughts((prev) => [...prev, event.data])
        } else if (event.type === 'sql_ready') {
          setLiveThoughts((prev) => [...prev, { node: 'SQL', action: 'Generated SQL', detail: event.data?.slice(0, 120) }])
        } else if (event.type === 'final' && !finalReceived) {
          finalReceived = true
          const answerText = sanitizeAnswer(event.answer)
          const thoughts = (event.thought_steps ?? []).map(
            (s) => `[${s.node}] ${s.action} - ${s.detail ?? ''}`
          )
          setMessages((prev) => [
            ...prev,
            { role: 'bot', text: answerText, thoughts, filters: [], ts: formatTime(new Date()) },
          ])
          if (event.chart_spec && event.chart_spec.type !== 'none') {
            setChartData({ chart_spec: event.chart_spec, sql: event.sql, answer: answerText })
          }
          setLiveThoughts([])
          setLoading(false)
          activeSourceRef.current = null
        } else if (event.type === 'error') {
          setMessages((prev) => [
            ...prev,
            {
              role: 'bot',
              text: event.message || FALLBACK_ERROR_TEXT,
              thoughts: ['Agent returned an error'],
              ts: formatTime(new Date()),
            },
          ])
          setLiveThoughts([])
          setLoading(false)
          activeSourceRef.current = null
        } else if (event.type === 'done') {
          setLiveThoughts([])
          setLoading(false)
          activeSourceRef.current = null
        }
      }

      // SSE streaming via GET EventSource
      if (typeof EventSource !== 'undefined') {
        const source = apiService.openNLQStream(query, sessionId.current, handleSSEEvent)
        activeSourceRef.current = source
      } else {
        // Fallback: blocking POST
        apiService.nlqQuery(query, sessionId.current)
          .then((d) => {
            const answerText = sanitizeAnswer(d.answer)
            const thoughts = d.thought_process
              ? d.thought_process.split('\n').filter(Boolean)
              : []
            setMessages((prev) => [
              ...prev,
              { role: 'bot', text: answerText, thoughts, filters: [], ts: formatTime(new Date()) },
            ])
          })
          .catch((err) => {
            setMessages((prev) => [
              ...prev,
              { role: 'bot', text: err.message || FALLBACK_ERROR_TEXT, thoughts: ['Request failed'], ts: formatTime(new Date()) },
            ])
          })
          .finally(() => { setLoading(false) })
      }
    },
    [input, loading]
  )

  const closePanel = () => {
    setNlqOpen(false)
    setExpanded(false)
  }

  // ── Compact panel (stage 1): floating bottom-right, NO backdrop ───────────
  const CompactPanel = (
    <motion.div
      key="compact"
      initial={{ opacity: 0, y: 20, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 16, scale: 0.96 }}
      transition={{ type: 'spring', stiffness: 380, damping: 36 }}
      className={[
        'fixed z-50',
        'bottom-20 right-4 left-4 sm:left-auto sm:right-8 sm:bottom-28',
        'w-auto sm:w-[420px]',
        'bg-[#0f0f0f] border border-[#272727]',
        'rounded-2xl flex flex-col overflow-hidden',
        'shadow-[0_24px_60px_rgba(0,0,0,0.7),0_0_0_1px_rgba(255,255,255,0.04)]',
        className,
      ].join(' ')}
      style={{ height: 'min(520px, calc(100vh - 120px))' }}
    >
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-[#222]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-[#e63946]/10 border border-[#e63946]/30 flex items-center justify-center">
            <Sparkles size={14} className="text-[#e63946]" />
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-none">Ask AlphaStream</p>
            <p className="text-[10px] text-[#555] mt-0.5 leading-none">Powered by Claude · Analytics</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setExpanded(true)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[#555] hover:text-white hover:bg-[#1f1f1f] transition-colors"
            title="Expand for charts and full view"
          >
            <Maximize2 size={13} />
          </button>
          <button
            onClick={closePanel}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-[#555] hover:text-[#aaa] hover:bg-[#1f1f1f] transition-colors"
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Context banner */}
      <ContextBanner pageContext={currentPageCtx} chartContext={chartCtx} onClearChart={() => setChartCtx(null)} />

      {/* Quick prompts - context-aware */}
      <div className="flex-shrink-0 px-4 py-2.5 border-b border-[#1a1a1a] bg-[#0d0d0d]">
        <div className="flex flex-wrap gap-1.5">
          {(chartCtx
            ? CONTEXT_PROMPTS.chart_dropped
            : CONTEXT_PROMPTS.default || QUICK_PROMPTS
          ).slice(0, 2).map((p) => (
            <button
              key={p}
              onClick={() => sendMessage(p)}
              disabled={loading}
              className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#1a1a1a] border border-[#2a2a2a] text-[#888] hover:text-white hover:border-[#e63946]/40 hover:bg-[#e63946]/5 transition-colors disabled:opacity-40"
            >
              {p}
            </button>
          ))}
          <button
            onClick={() => setExpanded(true)}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#e63946]/10 border border-[#e63946]/25 text-[#e63946] hover:bg-[#e63946]/20 transition-colors"
          >
            <Maximize2 size={10} />
            Charts
          </button>
        </div>
      </div>

      {/* Chart drop zone */}
      <ChartDropZone onDrop={(ctx) => { setChartCtx(ctx); setInput('Analyze this chart') }} />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {loading && (
          <div className="flex items-start gap-2.5">
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#e63946]/15 border border-[#e63946]/25 flex items-center justify-center">
              <Bot size={13} className="text-[#e63946]" />
            </div>
            <div className="flex-1 min-w-0">
              <TypingIndicator />
              <LiveThoughtDisplay steps={liveThoughts} />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <ChatInput
        input={input}
        setInput={setInput}
        loading={loading}
        onSend={() => sendMessage()}
        inputRef={inputRef}
      />
    </motion.div>
  )

  // ── Expanded modal (stage 2): large centered, WITH backdrop ──────────────
  const ExpandedModal = (
    <>
      {/* Backdrop - only for expanded modal */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        onClick={() => setExpanded(false)}
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-[3px]"
      />

      <motion.div
        key="expanded"
        initial={{ opacity: 0, scale: 0.95, y: 24 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 24 }}
        transition={{ type: 'spring', stiffness: 280, damping: 28 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-6"
        onClick={(e) => e.target === e.currentTarget && setExpanded(false)}
      >
        <div
          className="relative w-full max-w-[1300px] bg-[#0d0d0d] border border-[#2a2a2a] rounded-2xl sm:rounded-3xl flex flex-col overflow-hidden"
          style={{
            height: 'min(90vh, 860px)',
            boxShadow: '0 32px 100px rgba(0,0,0,0.85), 0 0 0 1px rgba(255,255,255,0.05)',
          }}
        >
          {/* Modal header */}
          <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-[#222]">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#e63946]/12 border border-[#e63946]/30 flex items-center justify-center">
                <Sparkles size={17} className="text-[#e63946]" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Ask AlphaStream</h2>
                <p className="text-[10px] text-[#555] uppercase tracking-wider">Full analytics view · Claude Sonnet</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setExpanded(false)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium text-[#555] hover:text-white hover:bg-[#1f1f1f] transition-colors"
                title="Back to compact panel"
              >
                <Minimize2 size={12} />
                Compact
              </button>
              <button
                onClick={closePanel}
                className="w-8 h-8 rounded-xl flex items-center justify-center text-[#555] hover:text-[#aaa] hover:bg-[#1f1f1f] transition-colors"
              >
                <X size={15} />
              </button>
            </div>
          </div>

          {/* Context banner (expanded) */}
          <ContextBanner pageContext={currentPageCtx} chartContext={chartCtx} onClearChart={() => setChartCtx(null)} />

          {/* Quick prompts - context-aware */}
          <div className="flex-shrink-0 flex items-center gap-2 px-6 py-3 border-b border-[#1a1a1a] bg-[#0a0a0a]">
            <span className="text-[10px] text-[#555] uppercase tracking-wider flex-shrink-0">Try:</span>
            {(chartCtx ? CONTEXT_PROMPTS.chart_dropped : CONTEXT_PROMPTS.default || QUICK_PROMPTS).map((p) => (
              <button
                key={p}
                onClick={() => sendMessage(p)}
                disabled={loading}
                className="inline-flex items-center px-3 py-1.5 rounded-full text-[11px] font-medium bg-[#1a1a1a] border border-[#2a2a2a] text-[#888] hover:text-white hover:border-[#e63946]/40 hover:bg-[#e63946]/5 transition-colors disabled:opacity-40"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Body - split: chat (left) + charts (right). Stacks on mobile. */}
          <div className="flex-1 flex flex-col md:flex-row min-h-0">
            {/* Chat column */}
            <div className="flex flex-col w-full md:w-[480px] md:flex-shrink-0 border-b md:border-b-0 md:border-r border-[#1e1e1e] min-h-0 flex-1 md:flex-initial">
              <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
                {messages.map((msg, i) => (
                  <MessageBubble key={i} msg={msg} />
                ))}
                {loading && (
                  <div className="flex items-start gap-2.5">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#e63946]/15 border border-[#e63946]/25 flex items-center justify-center">
                      <Bot size={13} className="text-[#e63946]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <TypingIndicator />
                      <LiveThoughtDisplay steps={liveThoughts} />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
              <ChatInput
                input={input}
                setInput={setInput}
                loading={loading}
                onSend={() => sendMessage()}
                inputRef={inputRef}
              />
            </div>

            {/* Charts / visual column — hidden on mobile */}
            <div className="hidden md:flex flex-1 overflow-y-auto px-4 sm:px-6 py-5 bg-[#090909] flex-col">
              <ChartDropZone onDrop={(ctx) => { setChartCtx(ctx); setInput('Analyze this chart') }} />
              <ChartPreviewArea chartData={chartData} chartCtx={chartCtx} />
            </div>
          </div>
        </div>
      </motion.div>
    </>
  )

  return (
    <>
      {/* Compact panel - no backdrop so page stays interactive */}
      <AnimatePresence>
        {nlqOpen && !expanded && CompactPanel}
      </AnimatePresence>

      {/* Expanded modal - with backdrop */}
      <AnimatePresence>
        {nlqOpen && expanded && ExpandedModal}
      </AnimatePresence>
    </>
  )
}
