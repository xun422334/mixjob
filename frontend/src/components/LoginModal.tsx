import { useState, useEffect, useRef } from 'react'

interface LoginStatus {
  source: string
  logged_in: boolean
  message: string
  hours_ago?: number
}

const SOURCE_LABELS: Record<string, string> = {
  boss: 'BOSS直聘',
  liepin: '猎聘',
  zhaopin: '智联招聘',
  guopin: '国聘',
}

const ALL_SOURCES = ['boss', 'liepin', 'zhaopin', 'guopin']

interface LoginModalProps {
  show: boolean
  onClose: () => void
}

export default function LoginModal({ show, onClose }: LoginModalProps) {
  const [statuses, setStatuses] = useState<Record<string, LoginStatus>>({})
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/auth/login/status')
      const data = await resp.json()
      setStatuses(data.sources || {})
    } catch {
      setMessage('获取登录状态失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (show) {
      fetchStatus()
    } else {
      // Stop polling when modal closes
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [show])

  const handleLogin = async (source: string) => {
    setActionLoading(source)
    setMessage('')
    try {
      const resp = await fetch(`/api/auth/login/${source}`, { method: 'POST' })
      const data = await resp.json()
      setMessage(data.message)

      // Start polling for login status every 3 seconds
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        try {
          const sr = await fetch(`/api/auth/login/status/${source}`)
          const sd = await sr.json()
          setStatuses((prev) => ({ ...prev, [source]: sd }))
          if (sd.logged_in) {
            if (pollRef.current) {
              clearInterval(pollRef.current)
              pollRef.current = null
            }
            setMessage(`${SOURCE_LABELS[source] || source} 登录成功！`)
            setActionLoading(null)
          }
        } catch {
          // continue polling
        }
      }, 3000)
    } catch {
      setMessage('启动登录失败，请重试')
      setActionLoading(null)
    }
  }

  if (!show) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="rounded-xl p-6 w-96 max-w-[90vw] shadow-lg max-h-[80vh] overflow-y-auto"
        style={{ backgroundColor: '#fff' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold" style={{ color: '#1E88E5' }}>登录招聘网站</h3>
          <button
            className="text-sm px-1"
            style={{ color: '#999' }}
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {loading ? (
          <p className="text-xs text-center" style={{ color: '#999' }}>加载中...</p>
        ) : (
          <div className="flex flex-col gap-3">
            {ALL_SOURCES.map((key) => {
              const status = statuses[key]
              const loggedIn = status?.logged_in || false
              return (
                <div
                  key={key}
                  className="flex items-center justify-between p-3 rounded-lg"
                  style={{ backgroundColor: '#F5F9FF' }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: loggedIn ? '#4CAF50' : '#ccc' }}
                    />
                    <div>
                      <p className="text-sm font-medium" style={{ color: '#333' }}>
                        {SOURCE_LABELS[key] || key}
                      </p>
                      <p className="text-xs" style={{ color: loggedIn ? '#4CAF50' : '#999' }}>
                        {status?.message || '未登录'}
                      </p>
                    </div>
                  </div>
                  <button
                    className="text-xs px-3 py-1 rounded text-white transition-colors disabled:opacity-50"
                    style={{ backgroundColor: loggedIn ? '#81C784' : '#42A5F5' }}
                    onClick={() => handleLogin(key)}
                    disabled={actionLoading === key}
                  >
                    {actionLoading === key ? '等待登录...' : loggedIn ? '重新登录' : '登录'}
                  </button>
                </div>
              )
            })}
          </div>
        )}

        {message && (
          <p className="mt-3 text-xs text-center" style={{ color: '#1E88E5' }}>{message}</p>
        )}

        <p className="mt-3 text-xs" style={{ color: '#999' }}>
          点击登录后，系统将打开浏览器窗口，请在浏览器中完成扫码或账号登录。登录成功后浏览器会自动关闭。
        </p>
      </div>
    </div>
  )
}
