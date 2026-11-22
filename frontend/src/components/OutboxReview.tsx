import React, { useState } from 'react'
import {
  ShieldCheck,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Inbox,
  Eye,
  Edit3,
  Trash2,
  Send,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { DraftEmail, DraftStats } from '../types'

interface OutboxReviewProps {
  drafts: DraftEmail[]
  stats?: DraftStats
  loading: boolean
  onOpenDraft: (draft: DraftEmail, initialTab?: 'read' | 'edit') => void
  onSendDraft: (draft: DraftEmail) => void
  onDeleteDraft: (draftId: string) => void
  onRefresh: () => void
  statusFilter: string
  setStatusFilter: (status: string) => void
}

function formatDate(isoString?: string): string {
  if (!isoString) return 'Recently'
  try {
    const d = new Date(isoString)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return isoString
  }
}

const SkeletonRow = () => (
  <div className="bg-white border border-zinc-100 rounded-xl p-4 flex items-center gap-4">
    <div className="skeleton w-2.5 h-2.5 rounded-full flex-shrink-0" />
    <div className="flex-1 space-y-2">
      <div className="skeleton h-4 w-40" />
      <div className="skeleton h-3 w-64" />
    </div>
    <div className="skeleton h-3 w-24 hidden sm:block" />
    <div className="flex gap-2">
      <div className="skeleton h-8 w-8 rounded-lg" />
      <div className="skeleton h-8 w-8 rounded-lg" />
      <div className="skeleton h-8 w-8 rounded-lg" />
    </div>
  </div>
)

export const OutboxReview: React.FC<OutboxReviewProps> = ({
  drafts,
  stats,
  loading,
  onOpenDraft,
  onSendDraft,
  onDeleteDraft,
  onRefresh,
  statusFilter,
  setStatusFilter,
}) => {
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const filteredDrafts = drafts.filter((d) => {
    if (!statusFilter) return true
    return d.status === statusFilter
  })

  const statCards = [
    {
      key: '',
      label: 'All Drafts',
      value: stats?.total ?? drafts.length,
      icon: Inbox,
      color: 'text-zinc-500',
      activeColor: 'border-zinc-900 bg-zinc-900 text-white',
    },
    {
      key: 'draft',
      label: 'Pending Review',
      value: stats?.draft ?? 0,
      icon: Clock,
      color: 'text-amber-500',
      activeColor: 'border-amber-500 bg-amber-50 text-amber-800',
    },
    {
      key: 'sent',
      label: 'Sent',
      value: stats?.sent ?? 0,
      icon: CheckCircle2,
      color: 'text-emerald-500',
      activeColor: 'border-emerald-500 bg-emerald-50 text-emerald-800',
    },
    {
      key: 'failed',
      label: 'Failed',
      value: stats?.failed ?? 0,
      icon: AlertCircle,
      color: 'text-red-500',
      activeColor: 'border-red-400 bg-red-50 text-red-800',
    },
  ]

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Human Guarantee Banner */}
      <div className="flex items-start gap-3 bg-emerald-50 border border-emerald-200 rounded-xl p-4">
        <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center flex-shrink-0 shadow-sm">
          <ShieldCheck size={16} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-emerald-900">Human-in-the-Loop Guarantee</h3>
            <span className="px-2 py-0.5 rounded-full bg-emerald-200 text-emerald-800 text-[10px] font-mono font-bold">
              Manual Approval Required
            </span>
          </div>
          <p className="text-xs text-emerald-700 mt-1 leading-relaxed">
            Emails are saved as <strong>drafts</strong> and <strong>never</strong> sent without your explicit review and confirmation. Click <em>Review</em> on any draft to verify before sending.
          </p>
        </div>
        <a
          href="/api/outbox/resume/download"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-900 hover:bg-emerald-800 text-white text-xs font-medium transition-all flex-shrink-0"
        >
          <FileText size={12} />
          <span>Suriyan.pdf</span>
        </a>
      </div>

      {/* Stats + Header row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h1 className="text-xl font-semibold text-zinc-900 tracking-tight">Outbox</h1>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-2 bg-white border border-zinc-200 rounded-lg text-zinc-500 hover:text-zinc-800 hover:bg-zinc-50 hover:border-zinc-300 transition-all disabled:opacity-50 self-end sm:self-auto"
          title="Refresh outbox"
        >
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {statCards.map((card) => {
          const Icon = card.icon
          const isActive = statusFilter === card.key
          return (
            <button
              key={card.key}
              onClick={() => setStatusFilter(card.key)}
              className={`text-left p-4 rounded-xl border transition-all duration-150 ${
                isActive
                  ? card.activeColor + ' border-opacity-100'
                  : 'bg-white border-zinc-100 hover:border-zinc-200 shadow-sm text-zinc-800'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`text-[11px] font-medium uppercase tracking-wide ${isActive ? 'opacity-80' : 'text-zinc-400'}`}>
                  {card.label}
                </span>
                <Icon size={14} className={isActive ? 'opacity-70' : card.color} />
              </div>
              <div className={`text-2xl font-bold font-mono ${isActive ? '' : card.color}`}>
                {card.value}
              </div>
            </button>
          )
        })}
      </div>

      {/* Draft list */}
      <div className="space-y-2">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)
        ) : filteredDrafts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-12 h-12 rounded-2xl bg-zinc-100 flex items-center justify-center mb-4">
              <Inbox size={22} className="text-zinc-400" />
            </div>
            <h3 className="text-base font-semibold text-zinc-700 mb-1">
              {statusFilter ? `No ${statusFilter} emails` : 'No drafts yet'}
            </h3>
            <p className="text-sm text-zinc-400 max-w-xs">
              Generate outreach emails from funding deals and they'll appear here for review.
            </p>
          </div>
        ) : (
          filteredDrafts.map((draft) => {
            const isDeleting = deletingId === draft.id

            const statusDot =
              draft.status === 'sent'
                ? 'bg-emerald-500'
                : draft.status === 'failed'
                ? 'bg-red-500'
                : 'bg-amber-400'

            return (
              <div
                key={draft.id}
                className="bg-white border border-zinc-100 rounded-xl shadow-sm hover:shadow-md hover:border-zinc-200 transition-all duration-200"
              >
                <div className="flex items-center gap-4 p-4">
                  {/* Status dot */}
                  <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${statusDot}`} title={draft.status} />

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-zinc-900">{draft.company}</span>
                      {draft.recipient_email && (
                        <span className="text-xs text-zinc-400 font-mono">{draft.recipient_email}</span>
                      )}
                    </div>
                    <p className="text-sm text-zinc-500 truncate mt-0.5">{draft.subject}</p>
                  </div>

                  {/* Date */}
                  <span className="hidden sm:block text-xs text-zinc-400 flex-shrink-0">
                    {formatDate(draft.created_at)}
                  </span>

                  {/* Actions */}
                  {isDeleting ? (
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-xs text-zinc-500">Delete?</span>
                      <button
                        onClick={() => { onDeleteDraft(draft.id); setDeletingId(null) }}
                        className="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white transition-all"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setDeletingId(null)}
                        className="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-700 transition-all"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <button
                        onClick={() => onOpenDraft(draft, 'read')}
                        className="p-2 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-all"
                        title="Review email"
                      >
                        <Eye size={15} />
                      </button>
                      <button
                        onClick={() => onOpenDraft(draft, 'edit')}
                        className="p-2 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-all"
                        title="Edit email"
                      >
                        <Edit3 size={15} />
                      </button>
                      {draft.status === 'draft' && (
                        <button
                          onClick={() => onSendDraft(draft)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white transition-all"
                          title="Review & send"
                        >
                          <Send size={12} />
                          Send
                        </button>
                      )}
                      <button
                        onClick={() => setDeletingId(draft.id)}
                        className="p-2 rounded-lg text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-all"
                        title="Delete draft"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
