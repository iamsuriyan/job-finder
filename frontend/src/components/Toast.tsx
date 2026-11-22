import React from 'react'

interface ToastProps {
  message: string | null
  onClose: () => void
}

export const Toast: React.FC<ToastProps> = ({ message, onClose }) => {
  if (!message) return null

  return (
    <div className="fixed bottom-5 right-5 z-[100] animate-slide-in-up">
      <div className="flex items-center gap-3 bg-zinc-900 text-white text-sm font-medium px-4 py-3 rounded-xl shadow-float max-w-sm">
        <span className="flex-1">{message}</span>
        <button
          onClick={onClose}
          className="text-zinc-400 hover:text-white transition-colors ml-2 text-lg leading-none"
        >
          ×
        </button>
      </div>
    </div>
  )
}
