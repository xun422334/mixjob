import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  retryKey: number
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, retryKey: 0 }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, retryKey: 0 }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, retryKey: this.state.retryKey + 1 })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="rounded-lg p-6 text-center" style={{ backgroundColor: '#fff' }}>
          <p className="text-sm font-medium" style={{ color: '#e53935' }}>
            页面加载出错
          </p>
          <p className="text-xs mt-1" style={{ color: '#999' }}>
            {this.state.error?.message || '未知错误'}
          </p>
          <button
            className="mt-3 px-4 py-1.5 rounded-lg text-xs font-medium text-white transition-colors"
            style={{ backgroundColor: '#42A5F5' }}
            onClick={this.handleRetry}
          >
            重试
          </button>
        </div>
      )
    }
    return <div key={this.state.retryKey}>{this.props.children}</div>
  }
}
