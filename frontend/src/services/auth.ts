import type { TokenResponse } from '../types'

const BASE = '/api/v1/auth'

export const authApi = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const resp = await fetch(`${BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || 'Login failed')
    }
    return resp.json()
  },

  async refreshToken(): Promise<TokenResponse> {
    const resp = await fetch(`${BASE}/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!resp.ok) throw new Error('Token refresh failed')
    return resp.json()
  },

  async logout(): Promise<void> {
    await fetch(`${BASE}/logout`, { method: 'POST', credentials: 'include' })
  },
}
