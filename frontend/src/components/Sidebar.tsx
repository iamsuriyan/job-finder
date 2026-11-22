import React from 'react'
import {
  Layers,
  Flame,
  Inbox,
  Rss,
  User,
  Settings,
  ChevronLeft,
  ChevronRight,
  FileText,
  ExternalLink,
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

const navItems = [
  {
    id: 'deals',
    label: 'Funding Deals',
    sublabel: 'Live rounds',
    icon: Flame,
  },
  {
    id: 'outbox',
    label: 'Outbox',
    sublabel: 'Review queue',
    icon: Inbox,
  },
  {
    id: 'feeds',
    label: 'Feed Sources',
    sublabel: 'RSS health',
    icon: Rss,
  },
  {
    id: 'profile',
    label: 'My Profile',
    sublabel: 'Suriyan Dhanapal',
    icon: User,
  },
  {
    id: 'settings',
    label: 'SMTP Settings',
    sublabel: 'Email config',
    icon: Settings,
  },
]

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  isCollapsed,
  setIsCollapsed,
  outboxStats,
  resumeStatus,
}) => {
  return (
    <aside
      className={`fixed top-0 left-0 h-screen z-30 bg-white border-r border-zinc-100 flex flex-col transition-all duration-300 ease-spring select-none ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand */}
      <div
        className={`h-14 flex items-center border-b border-zinc-100 flex-shrink-0 ${
          isCollapsed ? 'justify-center px-0' : 'px-4 gap-3'
        }`}
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm">
          <Layers size={15} className="text-white" strokeWidth={2.5} />
        </div>
        {!isCollapsed && (
          <div className="flex flex-col animate-fade-in overflow-hidden">
            <span className="text-sm font-semibold text-zinc-900 leading-tight tracking-tight">
              FundWatch
            </span>
            <span className="text-[11px] text-zinc-400 leading-tight">
              Founder Outreach
            </span>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeTab === item.id
          const pendingBadge =
            item.id === 'outbox' && outboxStats?.draft ? outboxStats.draft : null

          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              title={isCollapsed ? item.label : undefined}
              className={`w-full group flex items-center gap-3 rounded-lg transition-all duration-150 ${
                isCollapsed ? 'justify-center px-0 py-2.5' : 'px-3 py-2'
              } ${
                isActive
                  ? 'bg-violet-50 text-violet-700'
                  : 'text-zinc-500 hover:text-zinc-800 hover:bg-zinc-50'
              }`}
            >
              {/* Active left indicator */}
              {!isCollapsed && (
                <span
                  className={`absolute left-0 w-0.5 h-6 rounded-r-full bg-violet-600 transition-all duration-150 ${
                    isActive ? 'opacity-100' : 'opacity-0'
                  }`}
                />
              )}

              <Icon
                size={17}
                strokeWidth={isActive ? 2.2 : 1.8}
                className={`flex-shrink-0 transition-colors duration-150 ${
                  isActive ? 'text-violet-600' : 'text-zinc-400 group-hover:text-zinc-600'
                }`}
              />

              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between min-w-0">
                  <span
                    className={`text-sm truncate ${
                      isActive ? 'font-semibold text-violet-800' : 'font-medium'
                    }`}
                  >
                    {item.label}
                  </span>
                  {pendingBadge !== null && (
                    <span className="ml-2 px-1.5 py-0.5 rounded-full bg-violet-600 text-white text-[10px] font-mono font-bold leading-none">
                      {pendingBadge}
                    </span>
                  )}
                </div>
              )}

              {isCollapsed && pendingBadge !== null && (
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-violet-600" />
              )}
            </button>
          )
        })}
      </nav>

      {/* Resume widget */}
      {!isCollapsed && (
        <div className="px-3 py-3 border-t border-zinc-100 animate-fade-in">
          <div className="bg-zinc-50 border border-zinc-100 rounded-xl p-3 space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-zinc-200 flex items-center justify-center flex-shrink-0">
                <FileText size={13} className="text-zinc-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-zinc-800 truncate">Suriyan.pdf</p>
                {resumeStatus?.size_kb && (
                  <p className="text-[10px] text-zinc-400">{resumeStatus.size_kb} KB</p>
                )}
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" title="Resume attached" />
            </div>
            <a
              href="/api/outbox/resume/download"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 w-full px-2.5 py-1.5 rounded-lg bg-white border border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50 text-zinc-600 text-xs font-medium transition-all duration-150"
            >
              <ExternalLink size={11} />
              <span>Preview Resume</span>
            </a>
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <div className={`py-3 border-t border-zinc-100 flex ${isCollapsed ? 'justify-center' : 'px-3'}`}>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-50 transition-all duration-150 w-full justify-center text-xs font-medium"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <ChevronRight size={15} />
          ) : (
            <>
              <ChevronLeft size={15} />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}
