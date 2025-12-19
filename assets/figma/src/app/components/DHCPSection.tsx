import { useState } from 'react';
import { DataTable } from './DataTable';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

interface DHCPScope {
  id: number;
  name: string;
  network: string;
  rangeStart: string;
  rangeEnd: string;
  gateway: string;
  dns: string;
  leaseTime: string;
}

interface DHCPReservation {
  id: number;
  hostname: string;
  mac: string;
  ip: string;
  description: string;
}

const initialScopes: DHCPScope[] = [
  { 
    id: 1, 
    name: 'Офис', 
    network: '192.168.1.0/24', 
    rangeStart: '192.168.1.100', 
    rangeEnd: '192.168.1.200', 
    gateway: '192.168.1.1',
    dns: '192.168.1.10',
    leaseTime: '86400'
  },
  { 
    id: 2, 
    name: 'Гостевая', 
    network: '192.168.2.0/24', 
    rangeStart: '192.168.2.50', 
    rangeEnd: '192.168.2.150', 
    gateway: '192.168.2.1',
    dns: '192.168.1.10',
    leaseTime: '43200'
  },
];

const initialReservations: DHCPReservation[] = [
  { id: 1, hostname: 'printer-01', mac: '00:11:22:33:44:55', ip: '192.168.1.50', description: 'Принтер офис' },
  { id: 2, hostname: 'nas-01', mac: '00:AA:BB:CC:DD:EE', ip: '192.168.1.51', description: 'Сетевое хранилище' },
];

export function DHCPSection() {
  const [scopes, setScopes] = useState<DHCPScope[]>(initialScopes);
  const [reservations, setReservations] = useState<DHCPReservation[]>(initialReservations);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogType, setDialogType] = useState<'scope' | 'reservation'>('scope');
  const [editingScope, setEditingScope] = useState<DHCPScope | null>(null);
  const [editingReservation, setEditingReservation] = useState<DHCPReservation | null>(null);
  const [scopeFormData, setScopeFormData] = useState({
    name: '',
    network: '',
    rangeStart: '',
    rangeEnd: '',
    gateway: '',
    dns: '',
    leaseTime: '86400',
  });
  const [reservationFormData, setReservationFormData] = useState({
    hostname: '',
    mac: '',
    ip: '',
    description: '',
  });

  const handleAddScope = () => {
    setDialogType('scope');
    setEditingScope(null);
    setScopeFormData({ name: '', network: '', rangeStart: '', rangeEnd: '', gateway: '', dns: '', leaseTime: '86400' });
    setDialogOpen(true);
  };

  const handleEditScope = (scope: DHCPScope) => {
    setDialogType('scope');
    setEditingScope(scope);
    setScopeFormData({
      name: scope.name,
      network: scope.network,
      rangeStart: scope.rangeStart,
      rangeEnd: scope.rangeEnd,
      gateway: scope.gateway,
      dns: scope.dns,
      leaseTime: scope.leaseTime,
    });
    setDialogOpen(true);
  };

  const handleDeleteScope = (scope: DHCPScope) => {
    if (confirm(`Удалить DHCP область ${scope.name}?`)) {
      setScopes(scopes.filter((s) => s.id !== scope.id));
    }
  };

  const handleAddReservation = () => {
    setDialogType('reservation');
    setEditingReservation(null);
    setReservationFormData({ hostname: '', mac: '', ip: '', description: '' });
    setDialogOpen(true);
  };

  const handleEditReservation = (reservation: DHCPReservation) => {
    setDialogType('reservation');
    setEditingReservation(reservation);
    setReservationFormData({
      hostname: reservation.hostname,
      mac: reservation.mac,
      ip: reservation.ip,
      description: reservation.description,
    });
    setDialogOpen(true);
  };

  const handleDeleteReservation = (reservation: DHCPReservation) => {
    if (confirm(`Удалить резервирование для ${reservation.hostname}?`)) {
      setReservations(reservations.filter((r) => r.id !== reservation.id));
    }
  };

  const handleSave = () => {
    if (dialogType === 'scope') {
      if (editingScope) {
        setScopes(scopes.map((s) => (s.id === editingScope.id ? { ...editingScope, ...scopeFormData } : s)));
      } else {
        const newScope: DHCPScope = {
          id: Math.max(...scopes.map((s) => s.id), 0) + 1,
          ...scopeFormData,
        };
        setScopes([...scopes, newScope]);
      }
    } else {
      if (editingReservation) {
        setReservations(reservations.map((r) => (r.id === editingReservation.id ? { ...editingReservation, ...reservationFormData } : r)));
      } else {
        const newReservation: DHCPReservation = {
          id: Math.max(...reservations.map((r) => r.id), 0) + 1,
          ...reservationFormData,
        };
        setReservations([...reservations, newReservation]);
      }
    }
    setDialogOpen(false);
  };

  return (
    <>
      <Tabs defaultValue="scopes" className="w-full">
        <TabsList>
          <TabsTrigger value="scopes">Области DHCP</TabsTrigger>
          <TabsTrigger value="reservations">Резервирования</TabsTrigger>
        </TabsList>
        
        <TabsContent value="scopes" className="mt-4">
          <DataTable
            title="Области DHCP"
            description="Управление областями DHCP. Настройка диапазонов IP адресов, шлюзов и DNS серверов."
            columns={[
              { key: 'name', label: 'Название', width: '15%' },
              { key: 'network', label: 'Сеть', width: '15%' },
              { key: 'rangeStart', label: 'Начало', width: '15%' },
              { key: 'rangeEnd', label: 'Конец', width: '15%' },
              { key: 'gateway', label: 'Шлюз', width: '12%' },
              { key: 'dns', label: 'DNS', width: '12%' },
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
            description="Статические привязки IP адресов к MAC адресам устройств."
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
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogType === 'scope'
                ? editingScope ? 'Редактирование области DHCP' : 'Добавление области DHCP'
                : editingReservation ? 'Редактирование резервирования' : 'Добавление резервирования'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {dialogType === 'scope' ? (
              <>
                <div className="space-y-2">
                  <Label htmlFor="name">Название</Label>
                  <Input
                    id="name"
                    value={scopeFormData.name}
                    onChange={(e) => setScopeFormData({ ...scopeFormData, name: e.target.value })}
                    placeholder="Офис"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="network">Сеть</Label>
                  <Input
                    id="network"
                    value={scopeFormData.network}
                    onChange={(e) => setScopeFormData({ ...scopeFormData, network: e.target.value })}
                    placeholder="192.168.1.0/24"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="rangeStart">Начало диапазона</Label>
                    <Input
                      id="rangeStart"
                      value={scopeFormData.rangeStart}
                      onChange={(e) => setScopeFormData({ ...scopeFormData, rangeStart: e.target.value })}
                      placeholder="192.168.1.100"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="rangeEnd">Конец диапазона</Label>
                    <Input
                      id="rangeEnd"
                      value={scopeFormData.rangeEnd}
                      onChange={(e) => setScopeFormData({ ...scopeFormData, rangeEnd: e.target.value })}
                      placeholder="192.168.1.200"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="gateway">Шлюз</Label>
                    <Input
                      id="gateway"
                      value={scopeFormData.gateway}
                      onChange={(e) => setScopeFormData({ ...scopeFormData, gateway: e.target.value })}
                      placeholder="192.168.1.1"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dns">DNS сервер</Label>
                    <Input
                      id="dns"
                      value={scopeFormData.dns}
                      onChange={(e) => setScopeFormData({ ...scopeFormData, dns: e.target.value })}
                      placeholder="192.168.1.10"
                    />
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="hostname">Имя хоста</Label>
                  <Input
                    id="hostname"
                    value={reservationFormData.hostname}
                    onChange={(e) => setReservationFormData({ ...reservationFormData, hostname: e.target.value })}
                    placeholder="printer-01"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="mac">MAC адрес</Label>
                  <Input
                    id="mac"
                    value={reservationFormData.mac}
                    onChange={(e) => setReservationFormData({ ...reservationFormData, mac: e.target.value })}
                    placeholder="00:11:22:33:44:55"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ip">IP адрес</Label>
                  <Input
                    id="ip"
                    value={reservationFormData.ip}
                    onChange={(e) => setReservationFormData({ ...reservationFormData, ip: e.target.value })}
                    placeholder="192.168.1.50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Описание</Label>
                  <Input
                    id="description"
                    value={reservationFormData.description}
                    onChange={(e) => setReservationFormData({ ...reservationFormData, description: e.target.value })}
                    placeholder="Принтер офис"
                  />
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
  );
}
