import { useState, useEffect, useRef } from 'react'
import { getCities } from '../api'

interface City {
  name: string
  code: string
}

interface CitySwitcherProps {
  selectedCities: string[]
  onCitiesChange: (cities: string[]) => void
}

export default function CitySwitcher({ selectedCities, onCitiesChange }: CitySwitcherProps) {
  const [cities, setCities] = useState<City[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getCities()
      .then((data) => setCities(data.cities || []))
      .catch(() => setError('加载城市失败'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!open) return
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const toggleCity = (name: string) => {
    if (selectedCities.includes(name)) {
      onCitiesChange(selectedCities.filter((c) => c !== name))
    } else if (selectedCities.length < 3) {
      onCitiesChange([...selectedCities, name])
    }
  }

  const filteredCities = search.trim()
    ? cities.filter((c) => c.name.includes(search.trim()))
    : cities

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen(!open)}
        className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
        style={{ backgroundColor: '#42A5F5', color: '#fff' }}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        {selectedCities.length > 0 ? selectedCities.join(' / ') : '选择城市'} ▼
      </button>
      {open && (
        <div
          className="absolute right-0 top-full mt-1 rounded-lg shadow-lg p-3 z-50 min-w-48"
          style={{ backgroundColor: '#fff' }}
          role="listbox"
        >
          <p className="text-xs mb-2" style={{ color: '#999' }}>
            最多选3个城市
          </p>
          <input
            className="w-full px-2 py-1 rounded text-xs border mb-2 outline-none"
            style={{ borderColor: '#BBDEFB' }}
            placeholder="搜索城市..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="max-h-48 overflow-y-auto">
            {loading ? (
              <p className="text-xs" style={{ color: '#999' }}>加载中...</p>
            ) : error ? (
              <p className="text-xs" style={{ color: '#e53935' }}>{error}</p>
            ) : filteredCities.length === 0 ? (
              <p className="text-xs" style={{ color: '#999' }}>无匹配城市</p>
            ) : (
              filteredCities.map((city) => (
                <label key={city.code} className="flex items-center gap-2 py-1 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={selectedCities.includes(city.name)}
                    onChange={() => toggleCity(city.name)}
                    disabled={!selectedCities.includes(city.name) && selectedCities.length >= 3}
                  />
                  {city.name}
                </label>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
