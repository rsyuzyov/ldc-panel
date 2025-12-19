import { useState, useEffect } from 'react'
import { DataTable } from './DataTable'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { api } from '../api/client'

interface DNSRecord {
  id: string
  name: string
  type: string
  value: string
  ttl: string
  zone: string
}

interface DNSSectionProps {
  serverId: string
}

export function DNSSection({ serverId }: DNSSectionProps) {
  const [records, setRecords] = useState<DNSRecord[]>([])
  const [zones, setZones] = useState<string[]>([])
  const [currentZone, setCurrentZone] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<DNSRecord | null>(null)
  const [formData, setFormData] = useState({ name: '', type: 'A', value: '', ttl: '3600', zone: '' })

  useEffect(() => {
    loadZones()
  }, [serverId])

  useEffect(() => {
    if (currentZone) {
      loadRecords(currentZone)
    }
  }, [currentZone])

  const loadZones = async () => {
    try {
      const data = await api.getDnsZones(serverId)
      const zoneNames = data.map((z: any) => z.name || z.zone || z)
      setZones(zoneNames)
      if (zoneNames.length > 0 && !currentZone) {
        setCurrentZone(zoneNames[0])
      }
    } catch (e) {
      console.error('Failed to load DNS zones:', e)
      setZones([])
    }
  }

  const loadRecords = async (zone: string) => {
    setLoading(true)
    try {
      const data = await api.getDnsRecords(serverId, zone)
      setRecords(data.map((r: any, i: number) => ({
        id: `${r.name}-${r.type}-${i}`,
        name: r.name || '',
        type: r.type || 'A',
        value: r.value || r.data || '',
        ttl: String(r.ttl || 3600),
        zone: zone,
      })))
    } catch (e) {
      console.error('Failed to load DNS records:', e)
      setRecords([])
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingRecord(null)
    setFormData({ name: '', type: 'A', value: '', ttl: '3600', zone: currentZone })
    setDialogOpen(true)
  }

  const handleEdit = (record: DNSRecord) => {
    setEditingRecord(record)
    setFormData({ name: record.name, type: record.type, value: record.value, ttl: record.ttl, zone: record.zone })
    setDialogOpen(true)
  }

  const handleDelete = async (record: DNSRecord) => {
    if (confirm(`Удалить DNS запись ${record.name} (${record.type})?`)) {
      try {
        await api.deleteDnsRecord(serverId, record.zone, record.name, record.type)
        setRecords(records.filter((r) => r.id !== record.id))
      } catch (e: any) {
        alert(e.message)
      }
    }
  }

  const handleSave = async () => {
    try {
      if (editingRecord) {
        await api.updateDnsRecord(serverId, formData.zone, formData.name, formData.type, {
          value: formData.value,
          ttl: parseInt(formData.ttl),
        })
      } else {
        await api.createDnsRecord(serverId, formData.zone || currentZone, {
          name: formData.name,
          type: formData.type,
          value: formData.value,
          ttl: parseInt(formData.ttl),
        })
      }
      await loadRecords(currentZone)
      setDialogOpen(false)
    } catch (e: any) {
      alert(e.message)
    }
  }

  if (loading && records.length === 0) {
    return <div className="text-gray-500">Загрузка...</div>
  }

  return (
    <>
      <div className="mb-4 flex items-center gap-4">
        <Label>Зона:</Label>
        <Select value={currentZone} onValueChange={setCurrentZone}>
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Выберите зону" />
          </SelectTrigger>
          <SelectContent>
            {zones.map((zone) => (
              <SelectItem key={zone} value={zone}>{zone}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        title="DNS записи"
        description={`Управление DNS записями зоны ${currentZone}`}
        columns={[
          { key: 'name', label: 'Имя', width: '25%' },
          { key: 'type', label: 'Тип', width: '10%' },
          { key: 'value', label: 'Значение', width: '35%' },
          { key: 'ttl', label: 'TTL', width: '10%' },
        ]}
        data={records}
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        searchPlaceholder="Поиск DNS записей..."
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingRecord ? 'Редактирование DNS записи' : 'Добавление DNS записи'}</DialogTitle>
            <DialogDescription>Настройка DNS записи в зоне {currentZone}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Имя записи</Label>
              <Input id="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="www" disabled={!!editingRecord} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Тип записи</Label>
              <Select value={formData.type} onValueChange={(value) => setFormData({ ...formData, type: value })} disabled={!!editingRecord}>
                <SelectTrigger id="type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="A">A</SelectItem>
                  <SelectItem value="AAAA">AAAA</SelectItem>
                  <SelectItem value="CNAME">CNAME</SelectItem>
                  <SelectItem value="MX">MX</SelectItem>
                  <SelectItem value="TXT">TXT</SelectItem>
                  <SelectItem value="SRV">SRV</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="value">Значение</Label>
              <Input id="value" value={formData.value} onChange={(e) => setFormData({ ...formData, value: e.target.value })} placeholder="192.168.1.10" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ttl">TTL (секунды)</Label>
              <Input id="ttl" value={formData.ttl} onChange={(e) => setFormData({ ...formData, ttl: e.target.value })} placeholder="3600" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Отмена</Button>
            <Button onClick={handleSave} className="bg-blue-600 hover:bg-blue-700">Сохранить</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
