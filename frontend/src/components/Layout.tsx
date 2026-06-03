import { useState } from 'react'
import CitySwitcher from './CitySwitcher'
import LoginModal from './LoginModal'

interface LayoutProps {
  children: React.ReactNode
  selectedCities: string[]
  onCitiesChange: (cities: string[]) => void
}

export default function Layout({ children, selectedCities, onCitiesChange }: LayoutProps) {
  const [loginOpen, setLoginOpen] = useState(false)

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#F5F9FF' }}>
      <nav
        className="flex items-center justify-between px-4 md:px-6 h-14 shadow-sm"
        style={{ backgroundColor: '#E3F2FD' }}
      >
        <h1 className="text-lg font-semibold" style={{ color: '#1E88E5' }}>
          AI智能求职助手
        </h1>
        <div className="flex items-center gap-3">
          <button
            className="text-xs px-2 py-1 rounded transition-colors"
            style={{ borderColor: '#42A5F5', color: '#42A5F5', border: '1px solid' }}
            onClick={() => setLoginOpen(true)}
          >
            登录招聘网站
          </button>
          <CitySwitcher selectedCities={selectedCities} onCitiesChange={onCitiesChange} />
        </div>
      </nav>
      <main className="flex-1">{children}</main>
      <LoginModal show={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  )
}
