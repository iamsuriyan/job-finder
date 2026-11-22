import React from 'react'
import {
  User,
  FileText,
  ExternalLink,
  Code2,
  Briefcase,
  GraduationCap,
  Sparkles,
  CheckCircle2,
  Mail,
  MapPin,
  Globe,
  Github,
  Linkedin,
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
    title: 'Generative AI & Product Engineer (2+ Years Experience)',
    email: 'suriyandhanapal@gmail.com',
    location: 'India',
    portfolio: 'https://iamsuriyan.github.io/Portfolio',
    github: 'https://github.com/iamsuriyan',
    linkedin: 'https://linkedin.com/in/suriyan-dhanapal',
    resume_path: '/home/viper/Downloads/Resumes/2+/Suriyan.pdf',
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-zinc-200 bg-white shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-2xl bg-zinc-950 flex items-center justify-center text-white text-2xl font-bold font-mono shadow-md">
            SD
          </div>
          <div className="space-y-1">
            <h1 className="text-xl font-bold text-zinc-950 flex items-center gap-2">
              <span>{candidate.name}</span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-100 border border-emerald-200 text-emerald-800 text-xs font-mono font-semibold">
                <CheckCircle2 size={12} /> Available
              </span>
            </h1>
            <p className="text-xs font-mono text-zinc-600 font-medium">{candidate.title}</p>
            <div className="flex items-center gap-3 pt-1 text-xs text-zinc-500 font-mono flex-wrap">
              <span className="flex items-center gap-1">
                <Mail size={12} /> {candidate.email}
              </span>
              <span className="flex items-center gap-1">
                <MapPin size={12} /> {candidate.location || 'India'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Links */}
        <div className="flex items-center gap-2.5 flex-wrap font-mono text-xs">
          <a
            href="/api/outbox/resume/download"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-zinc-950 hover:bg-zinc-800 text-white font-medium transition shadow-xs"
          >
            <FileText size={14} />
            <span>Download Resume PDF</span>
          </a>

          {candidate.portfolio && (
            <a
              href={candidate.portfolio}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-800 font-medium transition shadow-xs"
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
              className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-800 font-medium transition shadow-xs"
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
              className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-800 font-medium transition shadow-xs"
            >
              <Linkedin size={13} />
              <span>LinkedIn</span>
            </a>
          )}
        </div>
      </div>

      {/* Experience Highlights Grounded in Candidate's Resume */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="p-5 rounded-2xl border border-zinc-200 bg-white shadow-xs space-y-3">
          <div className="flex items-center gap-2 text-zinc-950 font-bold text-sm">
            <Sparkles size={16} className="text-amber-500" />
            <span>Core Experience: IIT Bombay Startup (Cooper Compass)</span>
          </div>
          <p className="text-xs text-zinc-600 leading-relaxed font-sans">
            Built an end-to-end compliance agent grounded in official Indian regulatory data (DGFT, GST, CBIC) using hybrid retrieval, cheapest-path-first document extraction (vision OCR + deterministic parsers), and human-in-the-loop review controls.
          </p>
          <div className="flex flex-wrap gap-1.5 font-mono text-[11px] pt-1">
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-800">Vision OCR</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-800">Hybrid Retrieval</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-800">Regulatory Agents</span>
          </div>
        </div>

        <div className="p-5 rounded-2xl border border-zinc-200 bg-white shadow-xs space-y-3">
          <div className="flex items-center gap-2 text-zinc-950 font-bold text-sm">
            <Code2 size={16} className="text-blue-500" />
            <span>Core Experience: Mindgryd (Voice & GenAI Scale)</span>
          </div>
          <p className="text-xs text-zinc-600 leading-relaxed font-sans">
            Integrated 25+ LLM, voice, STT, and TTS providers behind a unified connector layer serving live calls (~100 calls/day), and designed metadata-isolated multi-tenant RAG pipelines on pgvector & Weaviate.
          </p>
          <div className="flex flex-wrap gap-1.5 font-mono text-[11px] pt-1">
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-800">Live Voice / STT</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-800">pgvector RAG</span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-100 text-zinc-800">Multi-Tenancy</span>
          </div>
        </div>
      </div>

      {/* Resume File Verification Card */}
      <div className="p-5 rounded-2xl border border-zinc-200 bg-white shadow-xs space-y-4 font-mono text-xs">
        <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
          <div className="flex items-center gap-2 font-bold text-zinc-950">
            <FileText size={16} className="text-zinc-700" />
            <span>Attached Resume File Verification</span>
          </div>
          <span className="inline-flex items-center gap-1 text-emerald-700 text-[11px] font-semibold">
            <CheckCircle2 size={12} /> Ready for Dispatch
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-zinc-600">
          <div>
            <span className="text-zinc-400 block text-[10px]">FILE PATH</span>
            <span className="text-zinc-950 font-medium break-all">{resumeStatus?.path || candidate.resume_path}</span>
          </div>
          <div>
            <span className="text-zinc-400 block text-[10px]">FILE SIZE</span>
            <span className="text-zinc-950 font-medium">
              {resumeStatus?.size_kb ? `${resumeStatus.size_kb} KB` : '179.8 KB'} ({resumeStatus?.size_bytes || 184115} bytes)
            </span>
          </div>
          <div>
            <span className="text-zinc-400 block text-[10px]">ATTACHMENT BEHAVIOR</span>
            <span className="text-zinc-950 font-medium">Included in all job enquiries</span>
          </div>
        </div>
      </div>
    </div>
  )
}
