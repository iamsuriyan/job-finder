import React, { useState } from 'react'
import { CheckCircle2, AlertTriangle, Play, RefreshCw, ExternalLink, Loader2 } from 'lucide-react'
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

  const healthyCount = feeds.filter((f) => f.healthy).length

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900 tracking-tight flex items-center gap-2.5">
            Feed Sources Health
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-mono font-semibold">
              {healthyCount} / {feeds.length} Healthy
            </span>
          </h1>
          <p className="text-sm text-zinc-400 mt-0.5">
            Polite HTTP polling with ETag and If-Modified-Since caching to minimize bandwidth
          </p>
        </div>

        <button
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-xs font-medium text-zinc-700 transition shadow-xs disabled:opacity-50 self-start sm:self-auto"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          <span>Refresh States</span>
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {feeds.map((feed) => {
          const isTesting = testingUrl === feed.url

          return (
            <div
              key={feed.name}
              className="bg-white border border-zinc-100 rounded-xl shadow-sm hover:shadow-md hover:border-zinc-200 transition-all duration-200 p-5 flex flex-col justify-between gap-4"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-zinc-900">{feed.name}</span>
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
                    className="text-zinc-400 hover:text-violet-600 transition"
                    title="Open RSS XML feed in new tab"
                  >
                    <ExternalLink size={13} />
                  </a>
                </div>

                <div className="text-xs text-zinc-400 truncate mb-4 font-mono">{feed.url}</div>

                <div className="p-3 rounded-lg border border-zinc-100 bg-zinc-50/70 space-y-1.5 text-xs">
                  <div className="flex justify-between text-zinc-500">
                    <span>Last Successful Sync:</span>
                    <span className="font-medium text-zinc-800">{formatDate(feed.last_ok_at)}</span>
                  </div>
                  <div className="flex justify-between text-zinc-500">
                    <span>Consecutive Errors:</span>
                    <span
                      className={`font-semibold ${
                        feed.consecutive_failures > 0 ? 'text-amber-600' : 'text-zinc-800'
                      }`}
                    >
                      {feed.consecutive_failures}
                    </span>
                  </div>
                  <div className="flex justify-between text-zinc-500">
                    <span>HTTP ETag Cache:</span>
                    <span className="font-mono text-[11px] text-zinc-700 truncate max-w-[160px]">
                      {feed.etag ? 'Stored (304 Not Modified)' : 'None'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-zinc-100 flex items-center justify-between">
                <span className="text-xs text-zinc-400">Polled every 20m</span>

                <button
                  onClick={() => handleTestFeed(feed.url)}
                  disabled={isTesting}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition shadow-xs disabled:opacity-50"
                >
                  {isTesting ? <Loader2 size={12} className="animate-spin" /> : <Play size={11} />}
                  <span>{isTesting ? 'Testing...' : 'Test Feed Live'}</span>
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Test Result Drawer */}
      {testResult && (
        <div className="p-5 rounded-xl border border-zinc-900 bg-zinc-900 text-white shadow-lg space-y-3 animate-fade-in text-xs font-mono">
          <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
            <span className="font-semibold flex items-center gap-2">
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

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-zinc-400 block text-[10px]">Status Code</span>
              <span className="font-bold">{testResult.status_code || 'N/A'}</span>
            </div>
            <div>
              <span className="text-zinc-400 block text-[10px]">Total Entries</span>
              <span className="font-bold">{testResult.item_count || 0}</span>
            </div>
            <div>
              <span className="text-zinc-400 block text-[10px]">Feed Format</span>
              <span className="font-bold uppercase">{testResult.feed_format || 'RSS/Atom'}</span>
            </div>
            <div>
              <span className="text-zinc-400 block text-[10px]">HTTP Latency</span>
              <span className="font-bold">{testResult.latency_ms ? `${testResult.latency_ms} ms` : 'Fast'}</span>
            </div>
          </div>

          {testResult.latest_title && (
            <div className="pt-2 text-zinc-300">
              <span className="text-zinc-400">Latest Discovered Article: </span>
              <strong>{testResult.latest_title}</strong>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
