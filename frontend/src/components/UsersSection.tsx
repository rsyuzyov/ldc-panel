import { useState, useEffect } from 'react'
import { Key } from 'lucide-react'
import { DataTable } from './DataTable'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { MultiSelect } from './ui/multi-select'
import { api } from '../api/client'

interface ADGroup {
  dn: string
  cn: string
  sAMAccountName: string
}

interface User {
  id: string
  dn: string
  username: string
  fullName: string
  email: string
  groups: string
  groupDns: string[]
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

interface ServiceAccount {
  id: string
  name: string
  cn: string
  description: string
}

interface UsersSectionProps {
  serverId: string
}

export function UsersSection({ serverId }: UsersSectionProps) {
  const [users, setUsers] = useState<User[]>([])
  const [computers, setComputers] = useState<Computer[]>([])
  const [, setServiceAccounts] = useState<ServiceAccount[]>([])
  const [allGroups, setAllGroups] = useState<ADGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [groupsLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogType, setDialogType] = useState<'user' | 'computer'>('user')
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [editingComputer, setEditingComputer] = useState<Computer | null>(null)
  const [userFormData, setUserFormData] = useState({ username: '', fullName: '', email: '', groups: 'Domain Users', enabled: 'Да' })
  const [selectedGroupDns, setSelectedGroupDns] = useState<string[]>([])
  const [computerFormData, setComputerFormData] = useState({ name: '', os: '', ip: '', lastSeen: '', status: 'Онлайн' })
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)
  const [passwordUser, setPasswordUser] = useState<User | null>(null)
  const [newPassword, setNewPassword] = useState('')

  useEffect(() => {
    loadData()
  }, [serverId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [usersData, computersData, serviceData, groupsData] = await Promise.all([
        api.getUsers(serverId),
        api.getComputers(serverId).catch(() => []),
        api.getServiceAccounts(serverId).catch(() => []),
        api.getGroups(serverId).catch(() => []),
      ])

      setAllGroups(groupsData.map((g: any) => ({
        dn: g.dn,
        cn: g.cn,
        sAMAccountName: g.sAMAccountName,
      })))

      setUsers(
        usersData.map((u: any) => {
          // memberOf содержит DN групп в base64, декодируем и извлекаем CN
          const memberOf = u.memberOf || u.groups || []
          const memberOfArray = Array.isArray(memberOf) ? memberOf : [memberOf]
          
          // Декодируем DN групп
          const decodedDns = memberOfArray.map((dn: string) => {
            try {
              return decodeURIComponent(escape(atob(dn)))
            } catch {
              return dn
            }
          })
          
          const groupNames = decodedDns
            .map((decoded: string) => {
              const match = decoded.match(/CN=([^,]+)/i)
              return match ? match[1] : decoded
            })
            .join(', ')
          
          return {
            id: u.dn || u.username,
            dn: u.dn || '',
            username: u.username || u.sAMAccountName || '',
            fullName: u.fullName || u.displayName || u.cn || '',
            email: u.email || u.mail || '',
            groups: groupNames,
            groupDns: decodedDns,
            enabled: u.enabled !== false ? 'Да' : 'Нет',
          }
        })
      )

      setComputers(
        computersData.map((c: any) => ({
          id: c.dn || c.cn,
          name: c.cn || c.sAMAccountName?.replace('$', '') || '',
          os: c.operatingSystem || '',
          ip: c.dNSHostName || '',
          lastSeen: c.lastLogonTimestamp || '',
          status: c.enabled !== false ? 'Активен' : 'Отключён',
        }))
      )

      setServiceAccounts(
        serviceData.map((s: any) => ({
          id: s.dn || s.sAMAccountName,
          name: s.sAMAccountName || '',
          cn: s.cn || '',
          description: s.description || '',
        }))
      )
    } catch (e) {
      console.error('Failed to load data:', e)
      setUsers([])
    } finally {
      setLoading(false)
    }
  }

  const handleAddUser = () => {
    setDialogType('user')
    setEditingUser(null)
    setUserFormData({ username: '', fullName: '', email: '', groups: 'Domain Users', enabled: 'Да' })
    setSelectedGroupDns([])
    setDialogOpen(true)
  }
  const handleEditUser = (user: User) => {
    setDialogType('user')
    setEditingUser(user)
    setUserFormData({ username: user.username, fullName: user.fullName, email: user.email, groups: user.groups, enabled: user.enabled })
    setSelectedGroupDns(user.groupDns || [])
    setDialogOpen(true)
  }
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

  const handleChangePassword = (user: User) => {
    setPasswordUser(user)
    setNewPassword('')
    setPasswordDialogOpen(true)
  }

  const handleSavePassword = async () => {
    if (!passwordUser || !newPassword) return
    try {
      await api.changeUserPassword(serverId, passwordUser.username, newPassword)
      setPasswordDialogOpen(false)
      alert('Пароль успешно изменён')
    } catch (e: any) {
      alert(e.message)
    }
  }

  const handleAddComputer = () => {
    setDialogType('computer')
    setEditingComputer(null)
    setComputerFormData({ name: '', os: '', ip: '', lastSeen: '', status: 'Онлайн' })
    setDialogOpen(true)
  }
  const handleEditComputer = (computer: Computer) => {
    setDialogType('computer')
    setEditingComputer(computer)
    setComputerFormData({ name: computer.name, os: computer.os, ip: computer.ip, lastSeen: computer.lastSeen, status: computer.status })
    setDialogOpen(true)
  }
  const handleDeleteComputer = (computer: Computer) => {
    if (confirm(`Удалить компьютер ${computer.name}?`)) setComputers(computers.filter((c) => c.id !== computer.id))
  }

  const handleSave = async () => {
    if (dialogType === 'user') {
      try {
        if (editingUser) {
          // Обновляем базовые данные пользователя
          await api.updateUser(serverId, editingUser.username, userFormData)
          
          // Обновляем членство в группах
          const currentGroupDns = editingUser.groupDns || []
          const toAdd = selectedGroupDns.filter((dn) => !currentGroupDns.includes(dn))
          const toRemove = currentGroupDns.filter((dn) => !selectedGroupDns.includes(dn))
          
          // Добавляем в новые группы
          for (const groupDn of toAdd) {
            try {
              await api.addUserToGroup(serverId, groupDn, editingUser.dn)
            } catch (e) {
              console.error('Failed to add to group:', groupDn, e)
            }
          }
          
          // Удаляем из старых групп
          for (const groupDn of toRemove) {
            try {
              await api.removeUserFromGroup(serverId, groupDn, editingUser.dn)
            } catch (e) {
              console.error('Failed to remove from group:', groupDn, e)
            }
          }
          
          await loadData()
        } else {
          await api.createUser(serverId, userFormData)
          await loadData()
        }
        setDialogOpen(false)
      } catch (e: any) {
        alert(e.message)
      }
    } else {
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
        <TabsList>
          <TabsTrigger value="users">Пользователи</TabsTrigger>
          <TabsTrigger value="computers">Компьютеры</TabsTrigger>
        </TabsList>
        <TabsContent value="users" className="mt-4">
          <DataTable
            title="Пользователи домена"
            description="Управление пользователями Active Directory."
            columns={[
              { key: 'username', label: 'Логин', width: '15%' },
              { key: 'fullName', label: 'Полное имя', width: '20%' },
              { key: 'email', label: 'Email', width: '25%' },
              { key: 'groups', label: 'Группы', width: '20%' },
              { key: 'enabled', label: 'Активен', width: '10%' },
            ]}
            data={users}
            onAdd={handleAddUser}
            onEdit={handleEditUser}
            onDelete={handleDeleteUser}
            customActions={[
              {
                icon: <Key className="w-4 h-4" />,
                title: 'Сменить пароль',
                onClick: handleChangePassword,
                className: 'p-1 text-amber-600 hover:bg-amber-50 rounded transition-colors',
              },
            ]}
            searchPlaceholder="Поиск пользователей..."
          />
        </TabsContent>
        <TabsContent value="computers" className="mt-4">
          <DataTable
            title="Компьютеры домена"
            description="Управление компьютерами в домене."
            columns={[
              { key: 'name', label: 'Имя', width: '20%' },
              { key: 'os', label: 'ОС', width: '25%' },
              { key: 'ip', label: 'DNS имя', width: '20%' },
              { key: 'lastSeen', label: 'Последний вход', width: '20%' },
              { key: 'status', label: 'Статус', width: '15%' },
            ]}
            data={computers}
            onAdd={handleAddComputer}
            onEdit={handleEditComputer}
            onDelete={handleDeleteComputer}
            searchPlaceholder="Поиск компьютеров..."
          />
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogType === 'user' ? (editingUser ? 'Редактирование пользователя' : 'Добавление пользователя') : editingComputer ? 'Редактирование компьютера' : 'Добавление компьютера'}
            </DialogTitle>
            <DialogDescription>{dialogType === 'user' ? 'Настройка учётной записи пользователя' : 'Настройка компьютера домена'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4 overflow-hidden">
            {dialogType === 'user' ? (
              <>
                <div className="space-y-2">
                  <Label htmlFor="username">Логин</Label>
                  <Input id="username" value={userFormData.username} onChange={(e) => setUserFormData({ ...userFormData, username: e.target.value })} placeholder="ivanov" disabled={!!editingUser} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fullName">Полное имя</Label>
                  <Input id="fullName" value={userFormData.fullName} onChange={(e) => setUserFormData({ ...userFormData, fullName: e.target.value })} placeholder="Иванов Иван" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" value={userFormData.email} onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })} placeholder="ivanov@domain.local" />
                </div>
                <div className="space-y-2">
                  <Label>Группы</Label>
                  <MultiSelect
                    options={allGroups.map((g) => ({ value: g.dn, label: g.cn }))}
                    selected={selectedGroupDns}
                    onChange={setSelectedGroupDns}
                    placeholder="Выберите группы..."
                    loading={groupsLoading}
                  />
                </div>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="name">Имя компьютера</Label>
                  <Input id="name" value={computerFormData.name} onChange={(e) => setComputerFormData({ ...computerFormData, name: e.target.value })} placeholder="WS-001" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="os">Операционная система</Label>
                  <Input id="os" value={computerFormData.os} onChange={(e) => setComputerFormData({ ...computerFormData, os: e.target.value })} placeholder="Windows 11 Pro" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ip">IP адрес</Label>
                  <Input id="ip" value={computerFormData.ip} onChange={(e) => setComputerFormData({ ...computerFormData, ip: e.target.value })} placeholder="192.168.1.100" />
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Отмена
            </Button>
            <Button onClick={handleSave} className="bg-blue-600 hover:bg-blue-700">
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Смена пароля</DialogTitle>
            <DialogDescription>Новый пароль для {passwordUser?.username}</DialogDescription>
          </DialogHeader>
          <form autoComplete="off" onSubmit={(e) => e.preventDefault()}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="newPassword">Новый пароль</Label>
                <Input
                  id="newPassword"
                  type="password"
                  name="new-password-field"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Введите новый пароль"
                  autoComplete="new-password"
                  data-form-type="other"
                  data-lpignore="true"
                />
              </div>
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasswordDialogOpen(false)}>
              Отмена
            </Button>
            <Button onClick={handleSavePassword} className="bg-blue-600 hover:bg-blue-700" disabled={!newPassword}>
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
