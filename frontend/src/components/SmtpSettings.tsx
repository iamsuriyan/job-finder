import React, { useState } from 'react'
import { Shield, Key, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
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
    <div className="space-y-5 w-full animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 tracking-tight flex items-center gap-2.5">
          SMTP & Email Settings
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
              config?.smtp?.configured
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-zinc-100 text-zinc-600 border border-zinc-200'
            }`}
          >
            {config?.smtp?.configured ? 'Configured' : 'Credentials Optional'}
          </span>
        </h1>
        <p className="text-sm text-zinc-400 mt-0.5">
          Configure SMTP credentials to dispatch cold job enquiries upon explicit human review and approval.
        </p>
      </div>

      {/* Form Card */}
      <div className="bg-white border border-zinc-100 rounded-xl shadow-sm p-6 space-y-5">
        <div className="flex items-center gap-2.5 pb-4 border-b border-zinc-100 text-zinc-900 font-semibold text-sm">
          <Shield size={16} className="text-violet-600" />
          <span>Server Credentials</span>
        </div>

        <form onSubmit={handleTestConnection} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block font-medium text-zinc-700 mb-1.5">
                SMTP HOSTNAME
              </label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="smtp.gmail.com"
                className="w-full px-3 py-2 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-zinc-700 mb-1.5">
                PORT (587 / 465)
              </label>
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(Number(e.target.value))}
                placeholder="587"
                className="w-full px-3 py-2 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs font-mono"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block font-medium text-zinc-700 mb-1.5">
                SMTP USERNAME / EMAIL
              </label>
              <input
                type="text"
                value={user}
                onChange={(e) => setUser(e.target.value)}
                placeholder="suriyandhanapal@gmail.com"
                className="w-full px-3 py-2 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs font-mono"
              />
            </div>

            <div>
              <label className="block font-medium text-zinc-700 mb-1.5">
                APP PASSWORD
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Google App Password (16 chars)"
                className="w-full px-3 py-2 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs font-mono"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between">
            <span className="text-xs text-zinc-400">
              Credentials can also be persisted via your <code>.env</code> file.
            </span>

            <button
              type="submit"
              disabled={testing || !host || !user}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white font-medium text-xs transition shadow-xs disabled:opacity-50"
            >
              {testing ? <Loader2 size={13} className="animate-spin" /> : <Key size={13} />}
              <span>{testing ? 'Testing Handshake...' : 'Test SMTP Connection'}</span>
            </button>
          </div>
        </form>

        {testResult && (
          <div
            className={`p-4 rounded-lg border text-xs animate-fade-in flex items-start gap-3 ${
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
              <span className="font-semibold">{testResult.ok ? 'Connection Verified' : 'Connection Failed'}</span>
              <p className="mt-0.5 text-xs opacity-90">{testResult.message}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
