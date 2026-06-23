const BASE = import.meta.env.DEV ? '/api' : 'https://api.mixjob.cn/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 15000)
  try {
    const resp = await fetch(`${BASE}${url}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options,
    })
    if (!resp.ok) throw new Error(`API error: ${resp.status}`)
    return resp.json()
  } finally {
    clearTimeout(timeout)
  }
}

export async function uploadResume(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await fetch(`${BASE}/resume/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`)
  return resp.json() as Promise<{
    id: number
    filename: string
    skills: string[]
    experience: { company: string; position: string; duration: string; description: string }[]
    projects: { name: string; role: string; duration: string; description: string; tech_stack: string[] }[]
    education: { school: string; degree: string; major: string; year: string }[]
    personal_info: { name: string; phone: string; email: string; awards: string[]; certs: string[] }
  }>
}

export async function sendMessage(message: string, resumeId: number | null) {
  return request<{ response: string; detected_cities: string[]; detected_position: string }>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, resume_id: resumeId }),
  })
}

export async function getCities() {
  return request<{ cities: { name: string; code: string }[] }>('/cities')
}

export interface JobData {
  id: number
  title: string
  company: string
  description: string
  requirements: string
  source: string
  source_url: string
  salary: string
  city: string
  location: string
  posted_date: string
}

export async function createJob(job: Omit<JobData, 'id'>) {
  return request<{ job: JobData }>('/jobs', {
    method: 'POST',
    body: JSON.stringify(job),
  })
}

export async function getJobs(city?: string, keyword?: string, source?: string) {
  const params = new URLSearchParams()
  if (city) params.set('city', city)
  if (keyword) params.set('keyword', keyword)
  if (source) params.set('source', source)
  return request<{ jobs: JobData[] }>(`/jobs?${params.toString()}`)
}

export interface MatchData {
  job: JobData
  score: number
  resume_id: number
}

export async function getMatches(city?: string, minScore?: number, resumeId?: number, source?: string) {
  const params = new URLSearchParams()
  if (city) params.set('city', city)
  if (minScore !== undefined) params.set('min_score', String(minScore))
  if (resumeId !== undefined) params.set('resume_id', String(resumeId))
  if (source) params.set('source', source)
  return request<{ matches: MatchData[]; total_jobs: number; matched: number }>(`/match?${params.toString()}`)
}

export interface ScrapeResult {
  city: string
  keyword: string
  total_found: number
  after_dedup: number
  new_added: number
  duplicates_skipped: number
  per_source: Record<string, {
    status: "ok" | "error" | "skipped"
    count: number
    error?: string
  }>
}

export async function scrapeJobs(city: string, keyword: string, sources?: string[]) {
  return request<ScrapeResult>('/jobs/scrape', {
    method: 'POST',
    body: JSON.stringify({ city, keyword, sources }),
  })
}

export async function updateResume(jobId: number, resumeId: number) {
  const resp = await fetch(`${BASE}/resume/update/${jobId}?resume_id=${resumeId}`, {
    method: 'POST',
  })
  if (!resp.ok) throw new Error(`Update resume failed: ${resp.status}`)
  return resp.blob()
}

export async function fetchJobDetail(jobId: number) {
  return request<{ job: JobData }>(`/jobs/${jobId}/fetch-detail`, { method: 'POST' })
}

export async function getUserProfile() {
  return request<{ desired_cities: string[]; desired_position: string; desired_salary: string }>('/chat/profile')
}

export async function fetchChatKeywords() {
  return request<{ keywords: string }>('/chat/keywords')
}

export async function healthCheck() {
  return request<{ status: string }>('/health')
}

export async function fetchResumeKeywords() {
  return request<{ keywords: string; skills: string[]; positions: string[] }>('/resume/keywords')
}

export async function getLoginStatus() {
  return request<{ sources: Record<string, { source: string; logged_in: boolean; message: string; hours_ago?: number }> }>('/auth/login/status')
}

export async function getLoginStatusBySource(source: string) {
  return request<{ source: string; logged_in: boolean; message: string; hours_ago?: number }>(`/auth/login/status/${source}`)
}

export async function startProxyLogin(source: string) {
  return request<{ status: string; source: string; screenshot: string; session_status: string }>(`/auth/login/proxy/${source}`, { method: 'POST' })
}

export async function checkProxyLoginStatus(source: string) {
  return request<{ logged_in: boolean; active: boolean; screenshot?: string; message: string }>(`/auth/login/proxy/${source}/status`)
}

export async function refreshProxyLogin(source: string) {
  return request<{ status: string; screenshot: string }>(`/auth/login/proxy/${source}/refresh`, { method: 'POST' })
}

export async function cancelProxyLogin(source: string) {
  return request<{ status: string }>(`/auth/login/proxy/${source}/cancel`, { method: 'POST' })
}

