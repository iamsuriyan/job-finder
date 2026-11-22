import React, { useState } from 'react'
import {
  Inbox,
  Send,
  Eye,
  Edit3,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  FileText,
  User,
  Sparkles,
  ArrowRight,
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
  const [draftToDelete, setDraftToDelete] = useState<DraftEmail | null>(null)

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'Recent'
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

  const filteredDrafts = drafts.filter((d) => {
    if (!statusFilter) return true
    return d.status === statusFilter
  })

  return (
    <div className="space-y-6">
      {/* Top Banner: Human-in-the-Loop Security Guarantee */}
      <div className="p-5 rounded-2xl border border-emerald-200 bg-emerald-50/60 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-emerald-600 text-white shrink-0 shadow-xs">
            <ShieldCheck size={20} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-emerald-950 flex items-center gap-2">
              <span>Strict Human-in-the-Loop Cold Outreach Guarantee</span>
              <span className="px-2 py-0.5 rounded-full bg-emerald-200/80 text-emerald-800 text-[10px] font-mono font-bold">
                Manual Approval
              </span>
            </h2>
            <p className="text-xs text-emerald-800 mt-1 leading-relaxed">
              Emails are automatically saved with <strong>draft</strong> status and are <strong>never</strong> dispatched without explicit human inspection and confirmation. Click "Review & Read" on any draft to verify recipient, subject, and personalized accomplishments before sending.
            </p>
          </div>
        </div>

        <a
          href="/api/outbox/resume/download"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-emerald-950 hover:bg-emerald-900 text-white font-mono text-xs font-medium transition shrink-0 shadow-xs"
        >
          <FileText size={13} />
          <span>Suriyan.pdf Attached</span>
        </a>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          onClick={() => setStatusFilter('')}
          className={`cursor-pointer p-4 rounded-xl border transition-all ${
            statusFilter === ''
              ? 'border-zinc-950 bg-zinc-950 text-white shadow-sm'
              : 'border-zinc-200 bg-white hover:border-zinc-300 text-zinc-900 shadow-xs'
          }`}
        >
          <div className="text-[11px] font-mono uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Total Drafts</span>
            <Inbox size={14} className={statusFilter === '' ? 'text-zinc-400' : 'text-zinc-500'} />
          </div>
          <div className="text-2xl font-bold font-mono">{stats?.total || drafts.length}</div>
          <div className="text-[10px] font-mono mt-1 opacity-70">Generated for funded rounds</div>
        </div>

        <div
          onClick={() => setStatusFilter('draft')}
          className={`cursor-pointer p-4 rounded-xl border transition-all ${
            statusFilter === 'draft'
              ? 'border-zinc-950 bg-zinc-950 text-white shadow-sm'
              : 'border-zinc-200 bg-white hover:border-zinc-300 text-zinc-900 shadow-xs'
          }`}
        >
          <div className="text-[11px] font-mono uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Pending Review</span>
            <Clock size={14} className="text-amber-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-500">{stats?.draft || 0}</div>
          <div className="text-[10px] font-mono mt-1 opacity-70">Awaiting human dispatch</div>
        </div>

        <div
          onClick={() => setStatusFilter('sent')}
          className={`cursor-pointer p-4 rounded-xl border transition-all ${
            statusFilter === 'sent'
              ? 'border-zinc-950 bg-zinc-950 text-white shadow-sm'
              : 'border-zinc-200 bg-white hover:border-zinc-300 text-zinc-900 shadow-xs'
          }`}
        >
          <div className="text-[11px] font-mono uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Sent Successfully</span>
            <CheckCircle2 size={14} className="text-emerald-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-500">{stats?.sent || 0}</div>
          <div className="text-[10px] font-mono mt-1 opacity-70">Dispatched via SMTP</div>
        </div>

        <div
          onClick={() => setStatusFilter('failed')}
          className={`cursor-pointer p-4 rounded-xl border transition-all ${
            statusFilter === 'failed'
              ? 'border-zinc-950 bg-zinc-950 text-white shadow-sm'
              : 'border-zinc-200 bg-white hover:border-zinc-300 text-zinc-900 shadow-xs'
          }`}
        >
          <div className="text-[11px] font-mono uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Failed</span>
            <AlertCircle size={14} className="text-red-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-red-500">{stats?.failed || 0}</div>
          <div className="text-[10px] font-mono mt-1 opacity-70">SMTP connection error</div>
        </div>
      </div>

      {/* Filter Tabs Bar */}
      <div className="p-3 rounded-2xl border border-zinc-200 bg-white shadow-xs flex items-center justify-between">
        <div className="flex items-center gap-1.5 font-mono text-xs">
          <button
            onClick={() => setStatusFilter('')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              statusFilter === ''
                ? 'bg-zinc-950 text-white font-semibold'
                : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
            }`}
          >
            All ({drafts.length})
          </button>
          <button
            onClick={() => setStatusFilter('draft')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              statusFilter === 'draft'
                ? 'bg-zinc-950 text-white font-semibold'
                : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
            }`}
          >
            Ready to Send ({stats?.draft || 0})
          </button>
          <button
            onClick={() => setStatusFilter('sent')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              statusFilter === 'sent'
                ? 'bg-zinc-950 text-white font-semibold'
                : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
            }`}
          >
            Sent ({stats?.sent || 0})
          </button>
          <button
            onClick={() => setStatusFilter('failed')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              statusFilter === 'failed'
                ? 'bg-zinc-950 text-white font-semibold'
                : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
            }`}
          >
            Failed ({stats?.failed || 0})
          </button>
        </div>

        <button
          onClick={onRefresh}
          className="text-xs font-mono font-medium px-3 py-1.5 rounded-lg border border-zinc-200 hover:bg-zinc-100 text-zinc-700 transition"
        >
          Refresh Outbox
        </button>
      </div>

      {/* Drafts List */}
      {loading && drafts.length === 0 ? (
        <div className="py-24 text-center border-2 border-dashed border-zinc-200 rounded-2xl bg-white">
          <div className="w-7 h-7 mx-auto mb-3 border-2 border-zinc-900 border-t-transparent rounded-full animate-spin"></div>
          <p className="font-mono text-xs text-zinc-500">Loading outbox review drafts...</p>
        </div>
      ) : filteredDrafts.length === 0 ? (
        <div className="py-24 text-center border-2 border-dashed border-zinc-200 rounded-2xl bg-white">
          <p className="font-mono text-sm text-zinc-700 font-semibold">
            {statusFilter
              ? `No drafts with status '${statusFilter.toUpperCase()}'.`
              : 'Your outreach outbox is currently empty.'}
          </p>
          <p className="font-mono text-xs text-zinc-400 mt-1">
            Head to the <strong>Funding Deals</strong> tab and click "Draft Job Enquiry" on any startup deal.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredDrafts.map((draft) => {
            const isDraft = draft.status === 'draft'
            const isSent = draft.status === 'sent'
            const isFailed = draft.status === 'failed'

            return (
              <div
                key={draft.id}
                className="p-5 rounded-2xl border border-zinc-200 bg-white hover:border-zinc-400 transition-all duration-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-5 group"
              >
                {/* Left Side: Metadata & Subject Preview */}
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2.5 font-mono text-xs flex-wrap">
                    {/* Status Badge */}
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-semibold uppercase text-[10px] ${
                        isSent
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                          : isFailed
                          ? 'bg-red-100 text-red-800 border border-red-200'
                          : 'bg-zinc-100 text-zinc-800 border border-zinc-300'
                      }`}
                    >
                      {isSent ? (
                        <CheckCircle2 size={11} className="text-emerald-600" />
                      ) : isFailed ? (
                        <AlertCircle size={11} className="text-red-600" />
                      ) : (
                        <Clock size={11} className="text-zinc-600" />
                      )}
                      <span>{draft.status.toUpperCase()}</span>
                    </span>

                    <span className="font-bold text-zinc-950 px-2 py-0.5 rounded-md bg-zinc-100 border border-zinc-200">
                      {draft.company}
                    </span>

                    <span className="text-zinc-600">Created: {formatDate(draft.created_at)}</span>

                    {draft.attach_resume && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-zinc-700 font-semibold px-2 py-0.5 rounded-md bg-zinc-50 border border-zinc-200">
                        <FileText size={10} className="text-zinc-500" /> Suriyan.pdf
                      </span>
                    )}
                  </div>

                  {/* Recipient Line */}
                  <div className="flex items-center gap-2 font-mono text-xs text-zinc-700">
                    <span className="text-zinc-500 font-semibold">To:</span>
                    <span className="font-semibold text-zinc-950">{draft.recipient_name}</span>
                    {draft.recipient_email ? (
                      <span className="px-2 py-0.5 rounded-md bg-zinc-100 border border-zinc-200 text-zinc-900 font-medium">
                        {draft.recipient_email}
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-md bg-red-50 border border-red-200 text-red-600 font-bold">
                        NO EMAIL FOUND
                      </span>
                    )}
                  </div>

                  {/* Subject Line */}
                  <div className="text-sm font-semibold text-zinc-950 flex items-center gap-2">
                    <span>{draft.subject}</span>
                  </div>

                  {/* Body Preview */}
                  <p className="text-xs text-zinc-600 line-clamp-2 leading-relaxed font-sans">
                    {draft.body}
                  </p>

                  {/* Failure Error Message */}
                  {isFailed && draft.error_message && (
                    <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-700 font-mono text-[11px]">
                      Error: {draft.error_message}
                    </div>
                  )}
                </div>

                {/* Right Side: Action Buttons */}
                <div className="flex items-center gap-2 shrink-0 font-mono text-xs self-end md:self-center">
                  {/* Read / Review Button */}
                  <button
                    onClick={() => onOpenDraft(draft, 'read')}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-zinc-300 bg-white hover:bg-zinc-100 text-zinc-950 font-medium transition shadow-xs"
                    title="Open clean Reader view"
                  >
                    <Eye size={13} />
                    <span>Review & Read</span>
                  </button>

                  {/* Edit Button */}
                  <button
                    onClick={() => onOpenDraft(draft, 'edit')}
                    className="p-2 rounded-xl border border-zinc-300 bg-white hover:bg-zinc-100 text-zinc-700 hover:text-zinc-950 transition shadow-xs"
                    title="Edit subject or body"
                  >
                    <Edit3 size={14} />
                  </button>

                  {/* Send Button */}
                  {isDraft && (
                    <button
                      onClick={() => onSendDraft(draft)}
                      disabled={!draft.recipient_email}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-zinc-950 hover:bg-zinc-800 text-white font-medium transition shadow-xs disabled:opacity-50"
                      title={draft.recipient_email ? 'Dispatch email via SMTP' : 'Add recipient email first'}
                    >
                      <Send size={12} />
                      <span>Send Now</span>
                    </button>
                  )}

                  {/* Delete Button */}
                  <button
                    onClick={() => setDraftToDelete(draft)}
                    className="p-2 rounded-xl border border-zinc-200 bg-white hover:bg-red-50 hover:border-red-200 text-zinc-500 hover:text-red-600 transition shadow-xs"
                    title="Delete draft"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {draftToDelete && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-md p-6 rounded-2xl bg-white border border-zinc-200 shadow-xl space-y-4 animate-fadeIn">
            <h3 className="font-bold text-base text-zinc-950">Delete Outreach Draft?</h3>
            <p className="text-xs text-zinc-600 leading-relaxed">
              Are you sure you want to permanently delete the draft for <strong>{draftToDelete.company}</strong>? This action cannot be undone.
            </p>
            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setDraftToDelete(null)}
                className="px-4 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-xs font-mono font-medium transition"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onDeleteDraft(draftToDelete.id)
                  setDraftToDelete(null)
                }}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-mono font-medium transition shadow-xs"
              >
                Delete Draft
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
