import { useState, useEffect } from 'react'
import { DataTable } from './DataTable'
import { api } from '../api/client'

interface GPO {
  id: string
  name: string
  status: string
  linkedTo: string
  modifiedDate: string
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
        id: g.id || g.guid || String(i),
        name: g.name || g.display_name || g.guid || '',
        status: 'Включена',
        linkedTo: Array.isArray(g.links) ? g.links.join(', ') : (g.linkedTo || ''),
        modifiedDate: g.when_changed || g.modifiedDate || '',
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
        { key: 'name', label: 'Название политики', width: '30%' },
        { key: 'status', label: 'Статус', width: '15%' },
        { key: 'linkedTo', label: 'Привязана к', width: '30%' },
        { key: 'modifiedDate', label: 'Дата изменения', width: '25%' },
      ]}
      data={gpos}
      searchPlaceholder="Поиск политик..."
    />
  )
}
