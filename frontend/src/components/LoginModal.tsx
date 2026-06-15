import { useState, useEffect, useRef } from 'react'
import { getLoginStatus, getLoginStatusBySource } from '../api'

interface LoginStatus {
  source: string
  logged_in: boolean
  message: string
  hours_ago?: number
}

const LOGIN_URLS: Record<string, { label: string; url: string }> = {
  boss: {
    label: 'BOSS直聘',
    url: 'https://www.zhipin.com/web/user/?ka=header-login',
  },
  liepin: {
    label: '猎聘',
    url: 'https://www.liepin.com/login/',
  },
  zhaopin: {
    label: '智联招聘',
    url: 'https://passport.zhaopin.com/login',
  },
  guopin: {
    label: '国聘',
    url: 'https://www.iguopin.com/login',
  },
}

const ALL_SOURCES = ['boss', 'liepin', 'zhaopin', 'guopin']

interface LoginModalProps {
  show: boolean
  onClose: () => void
}

export default function LoginModal({ show, onClose }: LoginModalProps) {
  const [statuses, setStatuses] = useState<Record<string, LoginStatus>>({})
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const data = await getLoginStatus()
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
    setMessage('')
    // Open login page in new tab for user
    const entry = LOGIN_URLS[source]
    if (entry) {
      window.open(entry.url, '_blank')
    }

    // Also try backend Playwright auto-login (works in local dev)
    try {
      const resp = await fetch(`/api/auth/login/${source}`, { method: 'POST' })
      if (resp.ok) {
        const data = await resp.json()
        setMessage(data.message)
      }
    } catch {
      // Backend not available, just rely on new tab
    }

    // Poll for status change
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const sd = await getLoginStatusBySource(source)
        setStatuses((prev) => ({ ...prev, [source]: sd }))
        if (sd.logged_in) {
          if (pollRef.current) {
            clearInterval(pollRef.current)
            pollRef.current = null
          }
          setMessage(`${LOGIN_URLS[source]?.label || source} 登录成功！`)
        }
      } catch {
        // continue polling
      }
    }, 3000)
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
              const label = LOGIN_URLS[key]?.label || key
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
                      <p className="text-sm font-medium" style={{ color: '#333' }}>{label}</p>
                      <p className="text-xs" style={{ color: loggedIn ? '#4CAF50' : '#999' }}>
                        {status?.message || '未登录'}
                      </p>
                    </div>
                  </div>
                  <button
                    className="text-xs px-4 py-1.5 rounded text-white transition-colors hover:opacity-90"
                    style={{ backgroundColor: loggedIn ? '#81C784' : '#42A5F5' }}
                    onClick={() => handleLogin(key)}
                  >
                    {loggedIn ? '重新登录' : '去登录'}
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
          点击按钮跳转登录页面，完成登录后系统会自动检测状态（约需等待几秒）。
        </p>
      </div>
    </div>
  )
}
