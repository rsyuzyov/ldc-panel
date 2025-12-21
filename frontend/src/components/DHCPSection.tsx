import { useState, useEffect } from 'react'
import { DataTable } from './DataTable'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs'
import { api } from '../api/client'
import logger from '../utils/logger'

interface DHCPScope {
  id: string
  network: string
  netmask: string
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
  const [editingScope, setEditingScope] = useState<DHCPScope | null>(null)
  const [editingReservation, setEditingReservation] = useState<DHCPReservation | null>(null)
  const [scopeFormData, setScopeFormData] = useState({ network: '', netmask: '255.255.255.0', rangeStart: '', rangeEnd: '', gateway: '', dns: '' })
  const [reservationFormData, setReservationFormData] = useState({ hostname: '', mac: '', ip: '', description: '' })

  useEffect(() => {
    loadData()
  }, [serverId])

  const loadData = async () => {
    setLoading(true)
    try {
      // Используем объединённый эндпоинт — один запрос вместо трёх
      const data = await api.getDhcpAll(serverId)

      setScopes(
        data.subnets.map((s: any, i: number) => ({
          id: s.id || String(i),
          network: s.network || s.subnet || '',
          netmask: s.netmask || '255.255.255.0',
          rangeStart: s.range_start || s.rangeStart || '',
          rangeEnd: s.range_end || s.rangeEnd || '',
          gateway: s.routers || s.gateway || '',
          dns: s.domain_name_servers || s.dns || '',
        }))
      )

      setReservations(
        data.reservations.map((r: any, i: number) => ({
          id: r.id || r.mac || String(i),
          hostname: r.hostname || r.name || '',
          mac: r.mac || '',
          ip: r.ip || r.address || '',
          description: r.description || '',
        }))
      )

      setLeases(
        data.leases.map((l: any, i: number) => ({
          id: l.id || String(i),
          ip: l.ip || l.address || '',
          mac: l.mac || '',
          hostname: l.hostname || l.client_hostname || '',
          expires: l.ends || l.expires || '',
        }))
      )
    } catch (e) {
      logger.error('Failed to load DHCP data', e as Error)
    } finally {
      setLoading(false)
    }
  }

  // Scope handlers
  const handleAddScope = () => {
    setDialogType('scope')
    setEditingScope(null)
    setScopeFormData({ network: '', netmask: '255.255.255.0', rangeStart: '', rangeEnd: '', gateway: '', dns: '' })
    setDialogOpen(true)
  }

  const handleEditScope = (scope: DHCPScope) => {
    setDialogType('scope')
    setEditingScope(scope)
    setScopeFormData({
      network: scope.network,
      netmask: scope.netmask,
      rangeStart: scope.rangeStart,
      rangeEnd: scope.rangeEnd,
      gateway: scope.gateway,
      dns: scope.dns,
    })
    setDialogOpen(true)
  }

  const handleDeleteScope = async (scope: DHCPScope) => {
    if (confirm(`Удалить область ${scope.network}? Будет создан бэкап конфигурации.`)) {
      try {
        await api.deleteDhcpSubnet(serverId, scope.id)
        await loadData()
      } catch (e: any) {
        alert(e.message)
      }
    }
  }

  // Reservation handlers
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
        await loadData()
      } catch (e: any) {
        alert(e.message)
      }
    }
  }

  const handleSave = async () => {
    try {
      if (dialogType === 'scope') {
        const data = {
          network: scopeFormData.network,
          netmask: scopeFormData.netmask,
          range_start: scopeFormData.rangeStart || null,
          range_end: scopeFormData.rangeEnd || null,
          routers: scopeFormData.gateway || null,
          domain_name_servers: scopeFormData.dns || null,
        }
        if (editingScope) {
          await api.updateDhcpSubnet(serverId, editingScope.id, data)
        } else {
          await api.createDhcpSubnet(serverId, data)
        }
      } else {
        if (editingReservation) {
          await api.deleteDhcpReservation(serverId, editingReservation.mac)
        }
        await api.createDhcpReservation(serverId, reservationFormData)
      }
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
            description="Настроенные DHCP области. При сохранении создаётся бэкап."
            columns={[
              { key: 'network', label: 'Сеть', width: '18%' },
              { key: 'rangeStart', label: 'Начало диапазона', width: '17%' },
              { key: 'rangeEnd', label: 'Конец диапазона', width: '17%' },
              { key: 'gateway', label: 'Шлюз', width: '15%' },
              { key: 'dns', label: 'DNS серверы', width: '23%' },
            ]}
            data={scopes}
            onAdd={handleAddScope}
            onEdit={handleEditScope}
            onDelete={handleDeleteScope}
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
            <DialogTitle>
              {dialogType === 'scope'
                ? editingScope
                  ? 'Редактирование области DHCP'
                  : 'Добавление области DHCP'
                : editingReservation
                  ? 'Редактирование резервирования'
                  : 'Добавление резервирования'}
            </DialogTitle>
            <DialogDescription>
              {dialogType === 'scope' ? 'При сохранении будет создан бэкап конфигурации' : 'Привязка IP адреса к MAC адресу'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {dialogType === 'scope' ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="network">Сеть</Label>
                    <Input id="network" value={scopeFormData.network} onChange={(e) => setScopeFormData({ ...scopeFormData, network: e.target.value })} placeholder="192.168.1.0" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="netmask">Маска</Label>
                    <Input id="netmask" value={scopeFormData.netmask} onChange={(e) => setScopeFormData({ ...scopeFormData, netmask: e.target.value })} placeholder="255.255.255.0" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="rangeStart">Начало диапазона</Label>
                    <Input id="rangeStart" value={scopeFormData.rangeStart} onChange={(e) => setScopeFormData({ ...scopeFormData, rangeStart: e.target.value })} placeholder="192.168.1.100" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="rangeEnd">Конец диапазона</Label>
                    <Input id="rangeEnd" value={scopeFormData.rangeEnd} onChange={(e) => setScopeFormData({ ...scopeFormData, rangeEnd: e.target.value })} placeholder="192.168.1.200" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="gateway">Шлюз (routers)</Label>
                  <Input id="gateway" value={scopeFormData.gateway} onChange={(e) => setScopeFormData({ ...scopeFormData, gateway: e.target.value })} placeholder="192.168.1.1" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dns">DNS серверы</Label>
                  <Input id="dns" value={scopeFormData.dns} onChange={(e) => setScopeFormData({ ...scopeFormData, dns: e.target.value })} placeholder="192.168.1.1, 8.8.8.8" />
                </div>
              </>
            ) : (
              <>
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
    </>
  )
}
