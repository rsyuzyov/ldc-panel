import { useState } from 'react';
import { DataTable } from './DataTable';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';

interface Server {
  id: number;
  name: string;
  ip: string;
  status: string;
  role: string;
  version: string;
}

const initialServers: Server[] = [
  { id: 1, name: 'DC1.domain.local', ip: '192.168.1.10', status: 'Активен', role: 'Primary DC', version: 'Samba 4.18' },
  { id: 2, name: 'DC2.domain.local', ip: '192.168.1.11', status: 'Активен', role: 'Replica DC', version: 'Samba 4.18' },
];

export function ServersSection() {
  const [servers, setServers] = useState<Server[]>(initialServers);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    ip: '',
    status: '',
    role: '',
    version: '',
  });

  const handleAdd = () => {
    setEditingServer(null);
    setFormData({ name: '', ip: '', status: 'Активен', role: '', version: '' });
    setDialogOpen(true);
  };

  const handleEdit = (server: Server) => {
    setEditingServer(server);
    setFormData({
      name: server.name,
      ip: server.ip,
      status: server.status,
      role: server.role,
      version: server.version,
    });
    setDialogOpen(true);
  };

  const handleDelete = (server: Server) => {
    if (confirm(`Удалить сервер ${server.name}?`)) {
      setServers(servers.filter((s) => s.id !== server.id));
    }
  };

  const handleSave = () => {
    if (editingServer) {
      setServers(
        servers.map((s) =>
          s.id === editingServer.id ? { ...editingServer, ...formData } : s
        )
      );
    } else {
      const newServer: Server = {
        id: Math.max(...servers.map((s) => s.id), 0) + 1,
        ...formData,
      };
      setServers([...servers, newServer]);
    }
    setDialogOpen(false);
  };

  return (
    <>
      <DataTable
        title="Серверы"
        description="Управление контроллерами домена Samba AD. Просмотр статуса, добавление и удаление серверов."
        columns={[
          { key: 'name', label: 'Имя сервера', width: '25%' },
          { key: 'ip', label: 'IP адрес', width: '15%' },
          { key: 'status', label: 'Статус', width: '15%' },
          { key: 'role', label: 'Роль', width: '20%' },
          { key: 'version', label: 'Версия', width: '15%' },
        ]}
        data={servers}
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        searchPlaceholder="Поиск серверов..."
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingServer ? 'Редактирование сервера' : 'Добавление сервера'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Имя сервера</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="DC1.domain.local"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ip">IP адрес</Label>
              <Input
                id="ip"
                value={formData.ip}
                onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
                placeholder="192.168.1.10"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Роль</Label>
              <Input
                id="role"
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                placeholder="Primary DC"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="version">Версия</Label>
              <Input
                id="version"
                value={formData.version}
                onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                placeholder="Samba 4.18"
              />
            </div>
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
