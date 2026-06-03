import { useState, useCallback, useEffect } from 'react'
import Layout from '../components/Layout'
import ResumeUpload from '../components/ResumeUpload'
import ChatDialog from '../components/ChatDialog'
import JobCard from '../components/JobCard'

import ScrapeBar from '../components/ScrapeBar'
import ErrorBoundary from '../components/ErrorBoundary'
import { getMatches, getJobs, getUserProfile, type MatchData, type JobData } from '../api'

interface ResumeData {
  id: number
  filename: string
  skills: string[]
  experience: { company: string; position: string; duration: string; description: string }[]
  projects: { name: string; role: string; duration: string; description: string; tech_stack: string[] }[]
  education: { school: string; degree: string; major: string; year: string }[]
  personal_info: { name: string; phone: string; email: string; awards: string[]; certs: string[] }
}

type TabType = 'matches' | 'all'

export default function HomePage() {
  const [selectedCities, setSelectedCities] = useState<string[]>(['北京'])
  const [scrapeKeyword, setScrapeKeyword] = useState('')
  const [resumeData, setResumeData] = useState<ResumeData | null>(null)
  const [matches, setMatches] = useState<MatchData[]>([])
  const [allJobs, setAllJobs] = useState<JobData[]>([])
  const [loadingMatches, setLoadingMatches] = useState(false)
  const [loadingAllJobs, setLoadingAllJobs] = useState(false)
  const [matchesError, setMatchesError] = useState('')
  const [allJobsError, setAllJobsError] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('matches')
  const [sourceFilter, setSourceFilter] = useState<string>('')

  // Load saved cities on mount
  useEffect(() => {
    getUserProfile().then((profile) => {
      if (profile.desired_cities?.length > 0) {
        setSelectedCities((prev) => {
          const merged = [...prev]
          for (const c of profile.desired_cities) {
            if (!merged.includes(c) && merged.length < 3) {
              merged.push(c)
            }
          }
          return merged.length > prev.length ? merged : prev
        })
      }
    }).catch(() => {})
  }, [])

  const fetchMatches = useCallback(async () => {
    if (!resumeData) return
    setLoadingMatches(true)
    setMatchesError('')
    try {
      const allMatches: MatchData[] = []
      for (const city of selectedCities) {
        const data = await getMatches(city, 0, resumeData.id, sourceFilter || undefined)
        allMatches.push(...data.matches)
      }
      allMatches.sort((a, b) => b.score - a.score)
      setMatches(allMatches)
    } catch {
      setMatchesError('加载匹配失败，请检查网络后重试')
    } finally {
      setLoadingMatches(false)
    }
  }, [selectedCities, resumeData, sourceFilter])

  const fetchAllJobs = useCallback(async () => {
    setLoadingAllJobs(true)
    setAllJobsError('')
    try {
      const all: JobData[] = []
      for (const city of selectedCities) {
        const data = await getJobs(city, undefined, sourceFilter || undefined)
        all.push(...data.jobs)
      }
      // dedup by id
      const seen = new Set<number>()
      const unique = all.filter((j) => !seen.has(j.id) && seen.add(j.id))
      unique.sort((a, b) => b.id - a.id)
      setAllJobs(unique)
    } catch {
      setAllJobsError('加载岗位失败，请检查网络后重试')
    } finally {
      setLoadingAllJobs(false)
    }
  }, [selectedCities, sourceFilter])

  useEffect(() => {
    fetchMatches()
  }, [fetchMatches])

  useEffect(() => {
    if (activeTab === 'all') {
      fetchAllJobs()
    }
  }, [activeTab, fetchAllJobs])

  const handleCitiesDetected = useCallback(
    (cities: string[]) => {
      setSelectedCities((prev) => {
        const merged = [...prev]
        for (const c of cities) {
          const idx = merged.indexOf(c)
          if (idx >= 0) merged.splice(idx, 1)
          merged.unshift(c)
        }
        return merged.slice(0, 3)
      })
    },
    []
  )

  const handlePositionDetected = useCallback(
    (position: string) => {
      setScrapeKeyword(position)
    },
    []
  )

  const handleJobAdded = () => {
    fetchMatches()
    fetchAllJobs()
    if (!resumeData) {
      setActiveTab('all')
    }
  }

  return (
    <Layout selectedCities={selectedCities} onCitiesChange={setSelectedCities}>
      <div className="flex flex-col lg:flex-row gap-4 p-4 max-w-7xl mx-auto">
        {/* 左侧面板 */}
        <div className="flex flex-col gap-4 lg:w-80 shrink-0">
          <ErrorBoundary>
            <ResumeUpload onUploaded={setResumeData} data={resumeData} />
          </ErrorBoundary>
          <ErrorBoundary>
            <ChatDialog
              resumeId={resumeData?.id ?? null}
              onCitiesDetected={handleCitiesDetected}
              onPositionDetected={handlePositionDetected}
            />
          </ErrorBoundary>
        </div>

        {/* 右侧主区域 */}
        <div className="flex-1">
          <ErrorBoundary>
            <ScrapeBar
              selectedCity={selectedCities[0] || '北京'}
              keyword={scrapeKeyword}
              onKeywordChange={setScrapeKeyword}
              onScraped={handleJobAdded}
              resumeId={resumeData?.id ?? null}
            />
          </ErrorBoundary>

          {/* Tab 切换 */}
          <div className="flex items-center gap-3 mb-3 mt-4">
            <h2 className="font-semibold" style={{ color: '#1E88E5' }}>
              {activeTab === 'matches' ? '推荐岗位列表' : '全部岗位'}
              {selectedCities.length > 0 && (
                <span className="text-sm font-normal ml-2" style={{ color: '#999' }}>
                  ({selectedCities.join('、')})
                </span>
              )}
            </h2>
            <div className="flex rounded overflow-hidden border" style={{ borderColor: '#BBDEFB' }}>
              <button
                className="text-xs px-3 py-1 transition-colors hover:opacity-85"
                style={{
                  backgroundColor: activeTab === 'matches' ? '#42A5F5' : '#fff',
                  color: activeTab === 'matches' ? '#fff' : '#42A5F5',
                }}
                onClick={() => setActiveTab('matches')}
              >
                推荐匹配
              </button>
              <button
                className="text-xs px-3 py-1 transition-colors hover:opacity-85"
                style={{
                  backgroundColor: activeTab === 'all' ? '#42A5F5' : '#fff',
                  color: activeTab === 'all' ? '#fff' : '#42A5F5',
                }}
                onClick={() => setActiveTab('all')}
              >
                全部岗位
              </button>
            </div>
            {resumeData && activeTab === 'matches' && (
              <button
                className="text-xs px-2 py-1 rounded transition-colors"
                style={{ borderColor: '#42A5F5', color: '#42A5F5', border: '1px solid' }}
                onClick={fetchMatches}
                disabled={loadingMatches}
              >
                {loadingMatches ? '匹配中...' : '刷新匹配'}
              </button>
            )}
            {activeTab === 'all' && (
              <button
                className="text-xs px-2 py-1 rounded transition-colors"
                style={{ borderColor: '#42A5F5', color: '#42A5F5', border: '1px solid' }}
                onClick={fetchAllJobs}
                disabled={loadingAllJobs}
              >
                {loadingAllJobs ? '加载中...' : '刷新'}
              </button>
            )}
          </div>

          {/* 平台筛选按钮 */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <span className="text-xs" style={{ color: '#999' }}>平台：</span>
            {['', 'boss', 'liepin', 'zhaopin', 'guopin'].map((s) => {
              const labels: Record<string, string> = {
                '': '全部', boss: 'BOSS直聘', liepin: '猎聘', zhaopin: '智联招聘', guopin: '国聘',
              }
              return (
                <button
                  key={s}
                  className="text-xs px-2.5 py-1 rounded-full transition-colors"
                  style={{
                    backgroundColor: sourceFilter === s ? '#42A5F5' : '#F5F9FF',
                    color: sourceFilter === s ? '#fff' : '#666',
                    border: sourceFilter === s ? 'none' : '1px solid #ddd',
                  }}
                  onClick={() => setSourceFilter(s)}
                >
                  {labels[s]}
                </button>
              )
            })}
          </div>

          <ErrorBoundary>
            {/* 推荐匹配 Tab */}
            {activeTab === 'matches' && (
              <div className="flex flex-col gap-3">
                {!resumeData ? (
                  <p className="text-sm" style={{ color: '#999' }}>
                    上传简历或与AI沟通后，AI将为你匹配推荐岗位
                  </p>
                ) : loadingMatches ? (
                  <p className="text-sm" style={{ color: '#999' }}>AI正在评估匹配度...</p>
                ) : matchesError ? (
                  <div className="rounded-lg p-4 text-center" style={{ backgroundColor: '#fff' }}>
                    <p className="text-sm" style={{ color: '#e53935' }}>{matchesError}</p>
                    <button
                      className="mt-2 text-xs px-3 py-1 rounded text-white"
                      style={{ backgroundColor: '#42A5F5' }}
                      onClick={fetchMatches}
                    >
                      重试
                    </button>
                  </div>
                ) : matches.length > 0 ? (
                  matches.map((m) => (
                    <JobCard
                      key={m.job.id}
                      title={m.job.title}
                      company={m.job.company}
                      city={m.job.city}
                      score={m.score}
                      source={m.job.source}
                      sourceUrl={m.job.source_url}
                      salary={m.job.salary}
                      description={m.job.description}
                      requirements={m.job.requirements}
                      location={m.job.location}
                      postedDate={m.job.posted_date}
                      jobId={m.job.id}
                      resumeId={resumeData?.id ?? null}
                    />
                  ))
                ) : resumeData ? (
                  <p className="text-sm" style={{ color: '#999' }}>
                    {selectedCities.length > 0
                      ? `当前城市（${selectedCities.join('、')}）暂无匹配岗位，请尝试切换其他城市或使用上方一键抓取获取岗位数据`
                      : '请选择城市后查看匹配岗位'}
                  </p>
                ) : (
                  <p className="text-sm" style={{ color: '#999' }}>
                    上传简历或与AI沟通后，AI将为你匹配推荐岗位
                  </p>
                )}
              </div>
            )}

            {/* 全部岗位 Tab */}
            {activeTab === 'all' && (
              <div className="flex flex-col gap-3">
                {loadingAllJobs ? (
                  <p className="text-sm" style={{ color: '#999' }}>加载中...</p>
                ) : allJobsError ? (
                  <div className="rounded-lg p-4 text-center" style={{ backgroundColor: '#fff' }}>
                    <p className="text-sm" style={{ color: '#e53935' }}>{allJobsError}</p>
                    <button
                      className="mt-2 text-xs px-3 py-1 rounded text-white"
                      style={{ backgroundColor: '#42A5F5' }}
                      onClick={fetchAllJobs}
                    >
                      重试
                    </button>
                  </div>
                ) : allJobs.length > 0 ? (
                  allJobs.map((job) => (
                    <JobCard
                      key={job.id}
                      title={job.title}
                      company={job.company}
                      city={job.city}
                      score={-1}
                      source={job.source}
                      sourceUrl={job.source_url}
                      salary={job.salary}
                      description={job.description}
                      requirements={job.requirements}
                      location={job.location}
                      postedDate={job.posted_date}
                      jobId={job.id}
                      resumeId={resumeData?.id ?? null}
                    />
                  ))
                ) : (
                  <p className="text-sm" style={{ color: '#999' }}>
                    {selectedCities.length > 0
                      ? `当前城市（${selectedCities.join('、')}）暂无岗位，可使用上方搜索栏抓取获取`
                      : '暂无岗位，可使用上方搜索栏抓取获取'}
                  </p>
                )}
              </div>
            )}
          </ErrorBoundary>
        </div>
      </div>
    </Layout>
  )
}
