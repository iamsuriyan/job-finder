import React, { useState, useEffect, useCallback } from 'react'
import {
  X,
  Send,
  Eye,
  Edit3,
  FileText,
  Save,
  Check,
  Copy,
  ShieldCheck,
  Loader2,
  AlertTriangle,
} from 'lucide-react'
import { DraftEmail, ContactedRecipient } from '../types'

interface EmailModalProps {
  draft: DraftEmail | null
  isOpen: boolean
  onClose: () => void
  onSaveDraft: (draftId: string, payload: Partial<DraftEmail>) => Promise<void>
  onSendDraft: (draft: DraftEmail, force?: boolean) => Promise<void>
  initialTab?: 'read' | 'edit'
  showToast: (msg: string) => void
  contactedRecipients?: Record<string, ContactedRecipient>
}

export const EmailModal: React.FC<EmailModalProps> = ({
  draft,
  isOpen,
  onClose,
  onSaveDraft,
  onSendDraft,
  initialTab = 'read',
  showToast,
  contactedRecipients,
}) => {
  const [activeTab, setActiveTab] = useState<'read' | 'edit'>('read')
  const [formData, setFormData] = useState<Partial<DraftEmail>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [showConfirmSend, setShowConfirmSend] = useState(false)
  const [copied, setCopied] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

  const currentEmailKey = (formData.recipient_email || draft?.recipient_email || '')
    .trim()
    .toLowerCase()
  const priorContact = currentEmailKey && contactedRecipients ? contactedRecipients[currentEmailKey] : null
  const isAlreadyContacted = Boolean(priorContact && priorContact.draft_id !== draft?.id)

  const handleClose = useCallback(() => {
    setIsClosing(true)
    setTimeout(() => {
      setIsClosing(false)
      onClose()
    }, 160)
  }, [onClose])

  useEffect(() => {
    if (draft) {
      setFormData({
        company: draft.company,
        recipient_name: draft.recipient_name,
        recipient_email: draft.recipient_email || '',
        subject: draft.subject,
        body: draft.body,
        attach_resume: draft.attach_resume,
      })
      setActiveTab(initialTab)
      setShowConfirmSend(false)
      setIsClosing(false)
    }
  }, [draft, initialTab])

  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showConfirmSend) {
          setShowConfirmSend(false)
        } else {
          handleClose()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, showConfirmSend, handleClose])

  if (!isOpen || !draft) return null

  const handleCopyBody = () => {
    navigator.clipboard.writeText(formData.body || draft.body)
    setCopied(true)
    showToast('Copied email body to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onSaveDraft(draft.id, formData)
      showToast('Draft changes saved successfully')
    } catch (err: unknown) {
      showToast(`Save error: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsSaving(false)
    }
  }

  const handleConfirmSend = async () => {
    setIsSending(true)
    try {
      await onSaveDraft(draft.id, formData)
      await onSendDraft({ ...draft, ...formData } as DraftEmail, isAlreadyContacted)
      setShowConfirmSend(false)
      handleClose()
    } catch (err: unknown) {
      showToast(`Send error: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget && !showConfirmSend) {
          handleClose()
        }
      }}
      className={`fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto ${
        isClosing ? 'animate-backdrop-out' : 'animate-backdrop-in'
      }`}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`w-full max-w-3xl my-6 rounded-2xl bg-white border border-zinc-200 shadow-2xl overflow-hidden flex flex-col h-[780px] max-h-[92vh] relative transition-[height] duration-200 ease-out ${
          isClosing ? 'animate-scale-out' : 'animate-scale-in'
        }`}
      >
        {/* Top Header - Fixed height */}
        <div className="h-16 px-6 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/70 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-white flex-shrink-0 shadow-sm">
              <span className="text-sm">✉️</span>
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-zinc-900 truncate">
                  {formData.company || draft.company}
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-200 text-zinc-700 font-semibold uppercase">
                  {draft.status}
                </span>
              </div>
              <p className="text-xs text-zinc-500 truncate">
                To: {formData.recipient_name || 'Founder'} &lt;{formData.recipient_email || 'No email'}&gt;
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {/* View Mode Switcher */}
            <div className="flex items-center p-0.5 rounded-lg bg-zinc-200/70 text-xs">
              <button
                onClick={() => setActiveTab('read')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
                  activeTab === 'read' ? 'bg-white text-zinc-900 shadow-xs font-semibold' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <Eye size={13} />
                <span>Reader</span>
              </button>
              <button
                onClick={() => setActiveTab('edit')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-medium transition-all ${
                  activeTab === 'edit' ? 'bg-white text-zinc-900 shadow-xs font-semibold' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <Edit3 size={13} />
                <span>Editor</span>
              </button>
            </div>

            {/* Close Button */}
            <button
              onClick={handleClose}
              className="p-1.5 rounded-lg border border-zinc-200 hover:bg-zinc-100 text-zinc-400 hover:text-zinc-700 transition"
              title="Close modal"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Repeat Outreach Warning Banner */}
        {isAlreadyContacted && priorContact && (
          <div className="mx-6 mt-3 px-4 py-2.5 rounded-xl bg-amber-50 border border-amber-200/80 flex items-center gap-2.5 text-xs text-amber-900 flex-shrink-0 animate-fade-in">
            <AlertTriangle size={15} className="text-amber-600 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <span className="font-semibold">Repeat Outreach Safeguard:</span> This recipient (
              <span className="font-mono font-medium">{formData.recipient_email || draft.recipient_email}</span>
              ) was already emailed on{' '}
              <span className="font-medium">
                {new Date(priorContact.sent_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </span>{' '}
              for <span className="font-semibold">{priorContact.company}</span>.
            </div>
          </div>
        )}

        {/* Modal Body - Fixed scrollable container with smooth tab transition */}
        <div className="p-6 overflow-hidden flex-1 min-h-0 flex flex-col">
          <div key={activeTab} className="h-full flex flex-col animate-fade-in min-h-0">
            {activeTab === 'read' ? (
              /* READER MODE */
              <div className="space-y-4 flex flex-col h-full min-h-0">
                {/* Email Envelope Header */}
                <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 space-y-2 text-xs flex-shrink-0">
                  <div className="flex items-center">
                    <span className="w-16 font-medium text-zinc-400">To:</span>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-zinc-900">{formData.recipient_name || 'Founder'}</span>
                      {formData.recipient_email ? (
                        <span className="px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-200 font-mono text-[11px]">
                          {formData.recipient_email}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-mono text-[11px]">
                          Missing Email
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-start">
                    <span className="w-16 font-medium text-zinc-400 pt-0.5">Subject:</span>
                    <span className="font-semibold text-zinc-900 flex-1">{formData.subject}</span>
                  </div>

                  <div className="flex items-center">
                    <span className="w-16 font-medium text-zinc-400">Attachment:</span>
                    <div className="flex items-center gap-1.5 text-emerald-700 font-medium">
                      <FileText size={12} />
                      <span>Suriyan.pdf (Candidate Resume)</span>
                    </div>
                  </div>
                </div>

                {/* Email Body */}
                <div className="rounded-xl border border-zinc-100 bg-white p-5 shadow-xs flex-1 min-h-0 overflow-y-auto">
                  <div className="text-sm text-zinc-700 whitespace-pre-wrap leading-relaxed font-sans font-normal selection:bg-violet-100 selection:text-violet-900">
                    {formData.body}
                  </div>
                </div>
              </div>
            ) : (
              /* EDITOR MODE */
              <div className="space-y-4 text-xs flex flex-col h-full min-h-0">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-shrink-0">
                  <div>
                    <label className="block text-zinc-600 font-medium mb-1.5">Recipient Name</label>
                    <input
                      type="text"
                      value={formData.recipient_name || ''}
                      onChange={(e) => setFormData({ ...formData, recipient_name: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-zinc-600 font-medium mb-1.5">Recipient Email</label>
                    <input
                      type="email"
                      value={formData.recipient_email || ''}
                      onChange={(e) => setFormData({ ...formData, recipient_email: e.target.value })}
                      placeholder="founder@company.com"
                      className="w-full px-3 py-2 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs font-mono"
                    />
                  </div>
                </div>

                <div className="flex-shrink-0">
                  <label className="block text-zinc-600 font-medium mb-1.5">Subject Line</label>
                  <input
                    type="text"
                    value={formData.subject || ''}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs font-mono font-medium"
                  />
                </div>

                <div className="flex-1 min-h-0 flex flex-col">
                  <label className="block text-zinc-600 font-medium mb-1.5 flex-shrink-0">Email Body</label>
                  <textarea
                    value={formData.body || ''}
                    onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                    className="w-full flex-1 min-h-[160px] p-3 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs leading-relaxed font-sans resize-none"
                    placeholder="Email body text..."
                  />
                </div>

                <div className="flex items-center gap-2 pt-1 flex-shrink-0">
                  <input
                    type="checkbox"
                    id="attach_resume_toggle"
                    checked={formData.attach_resume ?? true}
                    onChange={(e) => setFormData({ ...formData, attach_resume: e.target.checked })}
                    className="rounded border-zinc-300 text-violet-600 focus:ring-violet-500 cursor-pointer"
                  />
                  <label htmlFor="attach_resume_toggle" className="text-xs text-zinc-700 cursor-pointer select-none">
                    Attach candidate resume PDF (<strong>Suriyan.pdf</strong>) on dispatch
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer Controls - Fixed height */}
        <div className="h-16 px-6 border-t border-zinc-100 bg-zinc-50/70 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyBody}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-xs font-medium text-zinc-700 transition shadow-xs"
            >
              {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
              <span>{copied ? 'Copied' : 'Copy Body'}</span>
            </button>

            {activeTab === 'edit' && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-zinc-300 bg-white hover:bg-zinc-50 text-xs font-semibold text-zinc-900 transition shadow-xs disabled:opacity-50"
              >
                <Save size={13} />
                <span>{isSaving ? 'Saving...' : 'Save Draft'}</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleClose}
              className="px-3.5 py-1.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-xs font-medium text-zinc-700 transition"
            >
              Close
            </button>

            <button
              onClick={() => setShowConfirmSend(true)}
              disabled={!formData.recipient_email || isSending}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-semibold transition shadow-xs disabled:opacity-50"
              title={formData.recipient_email ? 'Review & dispatch via SMTP' : 'Requires recipient email'}
            >
              <Send size={13} />
              <span>Send via SMTP</span>
            </button>
          </div>
        </div>

        {/* Human Confirmation Dialog Overlay */}
        {showConfirmSend && (
          <div
            onClick={(e) => {
              if (e.target === e.currentTarget && !isSending) {
                setShowConfirmSend(false)
              }
            }}
            className="absolute inset-0 z-60 bg-black/50 backdrop-blur-xs flex items-center justify-center p-6 animate-backdrop-in"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md p-6 rounded-2xl bg-white border border-zinc-200 shadow-2xl space-y-4 animate-scale-in"
            >
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-amber-50 text-amber-700 border border-amber-200">
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-zinc-900">Confirm Job Outreach</h3>
                  <p className="text-xs text-zinc-500">Human-in-the-loop Final Check</p>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-zinc-100 bg-zinc-50 space-y-2 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Company:</span>
                  <span className="font-semibold text-zinc-900">{formData.company}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">To:</span>
                  <span className="font-semibold text-zinc-900">{formData.recipient_email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Resume:</span>
                  <span className="font-semibold text-emerald-700">Resume Attached</span>
                </div>
              </div>

              {isAlreadyContacted && priorContact && (
                <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 text-left space-y-1">
                  <p className="font-semibold flex items-center gap-1.5 text-amber-950">
                    <AlertTriangle size={13} className="text-amber-600" />
                    Recipient Already Contacted
                  </p>
                  <p className="text-[11px] leading-relaxed text-amber-800">
                    You already sent an outreach email to this address for <strong>{priorContact.company}</strong> on{' '}
                    {new Date(priorContact.sent_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                    })}
                    . Confirming will resend another email.
                  </p>
                </div>
              )}

              <p className="text-xs text-zinc-600 leading-relaxed">
                This action will authenticate with your configured SMTP server and dispatch your personalized enquiry directly to <strong>{formData.recipient_email}</strong>.
              </p>

              <div className="flex items-center justify-end gap-2 pt-2 text-xs">
                <button
                  onClick={() => setShowConfirmSend(false)}
                  disabled={isSending}
                  className="px-3.5 py-1.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 font-medium text-zinc-700 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmSend}
                  disabled={isSending}
                  className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-lg text-white font-medium transition shadow-xs disabled:opacity-50 ${
                    isAlreadyContacted
                      ? 'bg-amber-600 hover:bg-amber-700'
                      : 'bg-zinc-900 hover:bg-zinc-800'
                  }`}
                >
                  {isSending && <Loader2 size={13} className="animate-spin" />}
                  <span>
                    {isSending
                      ? 'Dispatching...'
                      : isAlreadyContacted
                      ? 'Confirm & Resend Anyway'
                      : 'Yes, Dispatch Email'}
                  </span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
