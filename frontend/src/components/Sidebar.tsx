import React from 'react'
import {
  Flame,
  Inbox,
  Rss,
  User,
  Settings,
  ChevronLeft,
  ChevronRight,
  FileText,
  ExternalLink,
  Sparkles,
} from 'lucide-react'
import { ResumeStatus, DraftStats } from '../types'

interface SidebarProps {
  activeTab: string
  setActiveTab: (tab: string) => void
  isCollapsed: boolean
  setIsCollapsed: (collapsed: boolean) => void
  outboxStats?: DraftStats
  resumeStatus?: ResumeStatus | null
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  isCollapsed,
  setIsCollapsed,
  outboxStats,
  resumeStatus,
}) => {
  const navItems = [
    {
      id: 'deals',
      label: 'Funding Deals',
      sublabel: 'Live Startup Deals',
      icon: Flame,
      badge: null,
    },
    {
      id: 'outbox',
      label: 'Outbox & Review',
      sublabel: 'Human Review Queue',
      icon: Inbox,
      badge: outboxStats?.draft ? `${outboxStats.draft}` : null,
      badgeColor: 'bg-zinc-950 text-white',
    },
    {
      id: 'feeds',
      label: 'Feed Sources',
      sublabel: 'Health & Status',
      icon: Rss,
      badge: null,
    },
    {
      id: 'profile',
      label: 'Candidate Profile',
      sublabel: 'Suriyan Dhanapal',
      icon: User,
      badge: null,
    },
    {
      id: 'settings',
      label: 'SMTP & Config',
      sublabel: 'Outreach Settings',
      icon: Settings,
      badge: null,
    },
  ]

  return (
    <aside
      className={`fixed top-0 left-0 h-screen z-30 flex flex-col justify-between border-r border-zinc-200 bg-white transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] select-none ${
        isCollapsed ? 'w-20' : 'w-72'
      }`}
    >
      {/* Top Section: Brand & Navigation */}
      <div className="flex flex-col">
        {/* Brand Header */}
        <div className="h-18 px-5 border-b border-zinc-100 flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center gap-3 animate-fadeIn">
              <div className="w-9 h-9 rounded-xl bg-zinc-950 flex items-center justify-center text-white font-mono text-base font-bold shadow-xs">
                ⚡
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-sm tracking-tight text-zinc-950 flex items-center gap-1.5">
                  FundWatch
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                </span>
                <span className="text-[11px] font-mono text-zinc-600">Founder Outreach Engine</span>
              </div>
            </div>
          )}

          {isCollapsed && (
            <div className="mx-auto w-9 h-9 rounded-xl bg-zinc-950 flex items-center justify-center text-white font-mono text-base font-bold shadow-xs">
              ⚡
            </div>
          )}

          {/* Toggle Sidebar Collapse Button */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 rounded-lg border border-zinc-200 hover:bg-zinc-100 text-zinc-600 hover:text-zinc-900 transition-colors shadow-xs"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
          </button>
        </div>

        {/* Navigation List */}
        <nav className="p-3 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={isCollapsed ? item.label : undefined}
                className={`w-full group relative flex items-center gap-3.5 px-3 py-2.5 rounded-xl font-medium text-xs transition-all duration-150 ${
                  isActive
                    ? 'bg-zinc-950 text-white font-semibold shadow-xs'
                    : 'text-zinc-700 hover:text-zinc-950 hover:bg-zinc-100/80'
                } ${isCollapsed ? 'justify-center px-2' : ''}`}
              >
                <Icon
                  size={18}
                  className={`shrink-0 transition-transform duration-150 group-hover:scale-110 ${
                    isActive ? 'text-white' : 'text-zinc-600 group-hover:text-zinc-950'
                  }`}
                />

                {!isCollapsed && (
                  <div className="flex-1 text-left flex items-center justify-between">
                    <div className="flex flex-col">
                      <span>{item.label}</span>
                      <span
                        className={`text-[10px] font-mono leading-tight ${
                          isActive ? 'text-zinc-400' : 'text-zinc-600'
                        }`}
                      >
                        {item.sublabel}
                      </span>
                    </div>

                    {item.badge && (
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold transition-transform group-hover:scale-105 ${
                          isActive
                            ? 'bg-white text-zinc-950'
                            : 'bg-zinc-200 text-zinc-800'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Bottom Section: Attached Resume Widget & Human Guard */}
      <div className="p-3 border-t border-zinc-100 bg-zinc-50/70">
        {!isCollapsed ? (
          <div className="p-3 rounded-xl border border-zinc-200 bg-white shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-zinc-100 text-zinc-800">
                  <FileText size={14} />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-zinc-900 truncate max-w-[120px]">
                    {resumeStatus?.filename || 'Suriyan.pdf'}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-600">
                    {resumeStatus?.size_kb ? `${resumeStatus.size_kb} KB` : '179.8 KB'} • Attached
                  </span>
                </div>
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-500" title="Resume Ready"></span>
            </div>

            <a
              href="/api/outbox/resume/download"
              target="_blank"
              rel="noreferrer"
              className="w-full flex items-center justify-center gap-1.5 py-1.5 text-[11px] font-mono font-medium rounded-lg border border-zinc-200 bg-zinc-50 hover:bg-zinc-100 text-zinc-800 transition shadow-xs"
            >
              <span>Preview PDF</span>
              <ExternalLink size={11} className="text-zinc-400" />
            </a>

            <div className="pt-1 border-t border-zinc-100 flex items-center justify-between text-[10px] font-mono text-zinc-600">
              <span className="flex items-center gap-1">
                <Sparkles size={10} className="text-amber-500" /> Human Review Only
              </span>
              <span className="text-emerald-700 font-bold">100% Safe</span>
            </div>
          </div>
        ) : (
          <a
            href="/api/outbox/resume/download"
            target="_blank"
            rel="noreferrer"
            title="Preview Attached Resume PDF"
            className="flex items-center justify-center p-2.5 rounded-xl border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-700 transition shadow-xs"
          >
            <FileText size={16} />
          </a>
        )}
      </div>
    </aside>
  )
}
