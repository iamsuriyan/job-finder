import React, { useState } from 'react'
import { Rss, CheckCircle2, AlertTriangle, Play, RefreshCw, Clock, ExternalLink } from 'lucide-react'
import { FeedInfo } from '../types'
import { testFeed } from '../api/client'

interface FeedsMonitorProps {
  feeds: FeedInfo[]
  loading: boolean
  onRefresh: () => void
  showToast: (msg: string) => void
}

export const FeedsMonitor: React.FC<FeedsMonitorProps> = ({
  feeds,
  loading,
  onRefresh,
  showToast,
}) => {
  const [testingUrl, setTestingUrl] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<any | null>(null)

  const handleTestFeed = async (feedUrl: string) => {
    setTestingUrl(feedUrl)
    setTestResult(null)
    try {
      const res = await testFeed(feedUrl)
      setTestResult(res)
      showToast(res.ok ? 'Feed test passed!' : 'Feed test failed!')
    } catch (err: any) {
      showToast(`Feed inspection error: ${err.message}`)
    } finally {
      setTestingUrl(null)
    }
  }

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return 'Never'
    try {
      const d = new Date(isoString)
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="space-y-6">
      <div className="p-6 rounded-2xl border border-zinc-200 bg-white shadow-xs flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-950 flex items-center gap-2">
            <span>RSS & Atom Sources Health</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-100 border border-emerald-200 font-mono text-emerald-800 font-semibold">
              {feeds.filter((f) => f.healthy).length} / {feeds.length} Healthy
            </span>
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Polite HTTP polling with ETag and If-Modified-Since caching to respect publishers and minimize bandwidth.
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 font-mono text-xs font-medium text-zinc-700 transition shadow-xs"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh States</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {feeds.map((feed) => {
          const isTesting = testingUrl === feed.url

          return (
            <div
              key={feed.name}
              className="p-5 rounded-2xl border border-zinc-200 bg-white hover:border-zinc-300 transition shadow-xs flex flex-col justify-between gap-4"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-zinc-950">{feed.name}</span>
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold ${
                        feed.healthy
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-red-50 text-red-700 border border-red-200'
                      }`}
                    >
                      {feed.healthy ? <CheckCircle2 size={10} /> : <AlertTriangle size={10} />}
                      <span>{feed.healthy ? 'HEALTHY' : 'DEGRADED'}</span>
                    </span>
                  </div>

                  <a
                    href={feed.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-zinc-400 hover:text-zinc-700 transition"
                    title="Open RSS XML feed in new tab"
                  >
                    <ExternalLink size={13} />
                  </a>
                </div>

                <div className="text-[11px] font-mono text-zinc-500 truncate mb-4">{feed.url}</div>

                <div className="p-3 rounded-xl border border-zinc-100 bg-zinc-50/70 space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between text-zinc-600">
                    <span>Last Successful Sync:</span>
                    <span className="font-semibold text-zinc-900">{formatDate(feed.last_ok_at)}</span>
                  </div>
                  <div className="flex justify-between text-zinc-600">
                    <span>Consecutive Errors:</span>
                    <span
                      className={`font-semibold ${
                        feed.consecutive_failures > 0 ? 'text-amber-600' : 'text-zinc-900'
                      }`}
                    >
                      {feed.consecutive_failures}
                    </span>
                  </div>
                  <div className="flex justify-between text-zinc-600">
                    <span>HTTP ETag Cache:</span>
                    <span className="font-mono text-[10px] text-zinc-700 truncate max-w-[150px]">
                      {feed.etag ? 'Stored (304 Not Modified)' : 'None'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-zinc-100 flex items-center justify-between">
                <span className="text-[11px] font-mono text-zinc-400">Polled every 20m</span>

                <button
                  onClick={() => handleTestFeed(feed.url)}
                  disabled={isTesting}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-800 font-mono text-xs font-medium transition shadow-xs disabled:opacity-50"
                >
                  <Play size={11} className={isTesting ? 'animate-spin' : ''} />
                  <span>{isTesting ? 'Inspecting...' : 'Test Feed Live'}</span>
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Test Result Drawer / Modal */}
      {testResult && (
        <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-950 text-white shadow-xl space-y-3 animate-fadeIn font-mono text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
            <span className="font-bold flex items-center gap-2">
              <span className={testResult.ok ? 'text-emerald-400' : 'text-red-400'}>
                {testResult.ok ? '✓ LIVE FEED TEST SUCCEEDED' : '✗ FEED TEST FAILED'}
              </span>
            </span>
            <button
              onClick={() => setTestResult(null)}
              className="text-zinc-400 hover:text-white"
            >
              Dismiss ✕
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px]">
            <div>
              <span className="text-zinc-400 block">Status Code</span>
              <span className="font-bold">{testResult.status_code || 'N/A'}</span>
            </div>
            <div>
              <span className="text-zinc-400 block">Total Entries</span>
              <span className="font-bold">{testResult.item_count || 0}</span>
            </div>
            <div>
              <span className="text-zinc-400 block">Feed Format</span>
              <span className="font-bold uppercase">{testResult.feed_format || 'RSS/Atom'}</span>
            </div>
            <div>
              <span className="text-zinc-400 block">HTTP Latency</span>
              <span className="font-bold">{testResult.latency_ms ? `${testResult.latency_ms} ms` : 'Fast'}</span>
            </div>
          </div>

          {testResult.latest_title && (
            <div className="pt-2 text-[11px] text-zinc-300">
              <span className="text-zinc-400">Latest Discovered Article: </span>
              <strong>{testResult.latest_title}</strong>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
