import React, { createContext, useCallback, useContext, useRef, useState } from 'react'
import type { User } from '../types'
import { authApi } from '../services/auth'

const TOKEN_KEY = 'sg_access_token'

interface AuthContextValue {
  accessToken: string | null
  currentUser: Partial<User> | null
  isAuthenticated: boolean
  isInitialized: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  getToken: () => string | null
}

const AuthContext = createContext<AuthContextValue | null>(null)

function decodeUser(token: string): Partial<User> | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return { id: payload.sub, email: payload.email, role: payload.role }
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Initialize directly from localStorage — no async, no flicker
  const [accessToken, setAccessToken] = useState<string | null>(() => {
    return localStorage.getItem(TOKEN_KEY)
  })
  const [currentUser, setCurrentUser] = useState<Partial<User> | null>(() => {
    const t = localStorage.getItem(TOKEN_KEY)
    return t ? decodeUser(t) : null
  })
  // Tracks whether we've finished the initial hydration check
  const [isInitialized, setIsInitialized] = useState(true)
  const tokenRef = useRef<string | null>(accessToken)

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password)
    localStorage.setItem(TOKEN_KEY, access_token)
    tokenRef.current = access_token
    setAccessToken(access_token)
    setCurrentUser(decodeUser(access_token))
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout().catch(() => {})
    localStorage.removeItem(TOKEN_KEY)
    tokenRef.current = null
    setAccessToken(null)
    setCurrentUser(null)
  }, [])

  const getToken = useCallback(() => tokenRef.current, [])

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        currentUser,
        isAuthenticated: !!accessToken,
        isInitialized,
        login,
        logout,
        getToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuthContext must be inside AuthProvider')
  return ctx
}
