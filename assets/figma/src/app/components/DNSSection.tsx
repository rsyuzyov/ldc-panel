import { useState } from 'react';
import { DataTable } from './DataTable';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface DNSRecord {
  id: number;
  name: string;
  type: string;
  value: string;
  ttl: string;
  zone: string;
}

const initialRecords: DNSRecord[] = [
  { id: 1, name: 'dc1', type: 'A', value: '192.168.1.10', ttl: '3600', zone: 'domain.local' },
  { id: 2, name: 'dc2', type: 'A', value: '192.168.1.11', ttl: '3600', zone: 'domain.local' },
  { id: 3, name: 'www', type: 'CNAME', value: 'web.domain.local', ttl: '3600', zone: 'domain.local' },
  { id: 4, name: '@', type: 'MX', value: '10 mail.domain.local', ttl: '3600', zone: 'domain.local' },
  { id: 5, name: '_ldap._tcp', type: 'SRV', value: '0 100 389 dc1.domain.local', ttl: '3600', zone: 'domain.local' },
];

export function DNSSection() {
  const [records, setRecords] = useState<DNSRecord[]>(initialRecords);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<DNSRecord | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    type: 'A',
    value: '',
    ttl: '3600',
    zone: 'domain.local',
  });

  const handleAdd = () => {
    setEditingRecord(null);
    setFormData({ name: '', type: 'A', value: '', ttl: '3600', zone: 'domain.local' });
    setDialogOpen(true);
  };

  const handleEdit = (record: DNSRecord) => {
    setEditingRecord(record);
    setFormData({
      name: record.name,
      type: record.type,
      value: record.value,
      ttl: record.ttl,
      zone: record.zone,
    });
    setDialogOpen(true);
  };

  const handleDelete = (record: DNSRecord) => {
    if (confirm(`Удалить DNS запись ${record.name} (${record.type})?`)) {
      setRecords(records.filter((r) => r.id !== record.id));
    }
  };

  const handleSave = () => {
    if (editingRecord) {
      setRecords(
        records.map((r) =>
          r.id === editingRecord.id ? { ...editingRecord, ...formData } : r
        )
      );
    } else {
      const newRecord: DNSRecord = {
        id: Math.max(...records.map((r) => r.id), 0) + 1,
        ...formData,
      };
      setRecords([...records, newRecord]);
    }
    setDialogOpen(false);
  };

  return (
    <>
      <DataTable
        title="DNS записи"
        description="Управление DNS записями. Создание, редактирование и удаление A, AAAA, CNAME, MX, SRV и других записей."
        columns={[
          { key: 'name', label: 'Имя', width: '20%' },
          { key: 'type', label: 'Тип', width: '10%' },
          { key: 'value', label: 'Значение', width: '30%' },
          { key: 'ttl', label: 'TTL', width: '10%' },
          { key: 'zone', label: 'Зона', width: '20%' },
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
            <DialogTitle>
              {editingRecord ? 'Редактирование DNS записи' : 'Добавление DNS записи'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="zone">Зона</Label>
              <Input
                id="zone"
                value={formData.zone}
                onChange={(e) => setFormData({ ...formData, zone: e.target.value })}
                placeholder="domain.local"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Имя записи</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="www"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Тип записи</Label>
              <Select value={formData.type} onValueChange={(value) => setFormData({ ...formData, type: value })}>
                <SelectTrigger id="type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="A">A</SelectItem>
                  <SelectItem value="AAAA">AAAA</SelectItem>
                  <SelectItem value="CNAME">CNAME</SelectItem>
                  <SelectItem value="MX">MX</SelectItem>
                  <SelectItem value="TXT">TXT</SelectItem>
                  <SelectItem value="SRV">SRV</SelectItem>
                  <SelectItem value="PTR">PTR</SelectItem>
                  <SelectItem value="NS">NS</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="value">Значение</Label>
              <Input
                id="value"
                value={formData.value}
                onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                placeholder="192.168.1.10"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ttl">TTL (секунды)</Label>
              <Input
                id="ttl"
                value={formData.ttl}
                onChange={(e) => setFormData({ ...formData, ttl: e.target.value })}
                placeholder="3600"
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
