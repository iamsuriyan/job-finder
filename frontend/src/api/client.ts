import {
  Article,
  ConfigSummary,
  DraftEmail,
  DraftStats,
  FeedInfo,
  OverallStats,
  ResumeStatus,
} from '../types'

const BASE_URL = ''

export async function fetchArticles(params: {
  page?: number
  limit?: number
  matched_only?: boolean
  search?: string
  feed?: string
  stage?: string
}): Promise<{ items: Article[]; total: number; page: number; limit: number; total_pages: number }> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page.toString())
  if (params.limit) query.set('limit', params.limit.toString())
  if (params.matched_only !== undefined) query.set('matched_only', params.matched_only.toString())
  if (params.search) query.set('search', params.search)
  if (params.feed) query.set('feed', params.feed)
  if (params.stage) query.set('stage', params.stage)

  const res = await fetch(`${BASE_URL}/api/articles?${query.toString()}`)
  if (!res.ok) throw new Error('Failed to load articles')
  return res.json()
}

export async function fetchStats(): Promise<OverallStats> {
  const res = await fetch(`${BASE_URL}/api/stats`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export async function fetchFeeds(): Promise<FeedInfo[]> {
  const res = await fetch(`${BASE_URL}/api/feeds`)
  if (!res.ok) throw new Error('Failed to fetch feeds')
  return res.json()
}

export async function testFeed(url: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/feeds/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) throw new Error('Feed test failed')
  return res.json()
}

export async function fetchConfig(): Promise<ConfigSummary> {
  const res = await fetch(`${BASE_URL}/api/config`)
  if (!res.ok) throw new Error('Failed to fetch config')
  return res.json()
}

export async function fetchOutbox(status?: string): Promise<{ items: DraftEmail[]; stats: DraftStats }> {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  const res = await fetch(`${BASE_URL}/api/outbox${query}`)
  if (!res.ok) throw new Error('Failed to fetch outbox drafts')
  return res.json()
}

export async function fetchDraft(draftId: string): Promise<DraftEmail> {
  const res = await fetch(`${BASE_URL}/api/outbox/${encodeURIComponent(draftId)}`)
  if (!res.ok) throw new Error('Failed to fetch draft')
  return res.json()
}

export async function generateDraft(articleId: string, force: boolean = false): Promise<DraftEmail> {
  const query = `article_id=${encodeURIComponent(articleId)}${force ? '&force=true' : ''}`
  const res = await fetch(`${BASE_URL}/api/outbox/generate?${query}`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to generate draft' }))
    throw new Error(err.detail || 'Failed to generate draft')
  }
  return res.json()
}

export async function updateDraft(draftId: string, payload: Partial<DraftEmail>): Promise<DraftEmail> {
  const res = await fetch(`${BASE_URL}/api/outbox/${encodeURIComponent(draftId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update draft' }))
    throw new Error(err.detail || 'Failed to update draft')
  }
  return res.json()
}

export async function deleteDraft(draftId: string): Promise<{ ok: boolean }> {
  const res = await fetch(`${BASE_URL}/api/outbox/${encodeURIComponent(draftId)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete draft')
  return res.json()
}

export async function sendDraft(draftId: string): Promise<{ ok: boolean; message: string; recipient: string }> {
  const res = await fetch(`${BASE_URL}/api/outbox/${encodeURIComponent(draftId)}/send`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Dispatch failed' }))
    throw new Error(err.detail || 'Dispatch failed')
  }
  return res.json()
}

export async function fetchResumeStatus(): Promise<ResumeStatus> {
  const res = await fetch(`${BASE_URL}/api/outbox/resume/status`)
  if (!res.ok) throw new Error('Failed to check resume status')
  return res.json()
}

export async function testSmtpConnection(payload: {
  host: string
  port: number
  user: string
  password?: string
}): Promise<{ ok: boolean; message: string }> {
  const res = await fetch(`${BASE_URL}/api/outbox/smtp/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'SMTP connection failed' }))
    throw new Error(err.detail || 'SMTP test failed')
  }
  return res.json()
}
