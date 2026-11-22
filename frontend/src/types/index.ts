export interface DiscoveredEmail {
  name: string
  role: string
  email: string
  confidence?: number
  verified?: boolean
  source?: string
  provider?: string
}

export interface Founder {
  name: string
  role: string
}

export interface Article {
  id: string
  feed_name: string
  title: string
  link: string
  published_at?: string
  first_seen_at?: string
  summary?: string
  matched: number
  notified: number
  title_norm?: string
  // Extracted details
  company?: string
  amount?: number
  currency?: string
  stage?: string
  stage_tier?: 'first_funding' | 'seed' | 'series_a' | 'late' | 'unknown'
  sector?: string
  location?: string
  investors?: string[]
  domain?: string
  founders?: Founder[]
  emails?: DiscoveredEmail[]
}

export interface DraftEmail {
  id: string
  article_id: string
  company: string
  recipient_name: string
  recipient_email?: string | null
  subject: string
  body: string
  resume_path?: string
  attach_resume: boolean
  status: 'draft' | 'sent' | 'failed'
  error_message?: string | null
  sent_at?: string | null
  created_at: string
}

export interface DraftStats {
  total: number
  draft: number
  sent: number
  failed: number
}

export interface FeedInfo {
  name: string
  url: string
  healthy: boolean
  consecutive_failures: number
  last_ok_at?: string | null
  etag?: string | null
  last_modified?: string | null
}

export interface OverallStats {
  total: number
  matched: number
  notified: number
  total_feeds: number
  healthy_feeds: number
  by_feed: Record<string, number>
  by_day: Record<string, number>
  feeds: FeedInfo[]
}

export interface ResumeStatus {
  exists: boolean
  path: string
  filename: string
  size_bytes: number
  size_kb: number
}

export interface ContactedRecipient {
  draft_id: string
  company: string
  recipient_name: string
  sent_at: string
}

export interface CandidateProfile {
  id: string
  name: string
  title: string
  email: string
  phone?: string
  location?: string
  portfolio?: string
  github?: string
  linkedin?: string
  resume_path?: string
  resume_filename?: string
  bullets: string[]
  skills: string[]
  raw_text?: string
  updated_at?: string
}

export interface ConfigSummary {
  poll_interval_minutes: number
  jitter_seconds: number
  request_timeout_seconds: number
  max_items_per_feed: number
  max_article_age_days: number
  user_agent: string
  feeds_count: number
  funding_keywords: string[]
  exclude_keywords: string[]
  sector_keywords: string[]
  geo_keywords: string[]
  match_in_summary: boolean
  notifiers: { type: string; enabled: boolean; topic?: string }[]
  llm_extraction_enabled: boolean
  llm_model: string
  db_path: string
  candidate: {
    name: string
    title: string
    email: string
    phone?: string
    location?: string
    portfolio?: string
    github?: string
    linkedin?: string
    resume_path: string
  }
  smtp: {
    configured: boolean
    host: string
    port: number
    user: string
    from_email: string
  }
}
