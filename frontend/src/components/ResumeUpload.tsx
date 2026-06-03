import { useState, useRef } from 'react'
import { uploadResume } from '../api'

interface ResumeData {
  id: number
  filename: string
  skills: string[]
  experience: { company: string; position: string; duration: string; description: string }[]
  projects: { name: string; role: string; duration: string; description: string; tech_stack: string[] }[]
  education: { school: string; degree: string; major: string; year: string }[]
  personal_info: { name: string; phone: string; email: string; awards: string[]; certs: string[] }
}

interface ResumeUploadProps {
  onUploaded: (data: ResumeData) => void
  data: ResumeData | null
}

export default function ResumeUpload({ onUploaded, data }: ResumeUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const inputRef = useRef<HTMLInputElement>(null)

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf') && !file.name.toLowerCase().endsWith('.docx') && !file.name.toLowerCase().endsWith('.doc')) {
      setError('仅支持 PDF / Word 格式')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('文件不能超过10MB')
      return
    }
    setError('')
    setUploading(true)
    try {
      const result = await uploadResume(file)
      onUploaded(result)
    } catch {
      setError('上传失败，请重试')
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  if (data) {
    const hasPersonalInfo = data.personal_info && (data.personal_info.name || data.personal_info.phone || data.personal_info.email)
    const hasAwards = data.personal_info?.awards?.length > 0
    const hasCerts = data.personal_info?.certs?.length > 0

    return (
      <div className="rounded-lg p-4 max-h-[60vh] overflow-y-auto" style={{ backgroundColor: '#fff' }}>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-medium" style={{ color: '#1E88E5' }}>
            简历解析结果
          </p>
          <button
            className="text-xs underline"
            style={{ color: '#999' }}
            onClick={() => onUploaded(null as unknown as ResumeData)}
          >
            重新上传
          </button>
        </div>

        <div className="text-xs space-y-2">
          {/* 个人信息 */}
          {hasPersonalInfo && (
            <div
              className="rounded p-2 cursor-pointer"
              style={{ backgroundColor: '#F5F9FF' }}
              onClick={() => toggleSection('personal')}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium" style={{ color: '#1E88E5' }}>个人信息</span>
                <span style={{ color: '#999', fontSize: '10px' }}>{expandedSections['personal'] ? '收起' : '展开'}</span>
              </div>
              <div className="mt-1" style={{ color: '#333' }}>
                {[data.personal_info.name, data.personal_info.phone, data.personal_info.email].filter(Boolean).join(' · ') || '未识别'}
              </div>
              {expandedSections['personal'] && (
                <div className="mt-2 space-y-1">
                  {data.personal_info.name && <p><span style={{ color: '#666' }}>姓名：</span>{data.personal_info.name}</p>}
                  {data.personal_info.phone && <p><span style={{ color: '#666' }}>电话：</span>{data.personal_info.phone}</p>}
                  {data.personal_info.email && <p><span style={{ color: '#666' }}>邮箱：</span>{data.personal_info.email}</p>}
                  {hasAwards && <p><span style={{ color: '#666' }}>获奖：</span>{data.personal_info.awards.join('、')}</p>}
                  {hasCerts && <p><span style={{ color: '#666' }}>证书：</span>{data.personal_info.certs.join('、')}</p>}
                </div>
              )}
            </div>
          )}

          {/* 技能 */}
          <div
            className="rounded p-2 cursor-pointer"
            style={{ backgroundColor: '#F5F9FF' }}
            onClick={() => toggleSection('skills')}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium" style={{ color: '#1E88E5' }}>技能清单</span>
              <span style={{ color: '#999', fontSize: '10px' }}>{expandedSections['skills'] ? '收起' : '展开'}</span>
            </div>
            <div className="mt-1" style={{ color: '#333' }}>
              {(data.skills || []).join('、') || '未识别'}
            </div>
          </div>

          {/* 工作经历 */}
          <div
            className="rounded p-2 cursor-pointer"
            style={{ backgroundColor: '#F5F9FF' }}
            onClick={() => toggleSection('work')}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium" style={{ color: '#1E88E5' }}>
                工作经历 ({(data.experience || []).length})
              </span>
              <span style={{ color: '#999', fontSize: '10px' }}>{expandedSections['work'] ? '收起' : '展开'}</span>
            </div>
            {(data.experience || []).length > 0 ? (
              <div className="mt-1" style={{ color: '#333' }}>
                {data.experience.map((exp, i) => (
                  <div key={i} className="mb-2 border-b border-dashed pb-1" style={{ borderColor: '#E0E0E0' }}>
                    <p className="font-medium">{exp.position} @ {exp.company}</p>
                    <p style={{ color: '#999' }}>{exp.duration}</p>
                    {expandedSections['work'] && exp.description && (
                      <p className="mt-1" style={{ color: '#555' }}>{exp.description}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-1" style={{ color: '#999' }}>未识别</p>
            )}
          </div>

          {/* 项目经历 */}
          <div
            className="rounded p-2 cursor-pointer"
            style={{ backgroundColor: '#F5F9FF' }}
            onClick={() => toggleSection('projects')}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium" style={{ color: '#1E88E5' }}>
                项目经历 ({(data.projects || []).length})
              </span>
              <span style={{ color: '#999', fontSize: '10px' }}>{expandedSections['projects'] ? '收起' : '展开'}</span>
            </div>
            {(data.projects || []).length > 0 ? (
              <div className="mt-1" style={{ color: '#333' }}>
                {data.projects.map((proj, i) => (
                  <div key={i} className="mb-2 border-b border-dashed pb-1" style={{ borderColor: '#E0E0E0' }}>
                    <p className="font-medium">{proj.name}</p>
                    <p style={{ color: '#999' }}>{proj.role} · {proj.duration}</p>
                    {expandedSections['projects'] && (
                      <>
                        {proj.description && <p className="mt-1" style={{ color: '#555' }}>{proj.description}</p>}
                        {proj.tech_stack?.length > 0 && (
                          <p className="mt-1" style={{ color: '#42A5F5' }}>技术栈：{proj.tech_stack.join('、')}</p>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-1" style={{ color: '#999' }}>未识别</p>
            )}
          </div>

          {/* 教育背景 */}
          <div
            className="rounded p-2 cursor-pointer"
            style={{ backgroundColor: '#F5F9FF' }}
            onClick={() => toggleSection('edu')}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium" style={{ color: '#1E88E5' }}>教育背景</span>
              <span style={{ color: '#999', fontSize: '10px' }}>{expandedSections['edu'] ? '收起' : '展开'}</span>
            </div>
            {(data.education || []).length > 0 ? (
              <div className="mt-1" style={{ color: '#333' }}>
                {data.education.map((edu, i) => (
                  <div key={i} className="mb-1">
                    <p className="font-medium">{edu.school}</p>
                    <p style={{ color: '#999' }}>{edu.major} · {edu.degree}{edu.year ? ` · ${edu.year}` : ''}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-1" style={{ color: '#999' }}>未识别</p>
            )}
          </div>

          {/* 获奖与证书快捷展示 */}
          {(hasAwards || hasCerts) && (
            <div className="rounded p-2" style={{ backgroundColor: '#F5F9FF' }}>
              <span className="font-medium" style={{ color: '#1E88E5' }}>获奖与证书</span>
              <div className="mt-1" style={{ color: '#333' }}>
                {hasAwards && <p>获奖：{data.personal_info.awards.join('、')}</p>}
                {hasCerts && <p>证书：{data.personal_info.certs.join('、')}</p>}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          dragOver ? 'opacity-70' : ''
        }`}
        style={{
          borderColor: error ? '#ef4444' : '#42A5F5',
          backgroundColor: dragOver ? '#E3F2FD' : '#fff',
        }}
        role="button"
        tabIndex={0}
        aria-label="上传简历文件"
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputRef.current?.click() } }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? (
          <div>
            <p className="font-medium" style={{ color: '#1E88E5' }}>解析中...</p>
            <p className="text-xs mt-1" style={{ color: '#999' }}>AI正在分析你的简历</p>
          </div>
        ) : (
          <div>
            <p className="font-medium" style={{ color: '#1E88E5' }}>上传简历</p>
            <p className="text-xs mt-1" style={{ color: '#999' }}>
              支持 PDF / Word 格式，拖拽或点击上传
            </p>
          </div>
        )}
      </div>
      {error && <p className="text-xs mt-1 text-red-500">{error}</p>}
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.doc,.docx"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFile(file)
        }}
      />
    </div>
  )
}
