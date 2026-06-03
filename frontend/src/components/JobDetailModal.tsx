import { useState, useEffect } from 'react'
import { fetchJobDetail } from '../api'

const PLATFORM_SEARCH_URLS: Record<string, string> = {
  boss: 'https://www.zhipin.com/web/geek/job?query=',
  BOSS直聘: 'https://www.zhipin.com/web/geek/job?query=',
  liepin: 'https://www.liepin.com/zhaopin/?key=',
  猎聘: 'https://www.liepin.com/zhaopin/?key=',
  zhaopin: 'https://sou.zhaopin.com/?kw=',
  智联招聘: 'https://sou.zhaopin.com/?kw=',
  guopin: 'https://www.iguopin.com/job?keyword=',
  国聘: 'https://www.iguopin.com/job?keyword=',
}

const SOURCE_LABELS: Record<string, string> = {
  boss: 'BOSS直聘',
  BOSS直聘: 'BOSS直聘',
  liepin: '猎聘',
  猎聘: '猎聘',
  zhaopin: '智联招聘',
  智联招聘: '智联招聘',
  guopin: '国聘',
  国聘: '国聘',
  manual: '手动添加',
}

interface JobDetailModalProps {
  show: boolean
  onClose: () => void
  title: string
  company: string
  city: string
  salary: string
  location: string
  source: string
  sourceUrl: string
  description: string
  requirements: string
  postedDate: string
  jobId: number
}

export default function JobDetailModal({
  show, onClose, title, company, city, salary, location,
  source, sourceUrl, description, requirements, postedDate, jobId,
}: JobDetailModalProps) {
  const [fetching, setFetching] = useState(false)
  const [fetchedDesc, setFetchedDesc] = useState('')
  const [fetchedReq, setFetchedReq] = useState('')
  const [fetchError, setFetchError] = useState('')

  useEffect(() => {
    if (show && jobId && source !== 'manual' && (!description || !requirements)) {
      setFetching(true)
      setFetchError('')
      fetchJobDetail(jobId)
        .then((data) => {
          setFetchedDesc(data.job.description || '')
          setFetchedReq(data.job.requirements || '')
        })
        .catch(() => {
          setFetchError('抓取失败，请稍后重试')
        })
        .finally(() => setFetching(false))
    }
  }, [show, jobId])

  if (!show) return null

  const displayDesc = fetchedDesc || description
  const displayReq = fetchedReq || requirements

  const handleApply = () => {
    if (sourceUrl) {
      window.open(sourceUrl, '_blank', 'noopener,noreferrer')
    } else if (source && source !== 'manual' && PLATFORM_SEARCH_URLS[source]) {
      const query = encodeURIComponent(`${title} ${company}`)
      window.open(`${PLATFORM_SEARCH_URLS[source]}${query}`, '_blank', 'noopener,noreferrer')
    }
  }

  const hasUrl = !!(sourceUrl || (source && source !== 'manual' && PLATFORM_SEARCH_URLS[source]))

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="rounded-xl p-6 w-full max-w-lg max-h-[85vh] overflow-y-auto shadow-lg mx-4"
        style={{ backgroundColor: '#fff' }}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold" style={{ color: '#1E88E5' }}>{title}</h2>
            <p className="text-sm mt-1" style={{ color: '#666' }}>{company} · {city}</p>
          </div>
          <button
            className="text-lg px-1"
            style={{ color: '#999' }}
            onClick={onClose}
          >
            x
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mb-4">
          {salary && (
            <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#FFF3E0', color: '#E65100' }}>
              {salary}
            </span>
          )}
          {location && (
            <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#E8F5E9', color: '#2E7D32' }}>
              {location}
            </span>
          )}
          <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#F5F9FF', color: '#42A5F5' }}>
            {SOURCE_LABELS[source] || source || '未知来源'}
          </span>
          {postedDate && (
            <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#F3E5F5', color: '#7B1FA2' }}>
              {postedDate}
            </span>
          )}
        </div>

        <div className="mb-3">
          <p className="text-xs font-medium mb-1" style={{ color: '#333' }}>岗位描述</p>
          {fetching ? (
            <p className="text-sm" style={{ color: '#42A5F5' }}>正在从{source}抓取详情...</p>
          ) : fetchError ? (
            <p className="text-sm" style={{ color: '#c62828' }}>{fetchError}</p>
          ) : displayDesc ? (
            <p className="text-sm leading-relaxed" style={{ color: '#555', whiteSpace: 'pre-wrap' }}>{displayDesc}</p>
          ) : (
            <p className="text-sm" style={{ color: '#bbb' }}>暂无详细描述</p>
          )}
        </div>

        <div className="mb-4">
          <p className="text-xs font-medium mb-1" style={{ color: '#333' }}>任职要求</p>
          {fetching ? (
            <p className="text-sm" style={{ color: '#42A5F5' }}>...</p>
          ) : fetchError ? (
            <p className="text-sm" style={{ color: '#c62828' }}>{fetchError}</p>
          ) : displayReq ? (
            <p className="text-sm leading-relaxed" style={{ color: '#555', whiteSpace: 'pre-wrap' }}>{displayReq}</p>
          ) : (
            <p className="text-sm" style={{ color: '#bbb' }}>暂无任职要求</p>
          )}
        </div>

        <div className="flex gap-2">
          {hasUrl && (
            <button
              className="flex-1 py-2 rounded-lg text-sm font-medium text-white transition-colors hover:opacity-85"
              style={{ backgroundColor: '#42A5F5' }}
              onClick={handleApply}
            >
              去投递
            </button>
          )}
          <button
            className="flex-1 py-2 rounded-lg text-sm font-medium transition-colors hover:opacity-80"
            style={{ borderColor: '#BBDEFB', color: '#42A5F5', border: '1px solid' }}
            onClick={onClose}
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}
