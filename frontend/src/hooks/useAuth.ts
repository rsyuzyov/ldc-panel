import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

interface AuthState {
  isAuthenticated: boolean
  username: string | null
  loading: boolean
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    username: null,
    loading: true,
  })

  const checkAuth = useCallback(async () => {
    const token = api.getToken()
    if (!token) {
      setState({ isAuthenticated: false, username: null, loading: false })
      return
    }

    try {
      const user = await api.getMe()
      setState({ isAuthenticated: true, username: user.username, loading: false })
    } catch {
      api.setToken(null)
      setState({ isAuthenticated: false, username: null, loading: false })
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = async (username: string, password: string) => {
    const data = await api.login(username, password)
    setState({ isAuthenticated: true, username: data.username, loading: false })
  }

  const logout = async () => {
    try {
      await api.logout()
    } catch {
      // Ignore errors
    }
    api.setToken(null)
    setState({ isAuthenticated: false, username: null, loading: false })
  }

  return {
    ...state,
    login,
    logout,
    checkAuth,
  }
}
