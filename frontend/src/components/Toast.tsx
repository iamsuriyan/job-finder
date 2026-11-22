import React from 'react'
import { CheckCircle2, Sparkles } from 'lucide-react'

interface ToastProps {
  message: string | null
  onClose: () => void
}

export const Toast: React.FC<ToastProps> = ({ message }) => {
  if (!message) return null

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-slideIn select-none">
      <div className="flex items-center gap-2.5 px-4 py-3 rounded-2xl bg-zinc-950 text-white font-mono text-xs font-medium shadow-float border border-zinc-800">
        <Sparkles size={14} className="text-amber-400 shrink-0" />
        <span>{message}</span>
      </div>
    </div>
  )
}
