import { useState, useEffect } from 'react'
import { DataTable } from './DataTable'
import { api } from '../api/client'

interface GPO {
  id: string
  name: string
  status: string
  linkedTo: string
  modifiedDate: string
  description: string
}

interface GPOSectionProps {
  serverId: string
}

export function GPOSection({ serverId }: GPOSectionProps) {
  const [gpos, setGpos] = useState<GPO[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [serverId])

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await api.getGpos(serverId)
      setGpos(data.map((g: any, i: number) => ({
        id: g.id || g.dn || String(i),
        name: g.name || g.displayName || '',
        status: g.enabled !== false ? 'Включена' : 'Отключена',
        linkedTo: Array.isArray(g.linkedTo) ? g.linkedTo.join(', ') : (g.linkedTo || g.gPCFileSysPath || ''),
        modifiedDate: g.modifiedDate || g.whenChanged || '',
        description: g.description || '',
      })))
    } catch (e) {
      console.error('Failed to load GPOs:', e)
      setGpos([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-gray-500">Загрузка...</div>
  }

  return (
    <DataTable
      title="Групповые политики (GPO)"
      description="Просмотр групповых политик Active Directory (только чтение)"
      columns={[
        { key: 'name', label: 'Название политики', width: '25%' },
        { key: 'status', label: 'Статус', width: '12%' },
        { key: 'linkedTo', label: 'Привязана к', width: '25%' },
        { key: 'modifiedDate', label: 'Дата изменения', width: '18%' },
        { key: 'description', label: 'Описание', width: '20%' },
      ]}
      data={gpos}
      searchPlaceholder="Поиск политик..."
    />
  )
}
