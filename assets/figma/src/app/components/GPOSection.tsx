import { useState } from 'react';
import { DataTable } from './DataTable';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface GPO {
  id: number;
  name: string;
  status: string;
  linkedTo: string;
  modifiedDate: string;
  description: string;
}

const initialGPOs: GPO[] = [
  { 
    id: 1, 
    name: 'Default Domain Policy', 
    status: 'Включена', 
    linkedTo: 'domain.local', 
    modifiedDate: '2025-12-15 14:30',
    description: 'Стандартная политика домена'
  },
  { 
    id: 2, 
    name: 'Password Policy', 
    status: 'Включена', 
    linkedTo: 'domain.local', 
    modifiedDate: '2025-12-10 09:15',
    description: 'Политика паролей - минимум 8 символов, срок действия 90 дней'
  },
  { 
    id: 3, 
    name: 'Workstation Settings', 
    status: 'Включена', 
    linkedTo: 'OU=Workstations', 
    modifiedDate: '2025-12-01 16:45',
    description: 'Настройки рабочих станций - блокировка USB, обновления Windows'
  },
  { 
    id: 4, 
    name: 'User Restrictions', 
    status: 'Отключена', 
    linkedTo: 'OU=Users', 
    modifiedDate: '2025-11-25 11:20',
    description: 'Ограничения для пользователей - отключение командной строки'
  },
];

export function GPOSection() {
  const [gpos, setGpos] = useState<GPO[]>(initialGPOs);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingGPO, setEditingGPO] = useState<GPO | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    status: 'Включена',
    linkedTo: '',
    modifiedDate: '',
    description: '',
  });

  const handleAdd = () => {
    setEditingGPO(null);
    const now = new Date();
    const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    setFormData({ name: '', status: 'Включена', linkedTo: '', modifiedDate: dateStr, description: '' });
    setDialogOpen(true);
  };

  const handleEdit = (gpo: GPO) => {
    setEditingGPO(gpo);
    setFormData({
      name: gpo.name,
      status: gpo.status,
      linkedTo: gpo.linkedTo,
      modifiedDate: gpo.modifiedDate,
      description: gpo.description,
    });
    setDialogOpen(true);
  };

  const handleDelete = (gpo: GPO) => {
    if (confirm(`Удалить групповую политику ${gpo.name}?`)) {
      setGpos(gpos.filter((g) => g.id !== gpo.id));
    }
  };

  const handleSave = () => {
    const now = new Date();
    const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    if (editingGPO) {
      setGpos(
        gpos.map((g) =>
          g.id === editingGPO.id ? { ...editingGPO, ...formData, modifiedDate: dateStr } : g
        )
      );
    } else {
      const newGPO: GPO = {
        id: Math.max(...gpos.map((g) => g.id), 0) + 1,
        ...formData,
        modifiedDate: dateStr,
      };
      setGpos([...gpos, newGPO]);
    }
    setDialogOpen(false);
  };

  return (
    <>
      <DataTable
        title="Групповые политики (GPO)"
        description="Управление групповыми политиками Active Directory. Создание, редактирование и применение политик к объектам домена."
        columns={[
          { key: 'name', label: 'Название политики', width: '25%' },
          { key: 'status', label: 'Статус', width: '12%' },
          { key: 'linkedTo', label: 'Привязана к', width: '20%' },
          { key: 'modifiedDate', label: 'Дата изменения', width: '18%' },
          { key: 'description', label: 'Описание', width: '25%' },
        ]}
        data={gpos}
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        searchPlaceholder="Поиск политик..."
      />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingGPO ? 'Редактирование групповой политики' : 'Создание групповой политики'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Название политики</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="My Policy"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Статус</Label>
              <Select value={formData.status} onValueChange={(value) => setFormData({ ...formData, status: value })}>
                <SelectTrigger id="status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Включена">Включена</SelectItem>
                  <SelectItem value="Отключена">Отключена</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="linkedTo">Привязана к</Label>
              <Input
                id="linkedTo"
                value={formData.linkedTo}
                onChange={(e) => setFormData({ ...formData, linkedTo: e.target.value })}
                placeholder="domain.local или OU=Workstations,DC=domain,DC=local"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Описание</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Описание политики и её назначение"
                rows={4}
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
