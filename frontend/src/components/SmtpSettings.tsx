import React, { useState, useEffect } from 'react'
import { Shield, Key, CheckCircle2, AlertCircle, Loader2, Save, Eye, EyeOff } from 'lucide-react'
import { ConfigSummary } from '../types'
import { testSmtpConnection, saveSmtpConfig } from '../api/client'

interface SmtpSettingsProps {
  config?: ConfigSummary | null
  showToast: (msg: string) => void
  onConfigSaved?: () => void
}

export const SmtpSettings: React.FC<SmtpSettingsProps> = ({ config, showToast, onConfigSaved }) => {
  const [host, setHost] = useState(config?.smtp?.host || 'smtp.gmail.com')
  const [port, setPort] = useState(config?.smtp?.port || 587)
  const [user, setUser] = useState(config?.smtp?.user || '')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)

  useEffect(() => {
    if (config?.smtp) {
      if (config.smtp.host) setHost(config.smtp.host)
      if (config.smtp.port) setPort(config.smtp.port)
      if (config.smtp.user) setUser(config.smtp.user)
    }
  }, [config])

  const handleTestConnection = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
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

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await saveSmtpConfig({
        smtp_host: host,
        smtp_port: Number(port),
        smtp_user: user,
        smtp_password: password || undefined,
      })
      showToast('SMTP settings saved to .env!')
      setPassword('')
      if (onConfigSaved) onConfigSaved()
    } catch (err: any) {
      showToast(`Failed to save settings: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const hasConfiguredPassword = Boolean(config?.smtp?.has_password)
  const maskedPassword = config?.smtp?.password_masked || '••••••••••••'

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
            {config?.smtp?.configured ? 'Active & Configured' : 'Credentials Optional'}
          </span>
        </h1>
        <p className="text-sm text-zinc-400 mt-0.5">
          Configure Gmail or custom SMTP credentials to dispatch personalized cold job enquiries upon your explicit human review.
        </p>
      </div>

      {/* Form Card */}
      <div className="bg-white border border-zinc-100 rounded-xl shadow-sm p-6 space-y-5">
        <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
          <div className="flex items-center gap-2.5 text-zinc-900 font-semibold text-sm">
            <Shield size={16} className="text-violet-600" />
            <span>Server Credentials</span>
          </div>

          {hasConfiguredPassword && (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              <CheckCircle2 size={12} className="text-emerald-600" />
              App Password Loaded from .env ({maskedPassword})
            </span>
          )}
        </div>

        <form onSubmit={handleSaveConfig} className="space-y-4 text-xs">
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
              <div className="flex items-center justify-between mb-1.5">
                <label className="block font-medium text-zinc-700">
                  GMAIL APP PASSWORD
                </label>
                {hasConfiguredPassword && (
                  <span className="text-[11px] text-emerald-600 font-mono">
                    ✓ Configured ({maskedPassword})
                  </span>
                )}
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={
                    hasConfiguredPassword
                      ? `Active: ${maskedPassword} (leave empty to keep)`
                      : 'Google App Password (16 characters)'
                  }
                  className="w-full px-3 py-2 pr-16 rounded-lg border border-zinc-200 bg-white focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none transition text-xs font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 p-1"
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <p className="mt-1 text-[11px] text-zinc-400">
                {hasConfiguredPassword
                  ? `Your App Password is encrypted and active in .env (${maskedPassword}). Enter a new 16-character password only to replace it.`
                  : 'Requires a Google 16-character App Password (not your normal Gmail password).'}
              </p>
            </div>
          </div>

          <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-zinc-100">
            <span className="text-xs text-zinc-400">
              Settings and App Password are automatically saved to your <code>.env</code> file.
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleTestConnection()}
                disabled={testing || !host || (!password && !hasConfiguredPassword)}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-zinc-200 hover:bg-zinc-50 text-zinc-700 font-medium text-xs transition disabled:opacity-50 cursor-pointer"
              >
                {testing ? <Loader2 size={13} className="animate-spin text-zinc-500" /> : <Key size={13} />}
                <span>{testing ? 'Testing Handshake...' : 'Test Connection'}</span>
              </button>

              <button
                type="submit"
                disabled={saving || !host}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white font-medium text-xs transition shadow-xs disabled:opacity-50 cursor-pointer"
              >
                {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                <span>{saving ? 'Saving...' : 'Save to .env'}</span>
              </button>
            </div>
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
