import React, { useState } from 'react'
import {
  Search,
  ExternalLink,
  Mail,
  Copy,
  Check,
  Globe,
  Sparkles,
  RefreshCw,
  Building,
  DollarSign,
  Tag,
} from 'lucide-react'
import { Article, DraftEmail } from '../types'

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

  const handleCopyEmail = (email: string, e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(email)
    setCopiedEmail(email)
    showToast(`Copied ${email} to clipboard!`)
    setTimeout(() => setCopiedEmail(null), 2000)
  }

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'Just now'
    try {
      const date = new Date(isoString)
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header & Search Bar */}
      <div className="p-6 rounded-2xl border border-zinc-200 bg-white shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-zinc-950 flex items-center gap-2">
            <span>Verified Startup Funding Deals</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-zinc-100 border border-zinc-200 font-mono text-zinc-600 font-semibold">
              {total} Rounds
            </span>
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Real-time feed deduplicated across tech outlets with automated founder email extraction.
          </p>
        </div>

        {/* Search & Filter Controls */}
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              placeholder="Search startup, founder, or round..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 text-xs font-mono rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-900 focus:outline-none transition shadow-xs"
            />
          </div>

          <select
            value={feedFilter}
            onChange={(e) => setFeedFilter(e.target.value)}
            className="px-3 py-2 text-xs font-mono rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 focus:border-zinc-900 focus:outline-none transition shadow-xs"
          >
            <option value="">All Outlets (5)</option>
            {feeds.map((f) => (
              <option key={f.name} value={f.name}>
                {f.name}
              </option>
            ))}
          </select>

          <button
            onClick={onRefresh}
            className="p-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-700 transition shadow-xs"
            title="Refresh funding feed"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* In-Flight Draft Generation Banner */}
      {generatingArticleId && (
        <div className="p-4 rounded-xl border border-zinc-900 bg-zinc-950 text-white flex items-center justify-between shadow-md animate-fadeIn">
          <div className="flex items-center gap-3 text-xs font-mono">
            <div className="w-5 h-5 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
            <span>
              Generating personalized cold outreach draft... Extracting founder emails & validating MX records...
            </span>
          </div>
          <span className="text-[11px] font-mono text-zinc-400">Suriyan.pdf attached</span>
        </div>
      )}

      {/* Articles Grid */}
      {loading && articles.length === 0 ? (
        <div className="py-24 text-center border-2 border-dashed border-zinc-200 rounded-2xl bg-white">
          <div className="w-7 h-7 mx-auto mb-3 border-2 border-zinc-900 border-t-transparent rounded-full animate-spin"></div>
          <p className="font-mono text-xs text-zinc-500">Loading verified funding announcements...</p>
        </div>
      ) : articles.length === 0 ? (
        <div className="py-24 text-center border-2 border-dashed border-zinc-200 rounded-2xl bg-white">
          <p className="font-mono text-sm text-zinc-700 font-semibold">No deals match your search criteria.</p>
          <p className="font-mono text-xs text-zinc-400 mt-1">Try resetting the keyword search or feed filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {articles.map((article) => {
            const isGenerating = generatingArticleId === article.id

            return (
              <div
                key={article.id}
                className="flex flex-col justify-between p-5 rounded-2xl border border-zinc-200 bg-white hover:border-zinc-400 transition-all duration-200 shadow-xs hover:shadow-md group"
              >
                <div>
                  {/* Top Bar: Feed & Published Date */}
                  <div className="flex items-center justify-between text-[11px] font-mono text-zinc-600 mb-3">
                    <span className="px-2 py-0.5 rounded-md border border-zinc-200 bg-zinc-100 text-zinc-800 font-semibold">
                      {article.feed_name}
                    </span>
                    <span>{formatDate(article.published_at || article.first_seen_at)}</span>
                  </div>

                  {/* Title */}
                  <h2 className="font-bold text-sm leading-snug text-zinc-950 group-hover:text-black transition">
                    {article.title}
                  </h2>

                  {/* Extracted Details Tags */}
                  {(article.company || article.amount || article.stage || article.sector) && (
                    <div className="mt-3 flex flex-wrap gap-1.5 font-mono text-xs">
                      {article.company && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-zinc-950 text-white font-semibold">
                          <Building size={11} /> {article.company}
                        </span>
                      )}
                      {article.amount && (
                        <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-md border border-zinc-300 bg-zinc-100 text-zinc-950 font-bold">
                          <DollarSign size={11} /> {article.amount} {article.currency || 'USD'}
                        </span>
                      )}
                      {article.stage && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md border border-zinc-200 bg-zinc-50 text-zinc-700">
                          <Tag size={10} /> {article.stage}
                        </span>
                      )}
                      {article.sector && (
                        <span className="px-2 py-0.5 rounded-md border border-zinc-200 text-zinc-600 text-[11px]">
                          {article.sector}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Summary Snippet */}
                  {article.summary && (
                    <p className="mt-3 text-xs text-zinc-600 line-clamp-2 leading-relaxed">
                      {article.summary}
                    </p>
                  )}

                  {/* Discovered Founder Emails Pill Block */}
                  {article.emails && article.emails.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-zinc-100 font-mono text-xs">
                      <div className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2 flex items-center justify-between font-semibold">
                        <span className="flex items-center gap-1">
                          <Sparkles size={11} className="text-zinc-600" />
                          Founding Team & Emails
                        </span>
                        {article.domain && (
                          <span className="inline-flex items-center gap-1 text-zinc-600 font-semibold lowercase">
                            <Globe size={10} />
                            {article.domain}
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap gap-1.5">
                        {article.emails.slice(0, 2).map((em) => {
                          const isCopied = copiedEmail === em.email
                          return (
                            <button
                              key={em.email}
                              onClick={(e) => handleCopyEmail(em.email, e)}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-zinc-200 bg-zinc-50 hover:bg-zinc-100 text-zinc-900 transition text-[11px] font-medium shadow-xs"
                              title="Click to copy verified email"
                            >
                              <span>{em.email}</span>
                              {isCopied ? (
                                <Check size={11} className="text-emerald-600" />
                              ) : (
                                <Copy size={11} className="text-zinc-400 hover:text-zinc-700" />
                              )}
                            </button>
                          )
                        })}

                        {article.emails.length > 2 && (
                          <span className="text-[10px] text-zinc-600 self-center font-semibold">
                            +{article.emails.length - 2} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Bottom Card Actions */}
                <div className="mt-5 pt-3.5 border-t border-zinc-100 flex items-center justify-between text-xs font-mono">
                  <button
                    onClick={() => onDraftJobEnquiry(article)}
                    disabled={isGenerating}
                    className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-zinc-950 hover:bg-zinc-800 text-white font-medium transition shadow-xs disabled:opacity-50"
                  >
                    <Mail size={13} />
                    <span>{isGenerating ? 'Generating...' : 'Draft Job Enquiry'}</span>
                  </button>

                  <a
                    href={article.link}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-zinc-600 hover:text-zinc-950 font-medium transition"
                  >
                    <span>Read Deal</span>
                    <ExternalLink size={12} />
                  </a>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
