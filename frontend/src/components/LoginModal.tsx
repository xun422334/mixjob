interface LoginModalProps {
  show: boolean
  onClose: () => void
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

export default function LoginModal({ show, onClose }: LoginModalProps) {
  if (!show) return null

  const handleLogin = (source: string) => {
    const entry = LOGIN_URLS[source]
    if (entry) {
      window.open(entry.url, '_blank')
    }
  }

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

        <div className="flex flex-col gap-3">
          {Object.entries(LOGIN_URLS).map(([key, { label }]) => (
            <div
              key={key}
              className="flex items-center justify-between p-3 rounded-lg"
              style={{ backgroundColor: '#F5F9FF' }}
            >
              <span className="text-sm font-medium" style={{ color: '#333' }}>{label}</span>
              <button
                className="text-xs px-4 py-1.5 rounded text-white transition-colors hover:opacity-90"
                style={{ backgroundColor: '#42A5F5' }}
                onClick={() => handleLogin(key)}
              >
                去登录
              </button>
            </div>
          ))}
        </div>

        <p className="mt-3 text-xs" style={{ color: '#999' }}>
          点击按钮将在新标签页打开对应招聘网站的登录页面，登录完成后即可返回本页面。
        </p>
      </div>
    </div>
  )
}
