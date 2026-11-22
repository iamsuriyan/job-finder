import {
  Article,
  CandidateProfile,
  ConfigSummary,
  ContactedRecipient,
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

export async function fetchOutbox(
  status?: string
): Promise<{
  items: DraftEmail[]
  stats: DraftStats
  contacted_recipients?: Record<string, ContactedRecipient>
}> {
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

export async function sendDraft(
  draftId: string,
  force: boolean = false
): Promise<{ ok: boolean; message: string; recipient: string }> {
  const query = force ? '?force=true' : ''
  const res = await fetch(`${BASE_URL}/api/outbox/${encodeURIComponent(draftId)}/send${query}`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Dispatch failed' }))
    const error = new Error(err.detail || 'Dispatch failed')
    if (res.status === 409) {
      ;(error as any).isDuplicate = true
    }
    throw error
  }
  return res.json()
}

export async function fetchContactedRecipients(): Promise<Record<string, ContactedRecipient>> {
  const res = await fetch(`${BASE_URL}/api/outbox/recipients/contacted`)
  if (!res.ok) throw new Error('Failed to fetch contacted recipients')
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

export async function fetchCandidateProfile(): Promise<CandidateProfile> {
  const res = await fetch(`${BASE_URL}/api/candidate/profile`)
  if (!res.ok) throw new Error('Failed to load candidate profile')
  return res.json()
}

export async function uploadResumeFile(file: File): Promise<CandidateProfile> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE_URL}/api/candidate/resume/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to upload resume' }))
    throw new Error(err.detail || 'Failed to upload resume')
  }
  return res.json()
}

export async function updateCandidateProfile(
  payload: Partial<CandidateProfile>
): Promise<CandidateProfile> {
  const res = await fetch(`${BASE_URL}/api/candidate/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update candidate profile' }))
    throw new Error(err.detail || 'Failed to update candidate profile')
  }
  return res.json()
}

export async function dismissArticle(articleId: string): Promise<{ success: boolean; article_id: string }> {
  const res = await fetch(`${BASE_URL}/api/articles/${encodeURIComponent(articleId)}/dismiss`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to dismiss article' }))
    throw new Error(err.detail || 'Failed to dismiss article')
  }
  return res.json()
}

export async function regenerateDraftsWithProfile(): Promise<{ updated_count: number }> {
  const res = await fetch(`${BASE_URL}/api/candidate/regenerate-drafts`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to regenerate drafts' }))
    throw new Error(err.detail || 'Failed to regenerate drafts')
  }
  return res.json()
}
