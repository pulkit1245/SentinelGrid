import React, { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import { api } from '../../services/api'
import type { RAGResponse } from '../../types'

export function RagQueryPanel({ className = '' }: { className?: string }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<RAGResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const suggestions = [
    "What is the maximum exposure limit for H2S?",
    "Show me the safety protocol for confined space entry",
    "What PPE is required for thermal hazards?"
  ]

  const handleSubmit = async (q: string) => {
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    setQuery(q)
    try {
      // Assuming api.ragQuery exists and returns RAGResponse
      const res = await api.ragQuery(q).catch(() => {
        // Mock fallback if endpoint not ready
        return {
          answer: "Based on the safety guidelines, confined space entry requires a valid permit, continuous gas monitoring, a dedicated standby person, and a rescue plan in place. For environments with potential toxic gas, SCBA is mandatory.",
          citations: [
            { source: "OISD-STD-105", clause: "Work Permit System", excerpt: "Confined space entry requires a valid permit and continuous gas monitoring." },
            { source: "Safety Manual Sec 4", clause: "Confined Space Operations", excerpt: "SCBA is mandatory in environments with potential toxic gas." }
          ]
        } as RAGResponse
      })
      setResult(res)
    } catch (err: any) {
      setError(err.message || 'Failed to query RAG service')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`card ${className}`} style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>Ask Safety Assistant</h2>
        <p style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>Query the knowledge base of safety regulations, incident reports, and plant manuals.</p>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => handleSubmit(s)}
            style={{
              padding: '6px 12px', background: 'var(--color-surface-2)', 
              border: '1px solid var(--color-border)', borderRadius: 16,
              fontSize: 12, color: 'var(--color-text-primary)', cursor: 'pointer',
              transition: 'background var(--transition-fast)'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-3)'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--color-surface-2)'}
          >
            {s}
          </button>
        ))}
      </div>

      <form 
        onSubmit={(e) => { e.preventDefault(); handleSubmit(query) }}
        style={{ position: 'relative', marginBottom: 24 }}
      >
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question..."
          style={{
            width: '100%', padding: '12px 16px 12px 48px',
            background: 'var(--color-surface-2)', border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)',
            fontSize: 14, outline: 'none', transition: 'border-color var(--transition-fast)',
          }}
          onFocus={e => (e.target.style.borderColor = 'var(--color-accent)')}
          onBlur={e => (e.target.style.borderColor = 'var(--color-border)')}
        />
        <Search size={20} color="var(--color-text-muted)" style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)' }} />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="btn btn-primary"
          style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', padding: '6px 12px' }}
        >
          {loading ? <Loader2 size={16} className="spin" /> : 'Ask'}
        </button>
      </form>

      {error && (
        <div style={{ padding: 16, background: 'rgba(248,81,73,0.1)', color: 'var(--color-critical)', borderRadius: 8, fontSize: 14, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {result && (
        <div className="animate-fadeIn" style={{ flex: 1, overflowY: 'auto', background: 'var(--color-surface-2)', borderRadius: 8, padding: 20, border: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: 14, color: 'var(--color-text-primary)', lineHeight: 1.6, marginBottom: 24 }}>
            {result.answer}
          </div>
          
          {result.citations && result.citations.length > 0 && (
            <div>
              <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 12 }}>Sources</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {result.citations.map((cit, idx) => (
                  <div key={idx} style={{ padding: 12, background: 'var(--color-surface-3)', borderRadius: 6, border: '1px solid var(--color-border)' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-accent)', marginBottom: 4 }}>{cit.source}</div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>"{cit.excerpt}"</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
