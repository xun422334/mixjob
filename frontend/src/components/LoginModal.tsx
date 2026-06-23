import { useState, useEffect, useRef } from 'react'
import { getLoginStatus, startProxyLogin, checkProxyLoginStatus, refreshProxyLogin, cancelProxyLogin } from '../api'

interface LoginStatus {
  source: string
  logged_in: boolean
  message: string
  hours_ago?: number
}

const LOGIN_URLS: Record<string, { label: string; url: string }> = {
  boss: { label: 'BOSS直聘', url: 'https://www.zhipin.com/web/user/?ka=header-login' },
  liepin: { label: '猎聘', url: 'https://www.liepin.com/login/' },
  zhaopin: { label: '智联招聘', url: 'https://passport.zhaopin.com/login' },
  guopin: { label: '国聘', url: 'https://www.iguopin.com/login' },
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

  // QR code view state
  const [qrSource, setQrSource] = useState<string | null>(null)
  const [qrImage, setQrImage] = useState<string | null>(null)
  const [qrWaiting, setQrWaiting] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const data = await getLoginStatus()
      setStatuses(data.sources || {})
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        setMessage('请求超时，请检查网络后重试')
      } else {
        setMessage('获取登录状态失败')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (show) {
      fetchStatus()
      setQrSource(null)
      setQrImage(null)
    } else {
      cleanupPoll()
    }
    return () => cleanupPoll()
  }, [show])

  const cleanupPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const handleStartLogin = async (source: string) => {
    setMessage('')
    cleanupPoll()

    try {
      const data = await startProxyLogin(source)
      setQrSource(source)
      setQrImage(data.screenshot)
      setQrWaiting(true)

      // Poll for login detection
      pollRef.current = setInterval(async () => {
        try {
          const status = await checkProxyLoginStatus(source)
          if (status.logged_in) {
            cleanupPoll()
            setQrWaiting(false)
            setQrImage(null)
            setMessage(`${LOGIN_URLS[source]?.label || source} 登录成功！`)
            fetchStatus()
            // Auto close QR view after success
            setTimeout(() => setQrSource(null), 1500)
          } else if (!status.active) {
            cleanupPoll()
            setQrWaiting(false)
            setQrImage(null)
            setMessage(status.message || '登录超时，请重试')
            setQrSource(null)
          }
          // Still waiting - update screenshot if available
          if (status.screenshot) {
            setQrImage(status.screenshot)
          }
        } catch {
          // keep polling
        }
      }, 3000)
    } catch (e: any) {
      setMessage(e?.message || '启动登录失败，请重试')
    }
  }

  const handleRefresh = async () => {
    if (!qrSource) return
    try {
      const data = await refreshProxyLogin(qrSource)
      setQrImage(data.screenshot)
      setMessage('二维码已刷新')
    } catch {
      setMessage('刷新失败')
    }
  }

  const handleCancel = async () => {
    cleanupPoll()
    if (qrSource) {
      try { await cancelProxyLogin(qrSource) } catch {}
    }
    setQrSource(null)
    setQrImage(null)
    setQrWaiting(false)
    setMessage('')
  }

  if (!show) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="rounded-xl p-6 w-96 max-w-[90vw] shadow-lg max-h-[85vh] overflow-y-auto"
        style={{ backgroundColor: '#fff' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold" style={{ color: '#1E88E5' }}>
            {qrSource ? `${LOGIN_URLS[qrSource]?.label} 扫码登录` : '登录招聘网站'}
          </h3>
          <button className="text-sm px-1" style={{ color: '#999' }} onClick={onClose}>✕</button>
        </div>

        {qrSource ? (
          /* QR Code View */
          <div className="flex flex-col items-center gap-3">
            {qrImage ? (
              <img
                src={qrImage}
                alt="QR code"
                className="w-64 h-auto rounded-lg border"
                style={{ borderColor: '#eee' }}
              />
            ) : (
              <div className="w-64 h-64 flex items-center justify-center rounded-lg" style={{ backgroundColor: '#f5f5f5' }}>
                <span style={{ color: '#999' }}>加载中...</span>
              </div>
            )}

            {qrWaiting && (
              <p className="text-sm" style={{ color: '#42A5F5' }}>
                请使用手机扫码登录...
              </p>
            )}

            <div className="flex gap-2">
              <button
                className="text-xs px-4 py-1.5 rounded text-white transition-colors hover:opacity-90"
                style={{ backgroundColor: '#42A5F5' }}
                onClick={handleRefresh}
              >
                刷新二维码
              </button>
              <button
                className="text-xs px-4 py-1.5 rounded transition-colors hover:opacity-90"
                style={{ backgroundColor: '#f5f5f5', color: '#666' }}
                onClick={handleCancel}
              >
                返回
              </button>
            </div>

            <p className="text-xs" style={{ color: '#999' }}>
              截图中的二维码来自服务器端浏览器，用手机微信/支付宝扫码即可完成登录，登录状态会自动同步到服务器。
            </p>
          </div>
        ) : (
          /* Platform List View */
          <>
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
                        onClick={() => handleStartLogin(key)}
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
              点击登录后，系统会打开服务器端浏览器并显示二维码，用手机扫码即可完成登录。
            </p>
          </>
        )}
      </div>
    </div>
  )
}
