import React, { useState, useEffect } from 'react'
import {
  X,
  Send,
  Eye,
  Edit3,
  FileText,
  Save,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  ShieldCheck,
  Sparkles,
  ExternalLink,
} from 'lucide-react'
import { DraftEmail } from '../types'

interface EmailModalProps {
  draft: DraftEmail | null
  isOpen: boolean
  onClose: () => void
  onSaveDraft: (draftId: string, payload: Partial<DraftEmail>) => Promise<void>
  onSendDraft: (draft: DraftEmail) => Promise<void>
  initialTab?: 'read' | 'edit'
  showToast: (msg: string) => void
}

export const EmailModal: React.FC<EmailModalProps> = ({
  draft,
  isOpen,
  onClose,
  onSaveDraft,
  onSendDraft,
  initialTab = 'read',
  showToast,
}) => {
  const [activeTab, setActiveTab] = useState<'read' | 'edit'>('read')
  const [formData, setFormData] = useState<Partial<DraftEmail>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [showConfirmSend, setShowConfirmSend] = useState(false)
  const [copied, setCopied] = useState(false)

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
    }
  }, [draft, initialTab])

  if (!isOpen || !draft) return null

  const handleCopyBody = () => {
    navigator.clipboard.writeText(formData.body || draft.body)
    setCopied(true)
    showToast('Copied email body to clipboard!')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await onSaveDraft(draft.id, formData)
      showToast('Draft changes saved successfully!')
    } catch (err: any) {
      showToast(`Save error: ${err.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  const handleConfirmSend = async () => {
    setIsSending(true)
    try {
      // First persist any edited changes
      await onSaveDraft(draft.id, formData)
      await onSendDraft({ ...draft, ...formData } as DraftEmail)
      setShowConfirmSend(false)
      onClose()
    } catch (err: any) {
      showToast(`Send error: ${err.message}`)
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="w-full max-w-3xl my-8 rounded-2xl bg-white border border-zinc-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-fadeIn">
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-zinc-950 flex items-center justify-center text-white font-mono text-sm font-bold">
              ✉️
            </div>
            <div>
              <h2 className="text-sm font-bold text-zinc-950 flex items-center gap-2">
                <span>{formData.company || draft.company}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-200 text-zinc-800 font-semibold uppercase">
                  {draft.status}
                </span>
              </h2>
              <p className="text-[11px] font-mono text-zinc-600">
                To: {formData.recipient_name} &lt;{formData.recipient_email || 'NO EMAIL'}&gt;
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Mode Switcher */}
            <div className="flex items-center p-1 rounded-xl bg-zinc-200/70 text-xs font-mono">
              <button
                onClick={() => setActiveTab('read')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                  activeTab === 'read' ? 'bg-white text-zinc-950 shadow-xs font-semibold' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <Eye size={13} />
                <span>Reader</span>
              </button>
              <button
                onClick={() => setActiveTab('edit')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                  activeTab === 'edit' ? 'bg-white text-zinc-950 shadow-xs font-semibold' : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <Edit3 size={13} />
                <span>Editor</span>
              </button>
            </div>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl border border-zinc-200 hover:bg-zinc-100 text-zinc-500 hover:text-zinc-900 transition"
              title="Close modal"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {activeTab === 'read' ? (
            /* ========================================================= */
            /* READER MODE                                               */
            /* ========================================================= */
            <div className="space-y-6">
              {/* Email Envelope Metadata Card */}
              <div className="p-4 rounded-xl border border-zinc-200 bg-zinc-50/70 space-y-2 text-xs font-mono">
                <div className="flex items-center justify-between pb-2 border-b border-zinc-200">
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-600 font-semibold w-16">FROM:</span>
                    <span className="font-semibold text-zinc-950">Suriyan Dhanapal</span>
                    <span className="text-zinc-600 font-medium">&lt;suriyandhanapal@gmail.com&gt;</span>
                  </div>
                  <span className="text-[10px] text-zinc-600 font-semibold">SMTP Authenticated</span>
                </div>

                <div className="flex items-center justify-between pb-2 border-b border-zinc-200">
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-600 font-semibold w-16">TO:</span>
                    <span className="font-semibold text-zinc-950">{formData.recipient_name}</span>
                    {formData.recipient_email ? (
                      <span className="px-2 py-0.5 rounded-md bg-zinc-200 text-zinc-900 font-semibold">
                        {formData.recipient_email}
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-md bg-red-100 text-red-700 font-bold">
                        &lt;NO RECIPIENT EMAIL SET&gt;
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => setActiveTab('edit')}
                    className="text-[11px] text-zinc-600 hover:text-zinc-950 hover:underline font-medium"
                  >
                    Edit recipient ✎
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-600 font-semibold w-16">SUBJECT:</span>
                    <span className="font-bold text-zinc-950">{formData.subject}</span>
                  </div>
                </div>
              </div>

              {/* Formatted Email Content */}
              <div className="p-6 rounded-xl border border-zinc-200 bg-white shadow-xs space-y-4 text-xs text-zinc-800 leading-relaxed font-sans">
                {formData.body?.split('\n\n').map((paragraph, idx) => (
                  <p key={idx} className="whitespace-pre-line leading-relaxed">
                    {paragraph}
                  </p>
                ))}
              </div>

              {/* Resume Attachment Pill */}
              {formData.attach_resume && (
                <div className="p-3.5 rounded-xl border border-zinc-200 bg-zinc-50 flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-zinc-200 text-zinc-800">
                      <FileText size={16} />
                    </div>
                    <div>
                      <div className="font-semibold text-zinc-950">Suriyan_Dhanapal_Resume.pdf</div>
                      <div className="text-[10px] text-zinc-600 font-medium">179.8 KB • Application Attachment</div>
                    </div>
                  </div>

                  <a
                    href="/api/outbox/resume/download"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-800 text-[11px] font-medium transition shadow-xs"
                  >
                    <span>Inspect PDF</span>
                    <ExternalLink size={11} className="text-zinc-400" />
                  </a>
                </div>
              )}
            </div>
          ) : (
            /* ========================================================= */
            /* EDITOR MODE                                               */
            /* ========================================================= */
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-semibold text-zinc-600 mb-1.5">
                    RECIPIENT NAME
                  </label>
                  <input
                    type="text"
                    value={formData.recipient_name || ''}
                    onChange={(e) => setFormData({ ...formData, recipient_name: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-950 focus:outline-none transition shadow-xs text-xs font-mono text-zinc-950"
                    placeholder="e.g. Prabhat Shrivastava or Founding Team"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-zinc-600 mb-1.5">
                    RECIPIENT EMAIL (TO)
                  </label>
                  <input
                    type="email"
                    value={formData.recipient_email || ''}
                    onChange={(e) => setFormData({ ...formData, recipient_email: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-950 focus:outline-none transition shadow-xs text-xs font-mono text-zinc-950"
                    placeholder="e.g. prabhat@vituscare.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-zinc-600 mb-1.5">
                  EMAIL SUBJECT LINE
                </label>
                <input
                  type="text"
                  value={formData.subject || ''}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-950 focus:outline-none transition shadow-xs text-xs font-mono text-zinc-950"
                  placeholder="Subject line"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-zinc-600 mb-1.5 flex items-center justify-between">
                  <span>EMAIL BODY (MARKDOWN / TEXT)</span>
                  <button
                    onClick={handleCopyBody}
                    className="text-[10px] text-zinc-500 hover:text-zinc-950 inline-flex items-center gap-1"
                  >
                    {copied ? <Check size={11} className="text-emerald-600" /> : <Copy size={11} />}
                    <span>Copy text</span>
                  </button>
                </label>
                <textarea
                  rows={12}
                  value={formData.body || ''}
                  onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                  className="w-full p-4 rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-950 focus:outline-none transition shadow-xs font-sans text-xs text-zinc-900 leading-relaxed resize-y"
                  placeholder="Email body text..."
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="attach_resume_toggle"
                  checked={formData.attach_resume ?? true}
                  onChange={(e) => setFormData({ ...formData, attach_resume: e.target.checked })}
                  className="rounded border-zinc-300 text-zinc-950 focus:ring-zinc-950 cursor-pointer"
                />
                <label htmlFor="attach_resume_toggle" className="text-xs text-zinc-700 cursor-pointer select-none">
                  Attach candidate resume PDF (<strong>Suriyan.pdf</strong>) on dispatch
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="px-6 py-4 border-t border-zinc-200 bg-zinc-50/70 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyBody}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-xs font-mono text-zinc-700 font-medium transition shadow-xs"
            >
              {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
              <span>{copied ? 'Copied' : 'Copy Body'}</span>
            </button>

            {activeTab === 'edit' && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-zinc-300 bg-white hover:bg-zinc-100 text-xs font-mono text-zinc-950 font-semibold transition shadow-xs disabled:opacity-50"
              >
                <Save size={13} />
                <span>{isSaving ? 'Saving...' : 'Save Draft'}</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-xs font-mono text-zinc-700 font-medium transition"
            >
              Close
            </button>

            <button
              onClick={() => setShowConfirmSend(true)}
              disabled={!formData.recipient_email || isSending}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-zinc-950 hover:bg-zinc-800 text-white text-xs font-mono font-bold transition shadow-xs disabled:opacity-50"
              title={formData.recipient_email ? 'Review & dispatch via SMTP' : 'Requires recipient email'}
            >
              <Send size={13} />
              <span>Send via SMTP</span>
            </button>
          </div>
        </div>

        {/* Human Confirmation Dialog Overlay */}
        {showConfirmSend && (
          <div className="absolute inset-0 z-60 bg-black/50 backdrop-blur-xs flex items-center justify-center p-6 animate-fadeIn">
            <div className="w-full max-w-md p-6 rounded-2xl bg-white border border-zinc-200 shadow-2xl space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-amber-100 text-amber-800">
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-zinc-950">Confirm SMTP Job Outreach</h3>
                  <p className="text-[11px] font-mono text-zinc-500">Human-in-the-loop Final Check</p>
                </div>
              </div>

              <div className="p-4 rounded-xl border border-zinc-200 bg-zinc-50 space-y-2 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-zinc-500">Company:</span>
                  <span className="font-bold text-zinc-950">{formData.company}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">To:</span>
                  <span className="font-bold text-zinc-950">{formData.recipient_email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-500">Resume:</span>
                  <span className="font-semibold text-emerald-700">Suriyan.pdf Attached</span>
                </div>
              </div>

              <p className="text-xs text-zinc-600 leading-relaxed font-sans">
                This action will authenticate with your configured SMTP server and dispatch your personalized cold job enquiry directly to <strong>{formData.recipient_email}</strong>.
              </p>

              <div className="flex items-center justify-end gap-2.5 pt-2 font-mono text-xs">
                <button
                  onClick={() => setShowConfirmSend(false)}
                  disabled={isSending}
                  className="px-4 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 font-medium text-zinc-700 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmSend}
                  disabled={isSending}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-zinc-950 hover:bg-zinc-800 text-white font-bold transition shadow-xs disabled:opacity-50"
                >
                  {isSending && <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>}
                  <span>{isSending ? 'Dispatching...' : 'Yes, Dispatch Email'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
