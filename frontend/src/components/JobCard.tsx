import { useState } from 'react'
import { updateResume } from '../api'
import JobDetailModal from './JobDetailModal'

interface JobCardProps {
  title: string
  company: string
  city: string
  score: number
  source: string
  sourceUrl: string
  salary: string
  description: string
  requirements: string
  location: string
  postedDate: string
  jobId: number
  resumeId: number | null
}

export default function JobCard({ title, company, city, score, source, sourceUrl, salary, description, requirements, location, postedDate, jobId, resumeId }: JobCardProps) {
  const isRecommended = score >= 70
  const showScore = score >= 0
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showDetail, setShowDetail] = useState(false)

  const handleUpdateResume = async () => {
    if (!resumeId || loading) return
    setLoading(true)
    setError('')
    try {
      const blob = await updateResume(jobId, resumeId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `优化简历_${title}_${company}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setError('简历生成失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const descSnippet = description ? (description.length > 80 ? description.slice(0, 80) + '...' : description) : ''

  return (
    <div className="rounded-xl p-4 shadow-sm" style={{ backgroundColor: '#fff' }} role="article">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-semibold" style={{ color: '#1E88E5' }}>
            {title}
          </h3>
          <p className="text-sm" style={{ color: '#666' }}>
            {company} · {city}
          </p>
          {salary && (
            <p className="text-xs mt-0.5" style={{ color: '#999' }}>
              {salary}
            </p>
          )}
          {postedDate && (
            <p className="text-xs mt-0.5" style={{ color: '#999' }}>
              发布时间: {postedDate}
            </p>
          )}
          {descSnippet && (
            <p className="text-xs mt-1" style={{ color: '#999', maxWidth: '320px' }}>
              {descSnippet}
            </p>
          )}
        </div>
        <div className="text-right ml-3">
          {showScore && (
            <div className="flex items-center gap-1.5">
              <div className="w-16 h-1.5 rounded-full" style={{ backgroundColor: '#E0E0E0' }}>
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(score, 100)}%`,
                    backgroundColor: isRecommended ? '#4CAF50' : '#9E9E9E',
                  }}
                />
              </div>
              <span
                className={`text-xs font-medium ${isRecommended ? '' : ''}`}
                style={{ color: isRecommended ? '#4CAF50' : '#999' }}
                aria-label={`匹配度 ${score}%`}
              >
                {score}%
              </span>
            </div>
          )}
          <p className="text-xs mt-1" style={{ color: '#999' }}>
            来源: {sourceUrl ? (
              <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="underline" style={{ color: '#42A5F5' }}>
                {source}
              </a>
            ) : source}
          </p>
        </div>
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button
          className="px-3 py-1 rounded-lg text-xs font-medium transition-colors hover:opacity-80"
          style={{ borderColor: '#BBDEFB', color: '#42A5F5', border: '1px solid' }}
          onClick={() => setShowDetail(true)}
        >
          查看详情
        </button>
        <button
          className="px-3 py-1 rounded-lg text-xs font-medium text-white transition-colors disabled:opacity-50 hover:opacity-85"
          style={{ backgroundColor: '#42A5F5' }}
          onClick={handleUpdateResume}
          disabled={!resumeId || loading}
          aria-label={!resumeId ? '请先上传简历' : `为 ${title} 生成优化简历`}
        >
          {loading ? '生成中...' : '更新简历'}
        </button>
      </div>
      {error && (
        <p className="text-xs mt-2 text-right" style={{ color: '#e53935' }}>{error}</p>
      )}
      <JobDetailModal
        show={showDetail}
        onClose={() => setShowDetail(false)}
        title={title}
        company={company}
        city={city}
        salary={salary}
        location={location}
        source={source}
        sourceUrl={sourceUrl}
        description={description}
        requirements={requirements}
        postedDate={postedDate}
        jobId={jobId}
      />
    </div>
  )
}
