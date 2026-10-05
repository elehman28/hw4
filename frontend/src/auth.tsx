import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import * as api from './api'
import type { SignupData, User } from './api'

const TOKEN_KEY = 'cc_session'

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (data: SignupData) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!token)

  // Restore the session on page load.
  useEffect(() => {
    if (!token) return
    api
      .fetchMe(token)
      .then((r) => setUser(r.user))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
      })
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function startSession(res: api.AuthResponse) {
    localStorage.setItem(TOKEN_KEY, res.token)
    setToken(res.token)
    setUser(res.user)
  }

  const value: AuthState = {
    user,
    token,
    loading,
    login: async (email, password) => startSession(await api.login(email, password)),
    signup: async (data) => startSession(await api.signup(data)),
    logout: async () => {
      if (token) await api.logout(token).catch(() => undefined)
      localStorage.removeItem(TOKEN_KEY)
      setToken(null)
      setUser(null)
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
