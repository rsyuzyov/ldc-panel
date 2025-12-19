import { useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'

interface LoginPageProps {
  onLogin: (username: string, password: string) => Promise<void>
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await onLogin(username, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка авторизации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">LDC Panel</h1>
          <p className="text-gray-600 mt-2">Панель управления Samba AD DC</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="username">Логин</Label>
            <Input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="root"
              required
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Пароль</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          <Button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700"
            disabled={loading}
          >
            {loading ? 'Вход...' : 'Войти'}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Доступ только для root
        </p>
      </div>
    </div>
  )
}
