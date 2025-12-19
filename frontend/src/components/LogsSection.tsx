import { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { api } from '../api/client'

interface LogEntry {
  timestamp: string
  level: string
  operator: string
  action: string
  object: string
  details: string
}

export function LogsSection() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [levelFilter, setLevelFilter] = useState<string>('all')
  const [actionFilter, setActionFilter] = useState<string>('all')

  const loadLogs = async () => {
    setLoading(true)
    try {
      const data = await api.getLogs(200)
      setLogs(data)
    } catch (err) {
      console.error('Failed to load logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [])

  const filteredLogs = logs.filter((log) => {
    if (levelFilter !== 'all' && log.level !== levelFilter) return false
    if (actionFilter !== 'all' && log.action !== actionFilter) return false
    if (search) {
      const searchLower = search.toLowerCase()
      return (
        log.operator.toLowerCase().includes(searchLower) ||
        log.object.toLowerCase().includes(searchLower) ||
        log.details.toLowerCase().includes(searchLower)
      )
    }
    return true
  })

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-600 bg-red-50'
      case 'WARNING': return 'text-yellow-600 bg-yellow-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'CREATE': return 'text-green-600'
      case 'DELETE': return 'text-red-600'
      case 'UPDATE': return 'text-blue-600'
      case 'LOGIN': return 'text-purple-600'
      case 'LOGOUT': return 'text-gray-600'
      default: return 'text-gray-700'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Журнал операций</h2>
          <p className="text-sm text-gray-600 mt-1">История всех операций в системе</p>
        </div>
        <Button onClick={loadLogs} variant="outline" disabled={loading}>
          Обновить
        </Button>
      </div>

      <div className="flex gap-4 items-center">
        <Input
          placeholder="Поиск по оператору, объекту..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <Select value={levelFilter} onValueChange={setLevelFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Уровень" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все</SelectItem>
            <SelectItem value="INFO">INFO</SelectItem>
            <SelectItem value="WARNING">WARNING</SelectItem>
            <SelectItem value="ERROR">ERROR</SelectItem>
          </SelectContent>
        </Select>
        <Select value={actionFilter} onValueChange={setActionFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Действие" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все</SelectItem>
            <SelectItem value="CREATE">CREATE</SelectItem>
            <SelectItem value="UPDATE">UPDATE</SelectItem>
            <SelectItem value="DELETE">DELETE</SelectItem>
            <SelectItem value="LOGIN">LOGIN</SelectItem>
            <SelectItem value="LOGOUT">LOGOUT</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Время</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Уровень</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Оператор</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действие</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Объект</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Детали</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">Загрузка...</td>
              </tr>
            ) : filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">Нет записей</td>
              </tr>
            ) : (
              filteredLogs.map((log, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">{log.timestamp}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded ${getLevelColor(log.level)}`}>
                      {log.level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">{log.operator}</td>
                  <td className="px-4 py-3">
                    <span className={`text-sm font-medium ${getActionColor(log.action)}`}>{log.action}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">{log.object}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">{log.details}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="text-sm text-gray-500">
        Показано {filteredLogs.length} из {logs.length} записей
      </div>
    </div>
  )
}
