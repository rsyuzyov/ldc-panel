import { useState, useEffect } from 'react'
import { DataTable } from './DataTable'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { api } from '../api/client'

interface User {
  id: string
  username: string
  fullName: string
  email: string
  groups: string
  enabled: string
}

interface Computer {
  id: string
  name: string
  os: string
  ip: string
  lastSeen: string
  status: string
}

interface UsersSectionProps {
  serverId: string
}

export function UsersSection({ serverId }: UsersSectionProps) {
  const [users, setUsers] = useState<User[]>([])
  const [computers, setComputers] = useState<Computer[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogType, setDialogType] = useState<'user' | 'computer'>('user')
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [editingComputer, setEditingComputer] = useState<Computer | null>(null)
  const [userFormData, setUserFormData] = useState({ username: '', fullName: '', email: '', groups: 'Domain Users', enabled: 'Да' })
  const [computerFormData, setComputerFormData] = useState({ name: '', os: '', ip: '', lastSeen: '', status: 'Онлайн' })

  useEffect(() => {
    loadData()
  }, [serverId])

  const loadData = async () => {
    setLoading(true)
    try {
      const usersData = await api.getUsers(serverId)
      setUsers(usersData.map((u: any) => ({
        id: u.dn || u.username,
        username: u.username || u.sAMAccountName || '',
        fullName: u.fullName || u.displayName || u.cn || '',
        email: u.email || u.mail || '',
        groups: Array.isArray(u.groups) ? u.groups.join(', ') : (u.groups || ''),
        enabled: u.enabled !== false ? 'Да' : 'Нет',
      })))
      
      // TODO: загрузка компьютеров когда API будет готов
      // const computersData = await api.getComputers(serverId)
      setComputers([])
    } catch (e) {
      console.error('Failed to load users:', e)
      setUsers([])
    } finally {
      setLoading(false)
    }
  }

  const handleAddUser = () => { setDialogType('user'); setEditingUser(null); setUserFormData({ username: '', fullName: '', email: '', groups: 'Domain Users', enabled: 'Да' }); setDialogOpen(true) }
  const handleEditUser = (user: User) => { setDialogType('user'); setEditingUser(user); setUserFormData({ username: user.username, fullName: user.fullName, email: user.email, groups: user.groups, enabled: user.enabled }); setDialogOpen(true) }
  const handleDeleteUser = async (user: User) => {
    if (confirm(`Удалить пользователя ${user.username}?`)) {
      try {
        await api.deleteUser(serverId, user.username)
        setUsers(users.filter((u) => u.id !== user.id))
      } catch (e: any) {
        alert(e.message)
      }
    }
  }
  
  const handleAddComputer = () => { setDialogType('computer'); setEditingComputer(null); setComputerFormData({ name: '', os: '', ip: '', lastSeen: '', status: 'Онлайн' }); setDialogOpen(true) }
  const handleEditComputer = (computer: Computer) => { setDialogType('computer'); setEditingComputer(computer); setComputerFormData({ name: computer.name, os: computer.os, ip: computer.ip, lastSeen: computer.lastSeen, status: computer.status }); setDialogOpen(true) }
  const handleDeleteComputer = (computer: Computer) => { if (confirm(`Удалить компьютер ${computer.name}?`)) setComputers(computers.filter((c) => c.id !== computer.id)) }

  const handleSave = async () => {
    if (dialogType === 'user') {
      try {
        if (editingUser) {
          await api.updateUser(serverId, editingUser.username, userFormData)
          setUsers(users.map((u) => (u.id === editingUser.id ? { ...u, ...userFormData } : u)))
        } else {
          await api.createUser(serverId, userFormData)
          await loadData() // Перезагружаем список
        }
        setDialogOpen(false)
      } catch (e: any) {
        alert(e.message)
      }
    } else {
      // Компьютеры пока локально
      if (editingComputer) setComputers(computers.map((c) => (c.id === editingComputer.id ? { ...editingComputer, ...computerFormData } : c)))
      else setComputers([...computers, { id: String(Date.now()), ...computerFormData }])
      setDialogOpen(false)
    }
  }

  if (loading) {
    return <div className="text-gray-500">Загрузка...</div>
  }

  return (
    <>
      <Tabs defaultValue="users" className="w-full">
        <TabsList><TabsTrigger value="users">Пользователи</TabsTrigger><TabsTrigger value="computers">Компьютеры</TabsTrigger></TabsList>
        <TabsContent value="users" className="mt-4">
          <DataTable title="Пользователи домена" description="Управление пользователями Active Directory." columns={[{ key: 'username', label: 'Логин', width: '15%' }, { key: 'fullName', label: 'Полное имя', width: '20%' }, { key: 'email', label: 'Email', width: '25%' }, { key: 'groups', label: 'Группы', width: '20%' }, { key: 'enabled', label: 'Активен', width: '10%' }]} data={users} onAdd={handleAddUser} onEdit={handleEditUser} onDelete={handleDeleteUser} searchPlaceholder="Поиск пользователей..." />
        </TabsContent>
        <TabsContent value="computers" className="mt-4">
          <DataTable title="Компьютеры домена" description="Управление компьютерами в домене." columns={[{ key: 'name', label: 'Имя', width: '15%' }, { key: 'os', label: 'ОС', width: '20%' }, { key: 'ip', label: 'IP адрес', width: '15%' }, { key: 'lastSeen', label: 'Последняя активность', width: '20%' }, { key: 'status', label: 'Статус', width: '15%' }]} data={computers} onAdd={handleAddComputer} onEdit={handleEditComputer} onDelete={handleDeleteComputer} searchPlaceholder="Поиск компьютеров..." />
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{dialogType === 'user' ? (editingUser ? 'Редактирование пользователя' : 'Добавление пользователя') : (editingComputer ? 'Редактирование компьютера' : 'Добавление компьютера')}</DialogTitle>
          <DialogDescription>{dialogType === 'user' ? 'Настройка учётной записи пользователя' : 'Настройка компьютера домена'}</DialogDescription></DialogHeader>
          <div className="space-y-4 py-4">
            {dialogType === 'user' ? (
              <>
                <div className="space-y-2"><Label htmlFor="username">Логин</Label><Input id="username" value={userFormData.username} onChange={(e) => setUserFormData({ ...userFormData, username: e.target.value })} placeholder="ivanov" disabled={!!editingUser} /></div>
                <div className="space-y-2"><Label htmlFor="fullName">Полное имя</Label><Input id="fullName" value={userFormData.fullName} onChange={(e) => setUserFormData({ ...userFormData, fullName: e.target.value })} placeholder="Иванов Иван" /></div>
                <div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" value={userFormData.email} onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })} placeholder="ivanov@domain.local" /></div>
                <div className="space-y-2"><Label htmlFor="groups">Группы</Label><Input id="groups" value={userFormData.groups} onChange={(e) => setUserFormData({ ...userFormData, groups: e.target.value })} placeholder="Domain Users" /></div>
              </>
            ) : (
              <>
                <div className="space-y-2"><Label htmlFor="name">Имя компьютера</Label><Input id="name" value={computerFormData.name} onChange={(e) => setComputerFormData({ ...computerFormData, name: e.target.value })} placeholder="WS-001" /></div>
                <div className="space-y-2"><Label htmlFor="os">Операционная система</Label><Input id="os" value={computerFormData.os} onChange={(e) => setComputerFormData({ ...computerFormData, os: e.target.value })} placeholder="Windows 11 Pro" /></div>
                <div className="space-y-2"><Label htmlFor="ip">IP адрес</Label><Input id="ip" value={computerFormData.ip} onChange={(e) => setComputerFormData({ ...computerFormData, ip: e.target.value })} placeholder="192.168.1.100" /></div>
              </>
            )}
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setDialogOpen(false)}>Отмена</Button><Button onClick={handleSave} className="bg-blue-600 hover:bg-blue-700">Сохранить</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
