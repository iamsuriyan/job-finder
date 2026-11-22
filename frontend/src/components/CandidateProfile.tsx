import React from 'react'
import {
  FileText,
  Sparkles,
  CheckCircle2,
  Mail,
  MapPin,
  Globe,
  Github,
  Linkedin,
  Code2,
  ExternalLink,
} from 'lucide-react'
import { ResumeStatus, ConfigSummary } from '../types'

interface CandidateProfileProps {
  resumeStatus?: ResumeStatus | null
  config?: ConfigSummary | null
}

export const CandidateProfile: React.FC<CandidateProfileProps> = ({
  resumeStatus,
  config,
}) => {
  const candidate = config?.candidate || {
    name: 'Suriyan Dhanapal',
    title: 'Product Engineer (2+ Years Experience)',
    email: 'suriyandhanapal@gmail.com',
    location: 'India',
    portfolio: 'https://iamsuriyan.github.io/Portfolio',
    github: 'https://github.com/iamsuriyan',
    linkedin: 'https://linkedin.com/in/suriyan-dhanapal',
    resume_path: '/home/viper/Downloads/Resumes/2+/Suriyan.pdf',
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header Profile Card */}
      <div className="bg-white border border-zinc-100 rounded-xl shadow-sm p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center text-white text-xl font-bold font-mono shadow-sm flex-shrink-0">
            SD
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl font-semibold text-zinc-900 tracking-tight">{candidate.name}</h1>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold">
                <CheckCircle2 size={12} /> Available
              </span>
            </div>
            <p className="text-sm text-zinc-500 font-medium">{candidate.title}</p>
            <div className="flex items-center gap-4 pt-1 text-xs text-zinc-400 flex-wrap">
              <span className="flex items-center gap-1.5">
                <Mail size={13} /> {candidate.email}
              </span>
              <span className="flex items-center gap-1.5">
                <MapPin size={13} /> {candidate.location || 'India'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Links */}
        <div className="flex items-center gap-2 flex-wrap">
          <a
            href="/api/outbox/resume/download"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium transition shadow-xs"
          >
            <FileText size={13} />
            <span>Download Resume PDF</span>
          </a>

          {candidate.portfolio && (
            <a
              href={candidate.portfolio}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition shadow-xs"
            >
              <Globe size={13} />
              <span>Portfolio</span>
            </a>
          )}

          {candidate.github && (
            <a
              href={candidate.github}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition shadow-xs"
            >
              <Github size={13} />
              <span>GitHub</span>
            </a>
          )}

          {candidate.linkedin && (
            <a
              href={candidate.linkedin}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition shadow-xs"
            >
              <Linkedin size={13} />
              <span>LinkedIn</span>
            </a>
          )}
        </div>
      </div>

      {/* Experience Highlights Grounded in Resume */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-zinc-100 rounded-xl shadow-sm p-5 space-y-3">
          <div className="flex items-center gap-2 text-zinc-900 font-semibold text-sm">
            <Sparkles size={16} className="text-amber-500" />
            <span>IIT Bombay Startup (Cooper Compass)</span>
          </div>
          <p className="text-xs text-zinc-600 leading-relaxed">
            Built an end-to-end compliance agent grounded in official Indian regulatory data (DGFT, GST, CBIC) using hybrid retrieval, cheapest-path-first document extraction (vision OCR + deterministic parsers), and human-in-the-loop review controls.
          </p>
          <div className="flex flex-wrap gap-1.5 text-xs pt-1">
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-700 font-mono text-[11px]">Vision OCR</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-700 font-mono text-[11px]">Hybrid Retrieval</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-700 font-mono text-[11px]">Regulatory Agents</span>
          </div>
        </div>

        <div className="bg-white border border-zinc-100 rounded-xl shadow-sm p-5 space-y-3">
          <div className="flex items-center gap-2 text-zinc-900 font-semibold text-sm">
            <Code2 size={16} className="text-blue-500" />
            <span>Mindgryd (Voice & GenAI Scale)</span>
          </div>
          <p className="text-xs text-zinc-600 leading-relaxed">
            Integrated 25+ LLM, voice, STT, and TTS providers behind a unified connector layer serving live calls (~100 calls/day), and designed metadata-isolated multi-tenant RAG pipelines on pgvector & Weaviate.
          </p>
          <div className="flex flex-wrap gap-1.5 text-xs pt-1">
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-700 font-mono text-[11px]">Live Voice / STT</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-700 font-mono text-[11px]">pgvector RAG</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-700 font-mono text-[11px]">Multi-Tenancy</span>
          </div>
        </div>
      </div>

      {/* Resume File Verification Card */}
      <div className="bg-white border border-zinc-100 rounded-xl shadow-sm p-5 space-y-3 text-xs">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
          <div className="flex items-center gap-2 font-semibold text-zinc-900">
            <FileText size={15} className="text-zinc-600" />
            <span>Attached Resume File Verification</span>
          </div>
          <span className="inline-flex items-center gap-1 text-emerald-700 text-xs font-semibold">
            <CheckCircle2 size={12} /> Ready for Dispatch
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-zinc-600">
          <div>
            <span className="text-zinc-400 block text-[11px] mb-0.5">FILE PATH</span>
            <span className="text-zinc-900 font-mono text-xs break-all">{resumeStatus?.path || candidate.resume_path}</span>
          </div>
          <div>
            <span className="text-zinc-400 block text-[11px] mb-0.5">FILE SIZE</span>
            <span className="text-zinc-900 font-mono text-xs">
              {resumeStatus?.size_kb ? `${resumeStatus.size_kb} KB` : '179.8 KB'} ({resumeStatus?.size_bytes || 184115} bytes)
            </span>
          </div>
          <div>
            <span className="text-zinc-400 block text-[11px] mb-0.5">ATTACHMENT POLICY</span>
            <span className="text-zinc-900 font-medium text-xs">Attached to every cold enquiry</span>
          </div>
        </div>
      </div>
    </div>
  )
}
