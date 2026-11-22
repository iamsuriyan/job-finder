import React, { useState, useEffect, useRef } from 'react'
import {
  FileText,
  Sparkles,
  CheckCircle2,
  Mail,
  MapPin,
  Globe,
  Github,
  Linkedin,
  Upload,
  RefreshCw,
  Save,
  Plus,
  Trash2,
  ExternalLink,
  Phone,
  AlertCircle,
  FileCheck,
} from 'lucide-react'
import { CandidateProfile as ICandidateProfile, ResumeStatus } from '../types'
import {
  fetchCandidateProfile,
  uploadResumeFile,
  updateCandidateProfile,
  regenerateDraftsWithProfile,
} from '../api/client'

interface CandidateProfileProps {
  resumeStatus?: ResumeStatus | null
  candidateProfile?: ICandidateProfile | null
  onProfileUpdated?: (updated: ICandidateProfile) => void
  showToast: (msg: string) => void
}

export const CandidateProfile: React.FC<CandidateProfileProps> = ({
  resumeStatus,
  candidateProfile: initialProfile,
  onProfileUpdated,
  showToast,
}) => {
  const [profile, setProfile] = useState<ICandidateProfile | null>(initialProfile || null)
  const [loading, setLoading] = useState<boolean>(!initialProfile)
  const [uploading, setUploading] = useState<boolean>(false)
  const [saving, setSaving] = useState<boolean>(false)
  const [regenerating, setRegenerating] = useState<boolean>(false)
  const [isDragOver, setIsDragOver] = useState<boolean>(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (initialProfile) {
      setProfile(initialProfile)
    } else {
      loadProfile()
    }
  }, [initialProfile])

  const loadProfile = async () => {
    setLoading(true)
    try {
      const data = await fetchCandidateProfile()
      setProfile(data)
      onProfileUpdated?.(data)
    } catch (err: unknown) {
      showToast(`Failed to load profile: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showToast('Please upload a PDF file (.pdf)')
      return
    }

    setUploading(true)
    try {
      const updated = await uploadResumeFile(file)
      setProfile(updated)
      onProfileUpdated?.(updated)
      showToast(`Resume uploaded & parsed: ${updated.name || 'Profile'} ready!`)
    } catch (err: unknown) {
      showToast(`Upload failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setUploading(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileUpload(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      handleFileUpload(file)
    }
  }

  const handleFieldChange = (field: keyof ICandidateProfile, value: any) => {
    if (!profile) return
    setProfile({ ...profile, [field]: value })
  }

  const handleBulletChange = (index: number, value: string) => {
    if (!profile) return
    const nextBullets = [...(profile.bullets || [])]
    nextBullets[index] = value
    setProfile({ ...profile, bullets: nextBullets })
  }

  const handleAddBullet = () => {
    if (!profile) return
    const nextBullets = [...(profile.bullets || []), '']
    setProfile({ ...profile, bullets: nextBullets })
  }

  const handleRemoveBullet = (index: number) => {
    if (!profile) return
    const nextBullets = (profile.bullets || []).filter((_, i) => i !== index)
    setProfile({ ...profile, bullets: nextBullets })
  }

  const handleSaveProfile = async () => {
    if (!profile) return
    setSaving(true)
    try {
      const updated = await updateCandidateProfile(profile)
      setProfile(updated)
      onProfileUpdated?.(updated)
      showToast('Profile updated successfully!')
    } catch (err: unknown) {
      showToast(`Failed to save: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setSaving(false)
    }
  }

  const handleRegenerateDrafts = async () => {
    setRegenerating(true)
    try {
      const res = await regenerateDraftsWithProfile()
      showToast(`Updated ${res.updated_count} pending drafts with current profile!`)
    } catch (err: unknown) {
      showToast(`Regeneration failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setRegenerating(false)
    }
  }

  const getInitials = (name: string) => {
    const parts = name.trim().split(/\s+/)
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    return (name[0] || 'U').toUpperCase()
  }

  if (loading && !profile) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <RefreshCw size={24} className="animate-spin text-zinc-400" />
        <p className="text-xs text-zinc-400 font-medium">Loading candidate profile...</p>
      </div>
    )
  }

  const curr = profile || {
    id: 'active',
    name: 'Candidate',
    title: 'Product Engineer',
    email: '',
    bullets: [],
    skills: [],
    resume_filename: 'Resume.pdf',
  }

  return (
    <div className="space-y-6 w-full max-w-5xl mx-auto animate-fade-in pb-12">
      {/* 1. Header Profile Banner */}
      <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-xs p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center text-white text-xl font-bold font-mono shadow-xs flex-shrink-0">
            {getInitials(curr.name || 'Candidate')}
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl font-semibold text-zinc-900 tracking-tight">
                {curr.name || 'Candidate Name'}
              </h1>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold">
                <CheckCircle2 size={12} /> Active Profile
              </span>
            </div>
            <p className="text-sm text-zinc-500 font-medium">{curr.title || 'Product Engineer'}</p>
            <div className="flex items-center gap-4 pt-1 text-xs text-zinc-400 flex-wrap">
              {curr.email && (
                <span className="flex items-center gap-1.5">
                  <Mail size={13} /> {curr.email}
                </span>
              )}
              {curr.phone && (
                <span className="flex items-center gap-1.5">
                  <Phone size={13} /> {curr.phone}
                </span>
              )}
              {curr.location && (
                <span className="flex items-center gap-1.5">
                  <MapPin size={13} /> {curr.location}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Quick Links & Preview */}
        <div className="flex items-center gap-2 flex-wrap">
          <a
            href="/api/outbox/resume/download"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium transition shadow-xs"
          >
            <FileText size={13} />
            <span>Preview Resume</span>
            <ExternalLink size={11} className="text-zinc-400" />
          </a>

          {curr.portfolio && (
            <a
              href={curr.portfolio}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition shadow-xs"
            >
              <Globe size={13} />
              <span>Portfolio</span>
            </a>
          )}

          {curr.github && (
            <a
              href={curr.github}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition shadow-xs"
            >
              <Github size={13} />
              <span>GitHub</span>
            </a>
          )}

          {curr.linkedin && (
            <a
              href={curr.linkedin}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition shadow-xs"
            >
              <Linkedin size={13} />
              <span>LinkedIn</span>
            </a>
          )}
        </div>
      </div>

      {/* 2. Resume Upload Drag & Drop Zone */}
      <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-xs p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-zinc-900 font-semibold text-sm">
            <Upload size={16} className="text-violet-600" />
            <span>Upload Resume (PDF)</span>
          </div>
          <span className="text-xs text-zinc-400">Deterministic PDF parsing · No API key needed</span>
        </div>

        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-150 ${
            isDragOver
              ? 'border-violet-500 bg-violet-50/50'
              : 'border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="hidden"
          />

          {uploading ? (
            <div className="flex flex-col items-center space-y-3 py-2">
              <RefreshCw size={28} className="animate-spin text-violet-600" />
              <div className="space-y-1">
                <p className="text-sm font-semibold text-zinc-900">
                  Parsing resume & generating pitch bullets...
                </p>
                <p className="text-xs text-zinc-500">
                  Extracting contact, links, technical accomplishments, and skills.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-3">
              <div className="w-12 h-12 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center">
                <FileCheck size={22} />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-zinc-800">
                  <span className="text-violet-600 font-semibold hover:underline">
                    Click to upload
                  </span>{' '}
                  or drag and drop your PDF resume
                </p>
                <p className="text-xs text-zinc-400">PDF up to 10MB</p>
              </div>
            </div>
          )}
        </div>

        {/* Current Active File Info */}
        <div className="bg-zinc-50 border border-zinc-100 rounded-xl p-4 flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white border border-zinc-200 flex items-center justify-center text-zinc-600">
              <FileText size={15} />
            </div>
            <div>
              <p className="font-semibold text-zinc-900">
                {curr.resume_filename || 'No resume file attached'}
              </p>
              <p className="text-zinc-400 text-[11px]">
                {resumeStatus?.size_kb ? `${resumeStatus.size_kb} KB · ` : ''}
                Mandatory attachment for all cold enquiry emails
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/api/outbox/resume/download"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-zinc-200 hover:border-zinc-300 text-zinc-700 font-medium transition"
            >
              <ExternalLink size={12} />
              <span>Preview in New Tab</span>
            </a>
          </div>
        </div>
      </div>

      {/* 3. Candidate Identity & Contact Details */}
      <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-xs p-6 space-y-5">
        <div className="border-b border-zinc-100 pb-3">
          <h2 className="text-sm font-semibold text-zinc-900">Contact & Online Profiles</h2>
          <p className="text-xs text-zinc-400">
            These links and contact details will appear in your email sign-off and headers.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">Full Name</label>
            <input
              type="text"
              value={curr.name}
              onChange={(e) => handleFieldChange('name', e.target.value)}
              className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition"
              placeholder="e.g. Alex Rivera"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">Headline / Job Title</label>
            <input
              type="text"
              value={curr.title}
              onChange={(e) => handleFieldChange('title', e.target.value)}
              className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition"
              placeholder="e.g. Product Engineer"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">Email Address</label>
            <input
              type="email"
              value={curr.email}
              onChange={(e) => handleFieldChange('email', e.target.value)}
              className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition"
              placeholder="e.g. alex@example.com"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">Phone Number</label>
            <input
              type="text"
              value={curr.phone || ''}
              onChange={(e) => handleFieldChange('phone', e.target.value)}
              className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition"
              placeholder="e.g. +1 555-123-4567"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">Location</label>
            <input
              type="text"
              value={curr.location || ''}
              onChange={(e) => handleFieldChange('location', e.target.value)}
              className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition"
              placeholder="e.g. San Francisco, CA / Remote"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">Portfolio URL</label>
            <input
              type="text"
              value={curr.portfolio || ''}
              onChange={(e) => handleFieldChange('portfolio', e.target.value)}
              className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition"
              placeholder="https://..."
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">GitHub Profile URL</label>
            <input
              type="text"
              value={curr.github || ''}
              onChange={(e) => handleFieldChange('github', e.target.value)}
              className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition"
              placeholder="https://github.com/..."
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">LinkedIn Profile URL</label>
            <input
              type="text"
              value={curr.linkedin || ''}
              onChange={(e) => handleFieldChange('linkedin', e.target.value)}
              className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition"
              placeholder="https://linkedin.com/in/..."
            />
          </div>
        </div>
      </div>

      {/* 4. Cold Outreach Pitch Bullets (The 3 bullets) */}
      <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-xs p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-amber-500" />
              <h2 className="text-sm font-semibold text-zinc-900">
                Cold Outreach Pitch Bullets
              </h2>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              These top 3 accomplishments are injected into every outreach email enquiry.
            </p>
          </div>
          <button
            onClick={handleAddBullet}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-zinc-200 hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition"
          >
            <Plus size={12} />
            <span>Add Bullet</span>
          </button>
        </div>

        <div className="space-y-3">
          {(curr.bullets || []).map((bullet, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <span className="w-6 h-6 rounded-lg bg-zinc-100 text-zinc-500 flex items-center justify-center text-xs font-mono font-semibold flex-shrink-0 mt-1">
                {idx + 1}
              </span>
              <div className="flex-1">
                <textarea
                  rows={2}
                  value={bullet}
                  onChange={(e) => handleBulletChange(idx, e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-zinc-50 border border-zinc-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-violet-500 focus:bg-white transition leading-relaxed"
                  placeholder="e.g. Scaled production infrastructure to 50k rpm with sub-50ms latency..."
                />
              </div>
              <button
                onClick={() => handleRemoveBullet(idx)}
                className="p-1.5 text-zinc-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition mt-1"
                title="Remove bullet"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}

          {(!curr.bullets || curr.bullets.length === 0) && (
            <div className="text-center py-6 text-zinc-400 text-xs">
              No pitch bullets found. Click "Add Bullet" or re-upload your resume.
            </div>
          )}
        </div>
      </div>

      {/* 5. Sticky Save & Batch Actions Bar */}
      <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-xs p-5 flex flex-col sm:flex-row items-center justify-between gap-4 sticky bottom-6 z-10 backdrop-blur-md bg-white/95">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <AlertCircle size={14} className="text-violet-600 flex-shrink-0" />
          <span>Remember to save your changes and regenerate pending outbox drafts.</span>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={handleRegenerateDrafts}
            disabled={regenerating}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-semibold transition shadow-xs disabled:opacity-50"
          >
            <RefreshCw size={13} className={regenerating ? 'animate-spin' : ''} />
            <span>Regenerate Outbox Drafts</span>
          </button>

          <button
            onClick={handleSaveProfile}
            disabled={saving}
            className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-5 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold transition shadow-xs disabled:opacity-50"
          >
            <Save size={13} className={saving ? 'animate-spin' : ''} />
            <span>Save Profile Changes</span>
          </button>
        </div>
      </div>
    </div>
  )
}
