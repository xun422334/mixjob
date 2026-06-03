import { useState, useRef, useEffect } from 'react'
import { sendMessage } from '../api'

interface Message {
  role: 'user' | 'ai'
  content: string
}

interface ChatDialogProps {
  resumeId: number | null
  onCitiesDetected: (cities: string[]) => void
  onPositionDetected: (position: string) => void
}

export default function ChatDialog({ resumeId, onCitiesDetected, onPositionDetected }: ChatDialogProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [detectedCitiesMsg, setDetectedCitiesMsg] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const cityMsgTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const data = await sendMessage(input, resumeId)
      setMessages((prev) => [...prev, { role: 'ai', content: data.response }])
      if (data.detected_cities?.length > 0) {
        onCitiesDetected(data.detected_cities)
        const msg = `已识别意向城市：${data.detected_cities.join('、')}`
        setDetectedCitiesMsg(msg)
        if (cityMsgTimer.current) clearTimeout(cityMsgTimer.current)
        cityMsgTimer.current = setTimeout(() => setDetectedCitiesMsg(''), 4000)
      }
      if (data.detected_position) {
        onPositionDetected(data.detected_position)
      }
      // Check if AI response indicates API not available
      if (data.response.includes('未配置API密钥') || data.response.includes('密钥无效')) {
        setDetectedCitiesMsg('AI服务不可用，请检查API密钥配置')
        if (cityMsgTimer.current) clearTimeout(cityMsgTimer.current)
        cityMsgTimer.current = setTimeout(() => setDetectedCitiesMsg(''), 6000)
      }
    } catch {
      setMessages((prev) => [...prev, { role: 'ai', content: '抱歉，回复出错了，请重试。' }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="rounded-lg flex flex-col" style={{ backgroundColor: '#fff', minHeight: '280px' }}>
      <div className="flex-1 p-3 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 280px)' }} role="log" aria-live="polite">
        {messages.length === 0 && (
          <p className="text-xs" style={{ color: '#999' }}>
            和AI聊聊你的工作经历、技能和求职意向，AI将帮你识别岗位关键词和城市偏好
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`mb-2 flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className="rounded-lg px-3 py-2 text-sm max-w-4/5"
              style={{
                backgroundColor: msg.role === 'user' ? '#42A5F5' : '#F0F7FF',
                color: msg.role === 'user' ? '#fff' : '#333',
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start mb-2">
            <div className="rounded-lg px-3 py-2 text-sm" style={{ backgroundColor: '#F0F7FF', color: '#999' }}>
              AI正在输入...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {detectedCitiesMsg && (
        <div className="px-3 py-1.5 text-xs font-medium text-center" style={{ backgroundColor: '#E8F5E9', color: '#2E7D32' }}>
          {detectedCitiesMsg}
        </div>
      )}
      <div className="p-2 border-t flex gap-2" style={{ borderColor: '#E3F2FD' }}>
        <input
          className="flex-1 px-3 py-1.5 rounded-lg text-sm outline-none border"
          style={{ borderColor: '#BBDEFB' }}
          placeholder="描述你的职业背景和求职意向..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          className="px-4 py-1.5 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50 hover:opacity-85"
          style={{ backgroundColor: '#42A5F5' }}
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          发送
        </button>
      </div>
    </div>
  )
}
