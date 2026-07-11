import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCcw } from 'lucide-react'

interface Props {
  children?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100%', padding: 24 }}>
          <div className="card" style={{ maxWidth: 500, textAlign: 'center', padding: 32 }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
              <div style={{ width: 64, height: 64, borderRadius: '50%', background: 'rgba(248,81,73,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <AlertTriangle size={32} color="var(--color-critical)" />
              </div>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>Something went wrong</h2>
            <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginBottom: 24 }}>
              An unexpected error occurred in this component. Our team has been notified.
            </p>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div style={{ background: 'var(--color-surface-2)', padding: 12, borderRadius: 8, fontSize: 12, fontFamily: 'monospace', color: 'var(--color-critical)', textAlign: 'left', marginBottom: 24, overflowX: 'auto' }}>
                {this.state.error.toString()}
              </div>
            )}
            <button 
              className="btn btn-primary"
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}
            >
              <RefreshCcw size={16} />
              Try Again
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
