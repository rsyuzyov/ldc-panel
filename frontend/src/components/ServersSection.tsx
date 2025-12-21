import { useState, useEffect } from 'react'
import { DataTable } from './DataTable'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { api } from '../api/client'
import logger from '../utils/logger'

interface Server {
  id: string
  name: string
  host: string
  port: number
  user: string
  auth_type: string
  status: string
  role: string
  version: string
  services?: {
    samba: boolean
    dns: boolean
    dhcp: boolean
  }
}

interface ServersSectionProps {
  onServerAdded?: (server: Server) => void
  servers: Server[]
  setServers: React.Dispatch<React.SetStateAction<Server[]>>
}

export function ServersSection({ onServerAdded, servers, setServers }: ServersSectionProps) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingServer, setEditingServer] = useState<Server | null>(null)
  const [formData, setFormData] = useState({ name: '', host: '', user: 'root', port: 22, auth_type: 'password', password: '' })
  const [keyFile, setKeyFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadServers()
  }, [])

  const loadServers = async () => {
    try {
      const data = await api.getServers()
      const mapped = data.map((s: any) => ({
        ...s,
        status: s.services?.ad ? 'Активен' : 'Требует настройки',
        role: s.services?.ad ? 'Domain Controller' : '',
        version: s.services?.ad ? 'Samba AD' : '',
      }))
      setServers(mapped)

      // Автопроверка серверов которые ещё не проверены
      for (const server of mapped) {
        if (!server.services?.ad && server.id) {
          testServerConnection(server)
        }
      }
    } catch (e) {
      logger.error('Failed to load servers', e as Error)
    }
  }

  const handleAdd = () => {
    setEditingServer(null)
    setFormData({ name: '', host: '', user: 'root', port: 22, auth_type: 'password', password: '' })
    setKeyFile(null)
    setDialogOpen(true)
  }

  const handleEdit = (server: Server) => {
    setEditingServer(server)
    setFormData({ name: server.name, host: server.host, user: server.user, port: server.port, auth_type: server.auth_type || 'password', password: '' })
    setDialogOpen(true)
  }

  const handleDelete = async (server: Server) => {
    if (confirm(`Удалить сервер ${server.name}?`)) {
      try {
        await api.deleteServer(server.id)
        setServers(servers.filter((s) => s.id !== server.id))
      } catch (e) {
        alert((e as Error).message)
      }
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const form = new FormData()
      form.append('name', formData.name)
      form.append('host', formData.host)
      form.append('port', String(formData.port))
      form.append('user', formData.user)
      form.append('auth_type', formData.auth_type)
      if (formData.auth_type === 'password' && formData.password) {
        form.append('password', formData.password)
      }
      if (formData.auth_type === 'key' && keyFile) {
        form.append('key_file', keyFile)
      }

      if (editingServer) {
        // Обновление существующего сервера
        await api.updateServer(editingServer.id, form)
        setServers(servers.map((s) => (s.id === editingServer.id ? { ...s, ...formData, status: 'Проверка...' } : s)))
        setDialogOpen(false)
        // Проверка после обновления
        testServerConnection({ ...editingServer, ...formData })
      } else {
        // Создание нового сервера
        const id = formData.host.replace(/\./g, '-')
        form.append('id', id)

        const created = await api.createServer(form)

        const newServer: Server = {
          id: created.id || id,
          name: created.name || formData.name,
          host: created.host || formData.host,
          port: created.port || formData.port,
          user: created.user || formData.user,
          auth_type: created.auth_type || formData.auth_type,
          status: 'Проверка...',
          role: '',
          version: '',
        }

        setServers((prev) => [...prev, newServer])
        setDialogOpen(false)

        // Автоматическая проверка после добавления
        if (newServer.id) {
          testServerConnection(newServer)
        }
      }
    } catch (e) {
      alert((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const testServerConnection = async (server: Server) => {
    logger.debug('Testing server', { serverId: server.id })
    try {
      setServers((prev) =>
        prev.map((s) => (s.id === server.id ? { ...s, status: 'Проверка...' } : s))
      )

      const result = await api.testServer(server.id)
      logger.debug('Test result', { result })

      setServers((prev) =>
        prev.map((s) => {
          if (s.id !== server.id) return s
          if (result.success) {
            const updated = {
              ...s,
              status: 'Активен',
              role: result.services?.ad ? 'Domain Controller' : 'Server',
              version: result.services?.ad ? 'Samba AD' : '',
              services: result.services,
            }
            onServerAdded?.(updated)
            return updated
          } else {
            return { ...s, status: `Ошибка: ${result.error || 'Не удалось подключиться'}`, role: '', version: '' }
          }
        })
      )
    } catch (e) {
      logger.error('Server test error', e as Error)
      setServers((prev) =>
        prev.map((s) => (s.id === server.id ? { ...s, status: `Ошибка: ${(e as Error).message}` } : s))
      )
    }
  }

  const displayData = servers.map((s) => ({
    ...s,
    id: s.id,
  }))

  return (
    <>
      <DataTable
        title="Серверы"
        description="Управление контроллерами домена Samba AD."
        columns={[
          { key: 'name', label: 'Имя сервера', width: '30%' },
          { key: 'status', label: 'Статус', width: '20%' },
          { key: 'role', label: 'Роль', width: '25%' },
          { key: 'version', label: 'Версия', width: '15%' },
        ]}
        data={displayData}
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        searchPlaceholder="Поиск серверов..."
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingServer ? 'Редактирование сервера' : 'Добавление сервера'}</DialogTitle>
            <DialogDescription>Форма настройки подключения к серверу</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Имя сервера</Label>
              <Input id="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="DC1.domain.local" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="host">Хост (IP или FQDN)</Label>
              <Input id="host" value={formData.host} onChange={(e) => setFormData({ ...formData, host: e.target.value })} placeholder="192.168.1.10" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="user">Пользователь SSH</Label>
                <Input id="user" value={formData.user} onChange={(e) => setFormData({ ...formData, user: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="port">Порт SSH</Label>
                <Input id="port" type="number" value={formData.port} onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) || 22 })} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Тип аутентификации</Label>
              <Select value={formData.auth_type} onValueChange={(v) => setFormData({ ...formData, auth_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="password">Пароль</SelectItem>
                  <SelectItem value="key">SSH ключ</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {formData.auth_type === 'password' && (
              <div className="space-y-2">
                <Label htmlFor="password">Пароль SSH</Label>
                <Input id="password" type="password" value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} placeholder="••••••••" />
              </div>
            )}
            {formData.auth_type === 'key' && (
              <div className="space-y-2">
                <Label htmlFor="key_file">SSH ключ (приватный)</Label>
                <Input id="key_file" type="file" accept=".pem,.key,*" onChange={(e) => setKeyFile(e.target.files?.[0] || null)} />
                {keyFile && <p className="text-sm text-green-600">Выбран: {keyFile.name}</p>}
              </div>
            )}
            <p className="text-sm text-muted-foreground">Роль и версия определяются автоматически при подключении</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Отмена</Button>
            <Button onClick={handleSave} disabled={loading} className="bg-blue-600 hover:bg-blue-700">
              {loading ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
