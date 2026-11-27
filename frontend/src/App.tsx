import React, { useState, useEffect, useMemo } from 'react'
import { Sidebar } from './components/Sidebar'
import { DealsFeed } from './components/DealsFeed'
import { OutboxReview } from './components/OutboxReview'
import { FeedsMonitor } from './components/FeedsMonitor'
import { CandidateProfile } from './components/CandidateProfile'
import { SmtpSettings } from './components/SmtpSettings'
import { EmailModal } from './components/EmailModal'
import { Toast } from './components/Toast'
import {
  Article,
  CandidateProfile as ICandidateProfile,
  ContactedRecipient,
  DraftEmail,
  DraftStats,
  FeedInfo,
  ResumeStatus,
  ConfigSummary,
  ScraperStatus,
} from './types'
import {
  fetchArticles,
  fetchOutbox,
  fetchFeeds,
  fetchConfig,
  fetchResumeStatus,
  fetchCandidateProfile,
  fetchScraperStatus,
  triggerScraperPoll,
  generateDraft,
  updateDraft,
  deleteDraft,
  dismissArticle,
  sendDraft,
} from './api/client'
import { ExternalLink, RefreshCw, Loader2, Activity } from 'lucide-react'

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('deals')
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false)

  // Data states
  const [articles, setArticles] = useState<Article[]>([])
  const [totalArticles, setTotalArticles] = useState<number>(0)
  const [articlesPage, setArticlesPage] = useState<number>(1)
  const [loadingArticles, setLoadingArticles] = useState<boolean>(false)
  const [feedFilter, setFeedFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [stageFilter, setStageFilter] = useState<string>('all_early')

  const [drafts, setDrafts] = useState<DraftEmail[]>([])
  const [outboxStats, setOutboxStats] = useState<DraftStats>({ total: 0, draft: 0, sent: 0, failed: 0 })
  const [contactedRecipients, setContactedRecipients] = useState<Record<string, ContactedRecipient>>({})
  const [loadingOutbox, setLoadingOutbox] = useState<boolean>(false)
  const [outboxStatusFilter, setOutboxStatusFilter] = useState<string>('')

  const [feeds, setFeeds] = useState<FeedInfo[]>([])
  const [loadingFeeds, setLoadingFeeds] = useState<boolean>(false)

  const [resumeStatus, setResumeStatus] = useState<ResumeStatus | null>(null)
  const [config, setConfig] = useState<ConfigSummary | null>(null)
  const [candidateProfile, setCandidateProfile] = useState<ICandidateProfile | null>(null)

  // Live background scraping status
  const [scraperStatus, setScraperStatus] = useState<ScraperStatus | null>(null)
  const [triggeringScrape, setTriggeringScrape] = useState<boolean>(false)
  const prevScrapingRef = React.useRef<boolean>(false)

  // Draft modal & interaction states
  const [selectedDraft, setSelectedDraft] = useState<DraftEmail | null>(null)
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false)
  const [modalTab, setModalTab] = useState<'read' | 'edit'>('read')
  const [generatingArticleId, setGeneratingArticleId] = useState<string | null>(null)

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => {
      setToastMessage(null)
    }, 3500)
  }

  // Load articles
  const loadArticles = async () => {
    setLoadingArticles(true)
    try {
      const res = await fetchArticles({
        page: articlesPage,
        limit: 24,
        matched_only: true,
        search: searchQuery || undefined,
        feed: feedFilter || undefined,
        stage: stageFilter === 'all' ? undefined : stageFilter,
      })
      setArticles(res.items || [])
      setTotalArticles(res.total || 0)
    } catch (err: unknown) {
      showToast(`Failed to load funding deals: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoadingArticles(false)
    }
  }

  // Load outbox drafts
  const loadOutbox = async () => {
    setLoadingOutbox(true)
    try {
      const res = await fetchOutbox(outboxStatusFilter || undefined)
      setDrafts(res.items || [])
      if (res.stats) {
        setOutboxStats(res.stats)
      }
      if (res.contacted_recipients) {
        setContactedRecipients(res.contacted_recipients)
      }
    } catch (err: unknown) {
      showToast(`Failed to load outbox: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoadingOutbox(false)
    }
  }

  // Load feeds
  const loadFeeds = async () => {
    setLoadingFeeds(true)
    try {
      const items = await fetchFeeds()
      setFeeds(items || [])
    } catch (err: unknown) {
      showToast(`Failed to load feeds: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoadingFeeds(false)
    }
  }

  // Load metadata
  const loadMetadata = async () => {
    try {
      const [rStatus, cfg, cand] = await Promise.all([
        fetchResumeStatus().catch(() => null),
        fetchConfig().catch(() => null),
        fetchCandidateProfile().catch(() => null),
      ])
      if (rStatus) setResumeStatus(rStatus)
      if (cfg) setConfig(cfg)
      if (cand) setCandidateProfile(cand)
    } catch {
      // Ignore initial metadata fetch errors
    }
  }

  useEffect(() => {
    loadArticles()
  }, [articlesPage, feedFilter, searchQuery, stageFilter])

  useEffect(() => {
    loadOutbox()
  }, [outboxStatusFilter])

  useEffect(() => {
    loadFeeds()
    loadMetadata()
  }, [])

  // Poll background scraper status every 2.5 seconds
  useEffect(() => {
    let isMounted = true
    const checkScraper = async () => {
      try {
        const st = await fetchScraperStatus()
        if (isMounted) setScraperStatus(st)
      } catch {
        // silent polling catch
      }
    }

    checkScraper()
    const timer = setInterval(checkScraper, 2500)
    return () => {
      isMounted = false
      clearInterval(timer)
    }
  }, [])

  // Auto-refresh feeds and deals when a background scrape completes
  useEffect(() => {
    if (prevScrapingRef.current && scraperStatus && !scraperStatus.is_scraping) {
      loadArticles()
      loadFeeds()
      loadOutbox()
      const stats = scraperStatus.last_poll_stats
      if (stats && stats.new > 0) {
        showToast(`Feed scrape complete: ${stats.new} new funding rounds discovered!`)
      } else if (stats) {
        showToast(`Feed sweep complete: all ${stats.fetched} articles indexed.`)
      }
    }
    if (scraperStatus) {
      prevScrapingRef.current = scraperStatus.is_scraping
    }
  }, [scraperStatus?.is_scraping])

  // Auto-refresh when new jobs are ready in the outbox
  const prevJobTotalRef = React.useRef<number>(0)
  useEffect(() => {
    if (scraperStatus?.total_jobs_ready != null) {
      if (prevJobTotalRef.current !== 0 && scraperStatus.total_jobs_ready > prevJobTotalRef.current) {
        const added = scraperStatus.total_jobs_ready - prevJobTotalRef.current
        showToast(`⚡ Discovered ${added} new job opportunit${added > 1 ? 'ies' : 'y'}! Outbox updated.`)
        loadOutbox()
        loadArticles()
      }
      prevJobTotalRef.current = scraperStatus.total_jobs_ready
    }
  }, [scraperStatus?.total_jobs_ready])

  // Manual trigger for scraper
  const handleTriggerScrape = async () => {
    setTriggeringScrape(true)
    try {
      const res = await triggerScraperPoll()
      showToast(res.message || 'Scraping cycle started in background!')
      const st = await fetchScraperStatus()
      setScraperStatus(st)
    } catch (err: unknown) {
      showToast(`Scrape trigger failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setTriggeringScrape(false)
    }
  }

  // Handle Generate Draft action from Deals Feed
  const handleDraftJobEnquiry = async (article: Article) => {
    setGeneratingArticleId(article.id)
    try {
      const draft = await generateDraft(article.id)
      setSelectedDraft(draft)
      setModalTab('read')
      setIsModalOpen(true)
      await loadOutbox()
      showToast(`Job enquiry draft ready for ${article.company || article.title}!`)
    } catch (err: unknown) {
      showToast(`Draft generation failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setGeneratingArticleId(null)
    }
  }

  // Open existing draft
  const handleOpenDraft = (draft: DraftEmail, initialTab: 'read' | 'edit' = 'read') => {
    setSelectedDraft(draft)
    setModalTab(initialTab)
    setIsModalOpen(true)
  }

  // Save draft
  const handleSaveDraft = async (draftId: string, payload: Partial<DraftEmail>) => {
    const updated = await updateDraft(draftId, payload)
    setSelectedDraft(updated)
    await loadOutbox()
  }

  // Send draft via SMTP
  const handleSendDraft = async (draft: DraftEmail, force: boolean = false) => {
    const res = await sendDraft(draft.id, force)
    showToast(res.message || `Dispatched enquiry to ${draft.recipient_email}!`)
    await loadOutbox()
  }

  // Delete draft
  const handleDeleteDraft = async (draftId: string) => {
    await deleteDraft(draftId)
    showToast('Draft deleted successfully')
    await loadOutbox()
  }

  // Dismiss deal from active feed
  const handleDismissArticle = async (articleId: string) => {
    try {
      await dismissArticle(articleId)
      showToast('Deal dismissed from active feed')
      await loadArticles()
    } catch (err: unknown) {
      showToast(`Failed to dismiss deal: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  // Map drafts by company for 1-click View Draft button in deals feed
  const draftsByCompany = useMemo(() => {
    const map: Record<string, DraftEmail> = {}
    for (const d of drafts) {
      if (d.company) {
        map[d.company.trim().toLowerCase()] = d
      }
    }
    return map
  }, [drafts])

  const tabLabels: Record<string, string> = {
    deals: 'Funding Deals',
    outbox: 'Outbox',
    feeds: 'Feed Sources',
    profile: 'My Profile',
    settings: 'SMTP Settings',
  }

  const tabSubtitles: Record<string, string> = {
    deals: `${totalArticles} verified rounds`,
    outbox: `${outboxStats.draft} awaiting approval`,
    feeds: `${feeds.length} active feeds`,
    profile: candidateProfile
      ? `${candidateProfile.name} · ${candidateProfile.title || 'Product Engineer'}`
      : 'Candidate Profile',
    settings: config?.smtp?.configured ? 'Connected' : 'Ready to configure',
  }

  return (
    <div className="flex h-screen bg-[#FAFAFA] overflow-hidden text-zinc-900">
      {/* Fixed Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
        outboxStats={outboxStats}
        resumeStatus={resumeStatus}
        candidateProfile={candidateProfile}
      />

      {/* Main Content Area */}
      <div
        className={`flex-1 flex flex-col h-screen overflow-hidden transition-all duration-300 ease-spring ${
          isCollapsed ? 'ml-16' : 'ml-64'
        }`}
      >
        {/* Top Navbar */}
        <header className="h-14 px-6 border-b border-zinc-100 bg-white/90 backdrop-blur-md flex items-center justify-between flex-shrink-0 z-20">
          <div className="flex items-center gap-2.5">
            <span className="text-sm font-semibold text-zinc-900">
              {tabLabels[activeTab]}
            </span>
            <span className="text-zinc-300">/</span>
            <span className="text-xs text-zinc-400 font-medium">
              {tabSubtitles[activeTab]}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Live Continuous Discovery Engine Indicator */}
            {scraperStatus?.is_scraping ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-50 border border-violet-200 text-violet-800 text-xs shadow-xs animate-pulse">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-600"></span>
                </span>
                <span className="font-semibold text-violet-900">
                  Scanning ({scraperStatus.feed_index}/{scraperStatus.feed_total}):
                </span>
                <span className="font-medium max-w-[140px] truncate text-violet-700">
                  {scraperStatus.current_feed || 'Feeds...'}
                </span>
                <span className="text-[10px] font-mono font-bold bg-violet-200/80 text-violet-900 px-1.5 py-0.5 rounded">
                  {scraperStatus.progress_percent}%
                </span>
                {scraperStatus.total_jobs_ready != null && (
                  <span className="hidden sm:inline-flex text-[11px] font-semibold text-violet-800 bg-white/70 px-2 py-0.5 rounded-full border border-violet-200/60">
                    {scraperStatus.total_jobs_ready} jobs ready
                  </span>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span className="font-semibold">Continuous Discovery Active</span>
                  <span className="text-emerald-300">·</span>
                  <span className="font-mono text-emerald-700 font-semibold">
                    {scraperStatus?.total_jobs_ready ?? outboxStats.total} Jobs Ready
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleTriggerScrape}
                  disabled={triggeringScrape || scraperStatus?.is_scraping}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-800 text-xs font-medium border border-zinc-200/70 transition disabled:opacity-50 cursor-pointer"
                  title="Trigger immediate feed scan"
                >
                  <RefreshCw size={11} className={triggeringScrape ? 'animate-spin' : ''} />
                  <span>Scan Now</span>
                </button>
              </div>
            )}

            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-50 border border-zinc-200/60 text-zinc-600 text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-medium">System Online</span>
            </span>

            <a
              href="/api/outbox/resume/download"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium transition shadow-xs"
            >
              <span>{candidateProfile?.resume_filename || resumeStatus?.filename || 'Resume.pdf'}</span>
              <ExternalLink size={11} className="text-zinc-400" />
            </a>
          </div>
        </header>

        {/* Tab Content Body */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="w-full">
            {activeTab === 'deals' && (
              <DealsFeed
                articles={articles}
                loading={loadingArticles}
                total={totalArticles}
                page={articlesPage}
                setPage={setArticlesPage}
                onRefresh={loadArticles}
                onDraftJobEnquiry={handleDraftJobEnquiry}
                onOpenDraft={handleOpenDraft}
                onDismissArticle={handleDismissArticle}
                generatingArticleId={generatingArticleId}
                showToast={showToast}
                feedFilter={feedFilter}
                setFeedFilter={setFeedFilter}
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                feeds={feeds}
                contactedRecipients={contactedRecipients}
                stageFilter={stageFilter}
                setStageFilter={setStageFilter}
                draftsByCompany={draftsByCompany}
              />
            )}

            {activeTab === 'outbox' && (
              <OutboxReview
                drafts={drafts}
                stats={outboxStats}
                loading={loadingOutbox}
                onOpenDraft={handleOpenDraft}
                onSendDraft={(d) => handleOpenDraft(d, 'read')}
                onDeleteDraft={handleDeleteDraft}
                onRefresh={loadOutbox}
                statusFilter={outboxStatusFilter}
                setStatusFilter={setOutboxStatusFilter}
                contactedRecipients={contactedRecipients}
              />
            )}

            {activeTab === 'feeds' && (
              <FeedsMonitor
                feeds={feeds}
                loading={loadingFeeds}
                onRefresh={loadFeeds}
                showToast={showToast}
              />
            )}

            {activeTab === 'profile' && (
              <CandidateProfile
                resumeStatus={resumeStatus}
                candidateProfile={candidateProfile}
                onProfileUpdated={(updated) => {
                  setCandidateProfile(updated)
                  loadMetadata()
                  loadOutbox()
                }}
                showToast={showToast}
              />
            )}

            {activeTab === 'settings' && (
              <SmtpSettings
                config={config}
                showToast={showToast}
                onConfigSaved={loadMetadata}
              />
            )}
          </div>
        </main>
      </div>

      {/* Interactive Email Modal */}
      <EmailModal
        draft={selectedDraft}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSaveDraft={handleSaveDraft}
        onSendDraft={handleSendDraft}
        initialTab={modalTab}
        showToast={showToast}
        contactedRecipients={contactedRecipients}
      />

      {/* Toast Alert */}
      <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
    </div>
  )
}
