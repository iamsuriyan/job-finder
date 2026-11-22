import React, { useState, useEffect } from 'react'
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
  DraftEmail,
  DraftStats,
  FeedInfo,
  ResumeStatus,
  ConfigSummary,
} from './types'
import {
  fetchArticles,
  fetchOutbox,
  fetchFeeds,
  fetchConfig,
  fetchResumeStatus,
  generateDraft,
  updateDraft,
  deleteDraft,
  sendDraft,
} from './api/client'

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

  const [drafts, setDrafts] = useState<DraftEmail[]>([])
  const [outboxStats, setOutboxStats] = useState<DraftStats>({ total: 0, draft: 0, sent: 0, failed: 0 })
  const [loadingOutbox, setLoadingOutbox] = useState<boolean>(false)
  const [outboxStatusFilter, setOutboxStatusFilter] = useState<string>('')

  const [feeds, setFeeds] = useState<FeedInfo[]>([])
  const [loadingFeeds, setLoadingFeeds] = useState<boolean>(false)

  const [resumeStatus, setResumeStatus] = useState<ResumeStatus | null>(null)
  const [config, setConfig] = useState<ConfigSummary | null>(null)

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
      })
      setArticles(res.items || [])
      setTotalArticles(res.total || 0)
    } catch (err: any) {
      showToast(`Failed to load funding deals: ${err.message}`)
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
    } catch (err: any) {
      showToast(`Failed to load outbox: ${err.message}`)
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
    } catch (err: any) {
      showToast(`Failed to load feeds: ${err.message}`)
    } finally {
      setLoadingFeeds(false)
    }
  }

  // Load metadata
  const loadMetadata = async () => {
    try {
      const [rStatus, cfg] = await Promise.all([
        fetchResumeStatus().catch(() => null),
        fetchConfig().catch(() => null),
      ])
      if (rStatus) setResumeStatus(rStatus)
      if (cfg) setConfig(cfg)
    } catch {
      // Ignore initial metadata fetch errors
    }
  }

  useEffect(() => {
    loadArticles()
  }, [articlesPage, feedFilter, searchQuery])

  useEffect(() => {
    loadOutbox()
  }, [outboxStatusFilter])

  useEffect(() => {
    loadFeeds()
    loadMetadata()
  }, [])

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
    } catch (err: any) {
      showToast(`Draft generation failed: ${err.message}`)
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
  const handleSendDraft = async (draft: DraftEmail) => {
    const res = await sendDraft(draft.id)
    showToast(res.message || `Dispatched enquiry to ${draft.recipient_email}!`)
    await loadOutbox()
  }

  // Delete draft
  const handleDeleteDraft = async (draftId: string) => {
    await deleteDraft(draftId)
    showToast('Draft deleted successfully')
    await loadOutbox()
  }

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 flex font-sans selection:bg-zinc-950 selection:text-white">
      {/* Animated Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isCollapsed={isCollapsed}
        setIsCollapsed={setIsCollapsed}
        outboxStats={outboxStats}
        resumeStatus={resumeStatus}
      />

      {/* Main Content Area */}
      <main
        className={`flex-1 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] min-h-screen flex flex-col ${
          isCollapsed ? 'ml-20' : 'ml-72'
        }`}
      >
        {/* Top Navbar */}
        <header className="sticky top-0 z-20 h-18 px-8 border-b border-zinc-200 bg-white/80 backdrop-blur-md flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-lg bg-zinc-100 border border-zinc-200 text-zinc-700">
              {activeTab === 'deals' && '⚡ Deals Feed'}
              {activeTab === 'outbox' && '✉️ Human Outreach Review'}
              {activeTab === 'feeds' && '📡 RSS Sources Health'}
              {activeTab === 'profile' && '👤 Candidate Portfolio'}
              {activeTab === 'settings' && '⚙️ SMTP Configuration'}
            </span>

            <span className="text-zinc-300">/</span>

            <span className="text-xs font-mono text-zinc-500">
              {activeTab === 'deals' && `${totalArticles} Verified Rounds`}
              {activeTab === 'outbox' && `${outboxStats.draft} Awaiting Approval`}
              {activeTab === 'feeds' && `${feeds.length} Active Feeds`}
              {activeTab === 'profile' && 'Suriyan Dhanapal • GenAI & Product'}
              {activeTab === 'settings' && (config?.smtp?.configured ? 'Connected' : 'Ready to Configure')}
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-zinc-200 bg-zinc-50 text-zinc-700">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>Local Database Active</span>
            </span>

            <a
              href="/api/outbox/resume/download"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-zinc-950 hover:bg-zinc-800 text-white font-medium transition shadow-xs"
            >
              <span>Suriyan.pdf</span>
              <span className="text-[10px] text-zinc-400">↗</span>
            </a>
          </div>
        </header>

        {/* Tab Content Body */}
        <div className="p-8 flex-1 max-w-7xl w-full mx-auto animate-fadeIn">
          {activeTab === 'deals' && (
            <DealsFeed
              articles={articles}
              loading={loadingArticles}
              total={totalArticles}
              page={articlesPage}
              setPage={setArticlesPage}
              onRefresh={loadArticles}
              onDraftJobEnquiry={handleDraftJobEnquiry}
              generatingArticleId={generatingArticleId}
              showToast={showToast}
              feedFilter={feedFilter}
              setFeedFilter={setFeedFilter}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              feeds={feeds}
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
              config={config}
            />
          )}

          {activeTab === 'settings' && (
            <SmtpSettings
              config={config}
              showToast={showToast}
            />
          )}
        </div>
      </main>

      {/* Interactive Email Modal */}
      <EmailModal
        draft={selectedDraft}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSaveDraft={handleSaveDraft}
        onSendDraft={handleSendDraft}
        initialTab={modalTab}
        showToast={showToast}
      />

      {/* Toast Alert */}
      <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
    </div>
  )
}
