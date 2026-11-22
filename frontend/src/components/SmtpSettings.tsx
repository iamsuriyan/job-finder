import React, { useState } from 'react'
import { Settings, Send, CheckCircle2, AlertCircle, Shield, Key } from 'lucide-react'
import { ConfigSummary } from '../types'
import { testSmtpConnection } from '../api/client'

interface SmtpSettingsProps {
  config?: ConfigSummary | null
  showToast: (msg: string) => void
}

export const SmtpSettings: React.FC<SmtpSettingsProps> = ({ config, showToast }) => {
  const [host, setHost] = useState(config?.smtp?.host || 'smtp.gmail.com')
  const [port, setPort] = useState(config?.smtp?.port || 587)
  const [user, setUser] = useState(config?.smtp?.user || '')
  const [password, setPassword] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)

  const handleTestConnection = async (e: React.FormEvent) => {
    e.preventDefault()
    setTesting(true)
    setTestResult(null)
    try {
      const res = await testSmtpConnection({
        host,
        port: Number(port),
        user,
        password: password || undefined,
      })
      setTestResult(res)
      showToast(res.ok ? 'SMTP handshake verified!' : 'SMTP connection failed')
    } catch (err: any) {
      setTestResult({ ok: false, message: err.message })
      showToast(`SMTP test error: ${err.message}`)
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="p-6 rounded-2xl border border-zinc-200 bg-white shadow-xs">
        <h1 className="text-xl font-bold text-zinc-950 flex items-center gap-2">
          <span>Outreach SMTP & Email Settings</span>
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-semibold ${
              config?.smtp?.configured
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                : 'bg-zinc-100 text-zinc-700 border border-zinc-200'
            }`}
          >
            {config?.smtp?.configured ? 'Configured' : 'Credentials Optional'}
          </span>
        </h1>
        <p className="text-xs text-zinc-500 mt-1">
          Configure SMTP credentials to dispatch personalized cold job enquiries upon explicit human review and approval.
        </p>
      </div>

      <div className="p-6 rounded-2xl border border-zinc-200 bg-white shadow-xs space-y-6">
        <div className="flex items-center gap-2.5 pb-4 border-b border-zinc-100 text-zinc-950 font-bold text-sm">
          <Shield size={18} className="text-zinc-700" />
          <span>SMTP Server Credentials</span>
        </div>

        <form onSubmit={handleTestConnection} className="space-y-4 font-mono text-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-[11px] font-semibold text-zinc-600 mb-1.5">
                SMTP HOSTNAME
              </label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="smtp.gmail.com"
                className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-950 focus:outline-none transition shadow-xs text-xs font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-zinc-600 mb-1.5">
                PORT (587 / 465)
              </label>
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(Number(e.target.value))}
                placeholder="587"
                className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-950 focus:outline-none transition shadow-xs text-xs font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] font-semibold text-zinc-600 mb-1.5">
                SMTP USERNAME / EMAIL
              </label>
              <input
                type="text"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                placeholder="suriyandhanapal@gmail.com"
                className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-950 focus:outline-none transition shadow-xs text-xs font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-zinc-600 mb-1.5">
                APP PASSWORD
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Google App Password (16 chars)"
                className="w-full px-3.5 py-2.5 rounded-xl border border-zinc-200 bg-zinc-50 hover:bg-white focus:bg-white focus:border-zinc-950 focus:outline-none transition shadow-xs text-xs font-mono"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between">
            <span className="text-[11px] text-zinc-500">
              Settings can also be persisted via <code>.env</code> file.
            </span>

            <button
              type="submit"
              disabled={testing || !host || !user}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-zinc-950 hover:bg-zinc-800 text-white font-bold transition shadow-xs disabled:opacity-50"
            >
              {testing ? (
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <Key size={13} />
              )}
              <span>{testing ? 'Testing Handshake...' : 'Test SMTP Connection'}</span>
            </button>
          </div>
        </form>

        {testResult && (
          <div
            className={`p-4 rounded-xl border font-mono text-xs animate-fadeIn flex items-start gap-3 ${
              testResult.ok
                ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                : 'border-red-200 bg-red-50 text-red-900'
            }`}
          >
            {testResult.ok ? (
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle size={16} className="text-red-600 shrink-0 mt-0.5" />
            )}
            <div>
              <span className="font-bold">{testResult.ok ? 'Connection Verified' : 'Connection Failed'}</span>
              <p className="mt-0.5 text-[11px] opacity-90">{testResult.message}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
