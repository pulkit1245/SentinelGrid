import React, { useState } from 'react'
import { MessageSquare, Search, BookOpen, ExternalLink } from 'lucide-react'
import type { RAGResponse } from '../types'
import { api } from '../services/api'

export default function RAGPage() {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<RAGResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleQuery(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.ragQuery(question)
      setResponse(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  const EXAMPLE_QUERIES = [
    'What are the OISD requirements for hot-work near gas zones?',
    'Maximum permissible exposure limit for H2S in confined spaces?',
    'DGMS notification requirements for major incidents?',
  ]

  return (
    <div style={{ padding: '24px 28px', maxWidth: 900, display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>Regulatory RAG Assistant</h1>
        <p style={{ color: 'var(--color-text-secondary)', marginTop: 4, fontSize: 13 }}>
          Ask questions about OISD, DGMS, and Factories Act regulations — grounded in your incident history.
        </p>
      </div>

      {/* Example queries */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {EXAMPLE_QUERIES.map(q => (
          <button
            key={q}
            className="btn btn-ghost"
            style={{ fontSize: 12 }}
            onClick={() => setQuestion(q)}
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <form onSubmit={handleQuery} style={{ display: 'flex', gap: 12 }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Search size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
          <input
            id="rag-query-input"
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="e.g. What PPE is required for confined space entry?"
            style={{
              width: '100%',
              padding: '12px 14px 12px 44px',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-text-primary)',
              fontSize: 14,
              outline: 'none',
            }}
            onFocus={e => (e.target.style.borderColor = 'var(--color-accent)')}
            onBlur={e => (e.target.style.borderColor = 'var(--color-border)')}
          />
        </div>
        <button
          type="submit"
          id="btn-rag-submit"
          disabled={loading || !question.trim()}
          className="btn btn-primary"
        >
          {loading ? <span className="spinner" /> : <><MessageSquare size={14} /> Ask</>}
        </button>
      </form>

      {/* Response */}
      {response && (
        <div className="card animate-fadeIn" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Answer */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <BookOpen size={14} color="var(--color-accent)" />
              <span style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)' }}>
                Answer
              </span>
              {response.confidence > 0 && (
                <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--color-text-muted)' }}>
                  Confidence: {(response.confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
            <p style={{ lineHeight: 1.8, color: 'var(--color-text-primary)' }}>{response.answer}</p>
          </div>

          {/* Citations */}
          {response.citations.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-secondary)', marginBottom: 10 }}>
                Citations
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {response.citations.map((c, i) => (
                  <div key={i} style={{ padding: '10px 14px', background: 'var(--color-surface-2)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--color-accent)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-accent)' }}>{c.source}</span>
                      <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>§ {c.clause}</span>
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{c.excerpt}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {error && (
        <div style={{ padding: '12px 16px', background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)', borderRadius: 'var(--radius-md)', color: 'var(--color-critical)', fontSize: 13 }}>
          {error}
        </div>
      )}
    </div>
  )
}
