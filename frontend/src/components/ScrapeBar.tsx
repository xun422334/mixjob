import { useState, useEffect } from 'react'
import { scrapeJobs, fetchResumeKeywords, fetchChatKeywords, type ScrapeResult } from '../api'

interface ScrapeBarProps {
  selectedCity: string
  keyword: string
  onKeywordChange: (keyword: string) => void
  onScraped: () => void
  resumeId: number | null
}

const SOURCE_NAMES: Record<string, string> = {
  boss: 'BOSS直聘',
  liepin: '猎聘',
  zhaopin: '智联招聘',
  guopin: '国聘',
}

const ALL_SOURCES = ['boss', 'liepin', 'zhaopin', 'guopin'] as const

export default function ScrapeBar({ selectedCity, keyword, onKeywordChange, onScraped, resumeId }: ScrapeBarProps) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScrapeResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showSuggest, setShowSuggest] = useState(false)

  // Auto-fill keywords when a resume is uploaded
  useEffect(() => {
    if (resumeId == null) return
    fetchResumeKeywords()
      .then((data) => {
        if (data.keywords) {
          onKeywordChange(data.keywords)
        }
      })
      .catch(() => {})
  }, [resumeId])

  // Show smart suggest button when input is empty
  useEffect(() => {
    setShowSuggest(!keyword.trim())
  }, [keyword])

  const handleScrape = async () => {
    if (!keyword.trim() || loading) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const data = await scrapeJobs(selectedCity, keyword.trim())
      setResult(data)
      onScraped()
    } catch {
      setError('抓取失败，请检查网络后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleSmartSuggest = async () => {
    try {
      // Try resume keywords first, fall back to chat keywords
      let data: { keywords: string } | null = await fetchResumeKeywords()
      if (!data.keywords) {
        data = await fetchChatKeywords()
      }
      if (data.keywords) {
        onKeywordChange(data.keywords)
        setShowSuggest(false)
      }
    } catch {
      // silent
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleScrape()
  }

  return (
    <div className="rounded-lg p-3" style={{ backgroundColor: '#fff' }}>
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <input
            className="w-full px-3 py-1.5 rounded-lg text-sm outline-none border"
            style={{ borderColor: '#BBDEFB' }}
            placeholder={`在${selectedCity}搜索岗位（多关键词用 / 分隔，如 Java/Python/产品经理）`}
            value={keyword}
            onChange={(e) => onKeywordChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          {showSuggest && (
            <button
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs px-2 py-0.5 rounded transition-colors"
              style={{ backgroundColor: '#E3F2FD', color: '#1E88E5' }}
              onClick={handleSmartSuggest}
              title="根据简历技能智能推荐关键词"
            >
              智能推荐
            </button>
          )}
        </div>
        <button
          className="px-4 py-1.5 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50 whitespace-nowrap hover:opacity-85"
          style={{ backgroundColor: '#42A5F5' }}
          onClick={handleScrape}
          disabled={loading || !keyword.trim()}
        >
          {loading ? '抓取中...' : '一键抓取'}
        </button>
      </div>

      {error && (
        <p className="mt-2 text-xs" style={{ color: '#e53935' }}>{error}</p>
      )}

      {result && (
        <div className="mt-2" aria-live="polite">
          <p className="text-xs font-medium" style={{ color: '#2e7d32' }}>
            新增 {result.new_added} 个岗位
            {result.duplicates_skipped > 0 && (
              <span style={{ color: '#999', marginLeft: 8 }}>
                跳过 {result.duplicates_skipped} 个重复
              </span>
            )}
          </p>
          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
            {ALL_SOURCES.map((key) => {
              const src = result.per_source[key]
              return (
                <span key={key} className="inline-flex items-center gap-1 text-xs">
                  <span style={{ color: '#888' }}>{SOURCE_NAMES[key] || key}</span>
                  {src ? (
                    src.status === 'ok' ? (
                      <span style={{ color: '#2e7d32', fontWeight: 500 }}>{src.count}个</span>
                    ) : (
                      <span style={{ color: '#c62828' }}>{src.error || '失败'}</span>
                    )
                  ) : (
                    <span style={{ color: '#bbb' }}>未抓取</span>
                  )}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {!result && !error && (
        <p className="mt-2 text-xs" style={{ color: '#999' }}>
          输入关键词，从BOSS直聘、猎聘、智联招聘、国聘等平台抓取岗位
        </p>
      )}
    </div>
  )
}
