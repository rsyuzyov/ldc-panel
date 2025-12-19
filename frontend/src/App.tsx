import { useState, useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import { ServersSection } from './components/ServersSection'
import { UsersSection } from './components/UsersSection'
import { DNSSection } from './components/DNSSection'
import { DHCPSection } from './components/DHCPSection'
import { GPOSection } from './components/GPOSection'
import { BackupSection } from './components/BackupSection'
import { LogsSection } from './components/LogsSection'
import { LoginPage } from './components/LoginPage'
import { LoadingOverlay } from './components/LoadingOverlay'
import { useAuth } from './hooks/useAuth'
import { LoadingProvider, useLoading } from './contexts/LoadingContext'
import { setLoadingCallbacks } from './api/client'

export type SectionType = 'servers' | 'users' | 'dns' | 'dhcp' | 'gpo' | 'backup' | 'logs'

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

function AppContent() {
  const { isAuthenticated, loading, login, logout } = useAuth()
  const { startLoading, stopLoading } = useLoading()
  const [activeSection, setActiveSection] = useState<SectionType>('servers')
  const [servers, setServers] = useState<Server[]>([])
  const [currentServerId, setCurrentServerId] = useState<string | null>(null)

  // Связываем API клиент с контекстом загрузки
  useEffect(() => {
    setLoadingCallbacks(startLoading, stopLoading)
  }, [startLoading, stopLoading])

  // Автовыбор сервера если он единственный
  useEffect(() => {
    const availableServers = servers.filter(s => !s.status.startsWith('Ошибка'))
    if (availableServers.length === 1 && !currentServerId) {
      setCurrentServerId(availableServers[0].id)
    }
    // Если текущий сервер удалён
    if (currentServerId && !servers.find(s => s.id === currentServerId)) {
      setCurrentServerId(availableServers[0]?.id || null)
    }
  }, [servers, currentServerId])

  const handleServerAdded = (server: Server) => {
    // Если это первый сервер — выбираем его
    if (servers.length === 0 || (servers.length === 1 && servers[0].id === server.id)) {
      setCurrentServerId(server.id)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-600">Загрузка...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={login} />
  }

  const renderSection = () => {
    // Заглушка если нет сервера (кроме servers и logs)
    if (!currentServerId && activeSection !== 'servers' && activeSection !== 'logs') {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <p className="text-lg mb-2">Сервер не выбран</p>
          <p className="text-sm">Добавьте и выберите сервер для работы с этим разделом</p>
        </div>
      )
    }

    switch (activeSection) {
      case 'servers': return <ServersSection servers={servers} setServers={setServers} onServerAdded={handleServerAdded} />
      case 'users': return <UsersSection serverId={currentServerId!} />
      case 'dns': return <DNSSection serverId={currentServerId!} />
      case 'dhcp': return <DHCPSection serverId={currentServerId!} />
      case 'gpo': return <GPOSection serverId={currentServerId!} />
      case 'backup': return <BackupSection serverId={currentServerId!} />
      case 'logs': return <LogsSection />
      default: return <ServersSection servers={servers} setServers={setServers} onServerAdded={handleServerAdded} />
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar 
        activeSection={activeSection} 
        onSectionChange={setActiveSection} 
        onLogout={logout}
        servers={servers}
        currentServerId={currentServerId}
        onServerChange={setCurrentServerId}
      />
      <main className="flex-1 overflow-auto">
        <div className="p-6">{renderSection()}</div>
      </main>
      <LoadingOverlay />
    </div>
  )
}

export default function App() {
  return (
    <LoadingProvider>
      <AppContent />
    </LoadingProvider>
  )
}
