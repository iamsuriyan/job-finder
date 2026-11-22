import React, { useState } from 'react'
import {
  Search,
  ExternalLink,
  Copy,
  Check,
  RefreshCw,
  Zap,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from 'lucide-react'
import { Article } from '../types'

interface DealsFeedProps {
  articles: Article[]
  loading: boolean
  total: number
  page: number
  setPage: (page: number) => void
  onRefresh: () => void
  onDraftJobEnquiry: (article: Article) => void
  generatingArticleId: string | null
  showToast: (msg: string) => void
  feedFilter: string
  setFeedFilter: (feed: string) => void
  searchQuery: string
  setSearchQuery: (query: string) => void
  feeds: { name: string }[]
}

const STAGE_STYLES: Record<string, string> = {
  'pre-seed': 'bg-zinc-100 text-zinc-600 border-zinc-200',
  seed: 'bg-amber-50 text-amber-700 border-amber-200',
  'series a': 'bg-blue-50 text-blue-700 border-blue-200',
  'series b': 'bg-purple-50 text-purple-700 border-purple-200',
  'series c': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'series d': 'bg-rose-50 text-rose-700 border-rose-200',
}

function getStageStyle(stage?: string): string {
  if (!stage) return 'bg-zinc-100 text-zinc-500 border-zinc-200'
  const key = stage.toLowerCase()
  for (const [pattern, style] of Object.entries(STAGE_STYLES)) {
    if (key.includes(pattern)) return style
  }
  return 'bg-zinc-100 text-zinc-500 border-zinc-200'
}

function formatAmount(amount?: number, currency?: string): string | null {
  if (amount == null) return null
  const curr = currency || 'USD'
  if (amount >= 1_000_000) {
    return `${curr} ${(amount / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`
  }
  if (amount >= 1_000) {
    return `${curr} ${(amount / 1_000).toFixed(0)}K`
  }
  return `${curr} ${amount}`
}

function formatDate(isoString?: string): string {
  if (!isoString) return 'Recently'
  try {
    const d = new Date(isoString)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return isoString
  }
}

const SkeletonCard = () => (
  <div className="bg-white border border-zinc-100 rounded-xl shadow-sm p-5 space-y-3">
    <div className="flex items-center gap-2">
      <div className="skeleton h-5 w-32" />
      <div className="skeleton h-5 w-20" />
    </div>
    <div className="skeleton h-4 w-full" />
    <div className="skeleton h-4 w-3/4" />
    <div className="flex gap-2 pt-1">
      <div className="skeleton h-6 w-28 rounded-full" />
      <div className="skeleton h-6 w-24 rounded-full" />
    </div>
  </div>
)

export const DealsFeed: React.FC<DealsFeedProps> = ({
  articles,
  loading,
  total,
  page,
  setPage,
  onRefresh,
  onDraftJobEnquiry,
  generatingArticleId,
  showToast,
  feedFilter,
  setFeedFilter,
  searchQuery,
  setSearchQuery,
  feeds,
}) => {
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null)
  const totalPages = Math.ceil(total / 24)

  const handleCopyEmail = (email: string, e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(email)
    setCopiedEmail(email)
    showToast(`Copied ${email}`)
    setTimeout(() => setCopiedEmail(null), 2000)
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900 tracking-tight flex items-center gap-2.5">
            Funding Deals
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-violet-50 border border-violet-200 text-violet-700 text-xs font-mono font-semibold">
              {total}
            </span>
          </h1>
          <p className="text-sm text-zinc-400 mt-0.5">Real-time verified startup funding rounds</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search startup or founder..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 py-2 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all w-56 placeholder:text-zinc-400"
            />
          </div>

          {/* Feed filter */}
          <select
            value={feedFilter}
            onChange={(e) => setFeedFilter(e.target.value)}
            className="py-2 px-3 text-sm bg-white border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all text-zinc-700"
          >
            <option value="">All sources</option>
            {feeds.map((f) => (
              <option key={f.name} value={f.name}>{f.name}</option>
            ))}
          </select>

          {/* Refresh */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 bg-white border border-zinc-200 rounded-lg text-zinc-500 hover:text-zinc-800 hover:bg-zinc-50 hover:border-zinc-300 transition-all disabled:opacity-50"
            title="Refresh feed"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : articles.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-12 h-12 rounded-2xl bg-zinc-100 flex items-center justify-center mb-4">
            <Zap size={22} className="text-zinc-400" />
          </div>
          <h3 className="text-base font-semibold text-zinc-700 mb-1">No deals found</h3>
          <p className="text-sm text-zinc-400 max-w-xs">
            {searchQuery || feedFilter
              ? 'Try clearing your filters to see all funding rounds.'
              : 'Funding deals will appear here as they are discovered.'}
          </p>
          {(searchQuery || feedFilter) && (
            <button
              onClick={() => { setSearchQuery(''); setFeedFilter('') }}
              className="mt-4 px-4 py-2 text-sm font-medium bg-zinc-900 text-white rounded-lg hover:bg-zinc-800 transition-all"
            >
              Clear filters
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {articles.map((article) => {
            const isGenerating = generatingArticleId === article.id
            const emails = article.emails || []
            const amount = formatAmount(article.amount, article.currency)

            return (
              <div
                key={article.id}
                className="bg-white border border-zinc-100 rounded-xl shadow-sm hover:shadow-md hover:border-zinc-200 transition-all duration-200 p-5 flex flex-col gap-3"
              >
                {/* Top: Company + Stage + Amount */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-zinc-900 truncate">
                        {article.company || 'Unknown Company'}
                      </span>
                      {article.stage && (
                        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${getStageStyle(article.stage)}`}>
                          {article.stage}
                        </span>
                      )}
                    </div>
                    {amount && (
                      <span className="text-base font-bold font-mono text-violet-700 mt-0.5 block">
                        {amount}
                      </span>
                    )}
                  </div>
                </div>

                {/* Article title */}
                <p className="text-sm text-zinc-600 leading-snug line-clamp-2">
                  {article.title}
                </p>

                {/* Meta: source + date + link */}
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  {article.feed_name && (
                    <span className="font-medium text-zinc-500">{article.feed_name}</span>
                  )}
                  {article.feed_name && <span>·</span>}
                  <span>{formatDate(article.published_at)}</span>
                  <a
                    href={article.link}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-auto flex items-center gap-1 text-zinc-400 hover:text-violet-600 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink size={12} />
                  </a>
                </div>

                {/* Founder emails */}
                {emails.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {emails.map((em) => (
                      <button
                        key={em.email}
                        onClick={(e) => handleCopyEmail(em.email, e)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-violet-50 border border-violet-200 text-violet-700 text-[11px] font-mono hover:bg-violet-100 transition-colors"
                        title={`Copy ${em.email}`}
                      >
                        {copiedEmail === em.email ? (
                          <Check size={10} className="text-emerald-500" />
                        ) : (
                          <Copy size={10} />
                        )}
                        <span>{em.email}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* CTA */}
                <div className="pt-1 mt-auto">
                  <button
                    onClick={() => onDraftJobEnquiry(article)}
                    disabled={isGenerating}
                    className="w-full flex items-center justify-center gap-2 py-2 px-4 text-sm font-medium rounded-lg border border-zinc-200 bg-zinc-50 hover:bg-zinc-900 hover:text-white hover:border-zinc-900 text-zinc-700 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        <span>Drafting...</span>
                      </>
                    ) : (
                      <>
                        <Zap size={14} className="text-violet-500" />
                        <span>Draft Outreach</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-sm text-zinc-400">
            Page {page} of {totalPages} · {total} deals
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium bg-white border border-zinc-200 rounded-lg text-zinc-600 hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft size={14} />
              Prev
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium bg-white border border-zinc-200 rounded-lg text-zinc-600 hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              Next
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
