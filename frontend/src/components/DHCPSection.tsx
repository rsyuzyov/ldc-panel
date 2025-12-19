import { useState, useEffect } from 'react'
import { DataTable } from './DataTable'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { api } from '../api/client'

interface DHCPScope {
  id: string
  name: string
  network: string
  rangeStart: string
  rangeEnd: string
  gateway: string
  dns: string
}

interface DHCPReservation {
  id: string
  hostname: string
  mac: string
  ip: string
  description: string
}

interface DHCPLease {
  id: string
  ip: string
  mac: string
  hostname: string
  expires: string
}

interface DHCPSectionProps {
  serverId: string
}

export function DHCPSection({ serverId }: DHCPSectionProps) {
  const [scopes, setScopes] = useState<DHCPScope[]>([])
  const [reservations, setReservations] = useState<DHCPReservation[]>([])
  const [leases, setLeases] = useState<DHCPLease[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogType, setDialogType] = useState<'scope' | 'reservation'>('reservation')
  const [editingReservation, setEditingReservation] = useState<DHCPReservation | null>(null)
  const [reservationFormData, setReservationFormData] = useState({ hostname: '', mac: '', ip: '', description: '' })

  useEffect(() => {
    loadData()
  }, [serverId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [subnetData, reservationData, leaseData] = await Promise.all([
        api.getDhcpSubnets(serverId).catch(() => []),
        api.getDhcpReservations(serverId).catch(() => []),
        api.getDhcpLeases(serverId).catch(() => []),
      ])

      setScopes(subnetData.map((s: any, i: number) => ({
        id: s.id || String(i),
        name: s.name || s.subnet || '',
        network: s.network || s.subnet || '',
        rangeStart: s.rangeStart || s.range_start || '',
        rangeEnd: s.rangeEnd || s.range_end || '',
        gateway: s.gateway || s.routers || '',
        dns: s.dns || s.dns_servers || '',
      })))

      setReservations(reservationData.map((r: any, i: number) => ({
        id: r.id || r.mac || String(i),
        hostname: r.hostname || r.name || '',
        mac: r.mac || '',
        ip: r.ip || r.address || '',
        description: r.description || '',
      })))

      setLeases(leaseData.map((l: any, i: number) => ({
        id: l.id || String(i),
        ip: l.ip || l.address || '',
        mac: l.mac || '',
        hostname: l.hostname || l.client_hostname || '',
        expires: l.expires || l.end || '',
      })))
    } catch (e) {
      console.error('Failed to load DHCP data:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleAddReservation = () => {
    setDialogType('reservation')
    setEditingReservation(null)
    setReservationFormData({ hostname: '', mac: '', ip: '', description: '' })
    setDialogOpen(true)
  }

  const handleEditReservation = (reservation: DHCPReservation) => {
    setDialogType('reservation')
    setEditingReservation(reservation)
    setReservationFormData({
      hostname: reservation.hostname,
      mac: reservation.mac,
      ip: reservation.ip,
      description: reservation.description,
    })
    setDialogOpen(true)
  }

  const handleDeleteReservation = async (reservation: DHCPReservation) => {
    if (confirm(`Удалить резервирование для ${reservation.hostname}?`)) {
      try {
        await api.deleteDhcpReservation(serverId, reservation.mac)
        setReservations(reservations.filter((r) => r.id !== reservation.id))
      } catch (e: any) {
        alert(e.message)
      }
    }
  }

  const handleSave = async () => {
    try {
      if (editingReservation) {
        // Update не поддерживается — удаляем и создаём заново
        await api.deleteDhcpReservation(serverId, editingReservation.mac)
      }
      await api.createDhcpReservation(serverId, reservationFormData)
      await loadData()
      setDialogOpen(false)
    } catch (e: any) {
      alert(e.message)
    }
  }

  if (loading) {
    return <div className="text-gray-500">Загрузка...</div>
  }

  return (
    <>
      <Tabs defaultValue="scopes" className="w-full">
        <TabsList>
          <TabsTrigger value="scopes">Области DHCP</TabsTrigger>
          <TabsTrigger value="reservations">Резервирования</TabsTrigger>
          <TabsTrigger value="leases">Аренды</TabsTrigger>
        </TabsList>

        <TabsContent value="scopes" className="mt-4">
          <DataTable
            title="Области DHCP"
            description="Настроенные DHCP области (только просмотр)"
            columns={[
              { key: 'name', label: 'Название', width: '15%' },
              { key: 'network', label: 'Сеть', width: '15%' },
              { key: 'rangeStart', label: 'Начало', width: '15%' },
              { key: 'rangeEnd', label: 'Конец', width: '15%' },
              { key: 'gateway', label: 'Шлюз', width: '15%' },
              { key: 'dns', label: 'DNS', width: '15%' },
            ]}
            data={scopes}
            searchPlaceholder="Поиск областей..."
          />
        </TabsContent>

        <TabsContent value="reservations" className="mt-4">
          <DataTable
            title="Резервирования IP адресов"
            description="Статические привязки IP адресов к MAC адресам"
            columns={[
              { key: 'hostname', label: 'Имя хоста', width: '20%' },
              { key: 'mac', label: 'MAC адрес', width: '20%' },
              { key: 'ip', label: 'IP адрес', width: '15%' },
              { key: 'description', label: 'Описание', width: '35%' },
            ]}
            data={reservations}
            onAdd={handleAddReservation}
            onEdit={handleEditReservation}
            onDelete={handleDeleteReservation}
            searchPlaceholder="Поиск резервирований..."
          />
        </TabsContent>

        <TabsContent value="leases" className="mt-4">
          <DataTable
            title="Активные аренды"
            description="Текущие DHCP аренды (только просмотр)"
            columns={[
              { key: 'ip', label: 'IP адрес', width: '20%' },
              { key: 'mac', label: 'MAC адрес', width: '20%' },
              { key: 'hostname', label: 'Имя хоста', width: '25%' },
              { key: 'expires', label: 'Истекает', width: '25%' },
            ]}
            data={leases}
            searchPlaceholder="Поиск аренд..."
          />
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingReservation ? 'Редактирование резервирования' : 'Добавление резервирования'}</DialogTitle>
            <DialogDescription>Привязка IP адреса к MAC адресу</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="hostname">Имя хоста</Label>
              <Input id="hostname" value={reservationFormData.hostname} onChange={(e) => setReservationFormData({ ...reservationFormData, hostname: e.target.value })} placeholder="printer-01" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mac">MAC адрес</Label>
              <Input id="mac" value={reservationFormData.mac} onChange={(e) => setReservationFormData({ ...reservationFormData, mac: e.target.value })} placeholder="00:11:22:33:44:55" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ip">IP адрес</Label>
              <Input id="ip" value={reservationFormData.ip} onChange={(e) => setReservationFormData({ ...reservationFormData, ip: e.target.value })} placeholder="192.168.1.50" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Описание</Label>
              <Input id="description" value={reservationFormData.description} onChange={(e) => setReservationFormData({ ...reservationFormData, description: e.target.value })} placeholder="Принтер офис" />
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
