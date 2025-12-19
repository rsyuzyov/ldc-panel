import { Server, Users, Network, Settings, Shield, LogOut, Archive, FileText } from 'lucide-react'
import type { SectionType } from '../App'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'

interface ServerInfo {
  id: string
  name: string
  status: string
}

interface SidebarProps {
  activeSection: SectionType
  onSectionChange: (section: SectionType) => void
  onLogout?: () => void
  servers: ServerInfo[]
  currentServerId: string | null
  onServerChange: (serverId: string) => void
}

export function Sidebar({ activeSection, onSectionChange, onLogout, servers, currentServerId, onServerChange }: SidebarProps) {
  const menuItems = [
    { id: 'users' as SectionType, label: 'AD', icon: Users },
    { id: 'dns' as SectionType, label: 'DNS', icon: Network },
    { id: 'dhcp' as SectionType, label: 'DHCP', icon: Settings },
    { id: 'gpo' as SectionType, label: 'GPO', icon: Shield },
    { id: 'backup' as SectionType, label: 'Backup', icon: Archive },
    { id: 'logs' as SectionType, label: 'Логи', icon: FileText },
  ]

  // Показываем все серверы с непустым id, но помечаем неактивные
  const availableServers = servers.filter(s => s.id && !s.status.startsWith('Ошибка'))
  const hasCurrentServer = currentServerId !== null

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex-shrink-0">
      <div className="p-4 border-b border-gray-200">
        <h1 className="font-semibold text-gray-900">LDC Panel</h1>
      </div>

      <div className="p-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs text-gray-600">Текущий сервер</label>
          <button onClick={() => onSectionChange('servers')} className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Управление серверами">
            <Server className="w-4 h-4" />
          </button>
        </div>
        <Select value={currentServerId || undefined} onValueChange={onServerChange}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Выберите сервер" />
          </SelectTrigger>
          <SelectContent>
            {availableServers.length === 0 ? (
              <div className="px-2 py-1.5 text-sm text-gray-500">Нет доступных серверов</div>
            ) : (
              availableServers.map((server) => (
                <SelectItem key={server.id} value={server.id}>
                  {server.name} {server.status !== 'Активен' && `(${server.status})`}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
      </div>

      <nav className="p-2 flex-1">
        {menuItems.map((item) => {
          // Логи доступны всегда, остальное — только с сервером
          const isDisabled = item.id !== 'logs' && !hasCurrentServer
          return (
            <div key={item.id}>
              <button
                onClick={() => !isDisabled && onSectionChange(item.id)}
                disabled={isDisabled}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-md transition-colors ${
                  isDisabled 
                    ? 'text-gray-400 cursor-not-allowed' 
                    : activeSection === item.id 
                      ? 'bg-blue-50 text-blue-700' 
                      : 'text-gray-700 hover:bg-gray-100'
                }`}
                title={isDisabled ? 'Сначала выберите сервер' : undefined}
              >
                <item.icon className="w-4 h-4" />
                <span>{item.label}</span>
              </button>
            </div>
          )
        })}
      </nav>

      {onLogout && (
        <div className="p-3 border-t border-gray-200">
          <button
            onClick={onLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Выход</span>
          </button>
        </div>
      )}
    </aside>
  )
}
