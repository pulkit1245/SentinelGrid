import React, { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Shield, AlertTriangle, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { login, isAuthenticated } = useAuth()

  // ✅ Guard: if already authenticated (or just became authenticated after login),
  // React will re-render this component with isAuthenticated=true and this
  // Navigate fires. No manual navigate() needed — no race condition.
  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await login(email, password)
      // ✅ Do NOT call navigate() here. After login() resolves:
      //    - localStorage has the token
      //    - setAccessToken() has been queued
      //    - React re-renders this component
      //    - isAuthenticated becomes true
      //    - The <Navigate> guard above fires
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(ellipse at 60% 20%, rgba(110,94,224,0.12) 0%, transparent 60%), var(--color-bg)',
      padding: '24px',
    }}>
      <div style={{ width: '100%', maxWidth: 420 }} className="animate-fadeIn">
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 64, height: 64,
            background: 'linear-gradient(135deg, var(--color-accent), #4f3fb0)',
            borderRadius: 16,
            marginBottom: 16,
            boxShadow: 'var(--shadow-glow-accent)',
          }}>
            <Shield size={32} color="#fff" />
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.5px' }}>SentinelGrid</h1>
          <p style={{ color: 'var(--color-text-secondary)', marginTop: 6, fontSize: 13 }}>
            Industrial Safety Command Centre
          </p>
        </div>

        {/* Card */}
        <div className="card" style={{ padding: 32 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 24 }}>Sign in to your account</h2>

          {error && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '10px 14px', borderRadius: 'var(--radius-md)',
              background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
              color: 'var(--color-critical)', fontSize: 13, marginBottom: 20,
            }}>
              <AlertTriangle size={14} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label htmlFor="email" style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                placeholder="officer@plant.com"
                style={{
                  width: '100%', padding: '10px 14px',
                  background: 'var(--color-surface-2)', border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)',
                  fontSize: 14, outline: 'none', transition: 'border-color var(--transition-fast)',
                }}
                onFocus={e => (e.target.style.borderColor = 'var(--color-accent)')}
                onBlur={e => (e.target.style.borderColor = 'var(--color-border)')}
              />
            </div>

            <div>
              <label htmlFor="password" style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  style={{
                    width: '100%', padding: '10px 40px 10px 14px',
                    background: 'var(--color-surface-2)', border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)',
                    fontSize: 14, outline: 'none', transition: 'border-color var(--transition-fast)',
                  }}
                  onFocus={e => (e.target.style.borderColor = 'var(--color-accent)')}
                  onBlur={e => (e.target.style.borderColor = 'var(--color-border)')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  style={{
                    position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', color: 'var(--color-text-muted)',
                    display: 'flex', alignItems: 'center',
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              id="btn-login"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', padding: '11px 0', fontSize: 14, marginTop: 8 }}
            >
              {loading ? <span className="spinner" /> : 'Sign In'}
            </button>
          </form>

          <div style={{ marginTop: 20, padding: '12px 16px', background: 'rgba(110,94,224,0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(110,94,224,0.2)' }}>
            <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', fontWeight: 600, marginBottom: 6 }}>Demo credentials</p>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span>officer@sentinelgrid.demo / Demo@1234</span>
              <span>admin@sentinelgrid.demo / Demo@1234</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
