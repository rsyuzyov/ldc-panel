import { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { DataTable } from './DataTable'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog'
import { api } from '../api/client'
import logger from '../utils/logger'

interface BackupFile {
  filename: string
  type: string
  size: number
  created: string
}

interface BackupSectionProps {
  serverId: string
}

export function BackupSection({ serverId }: BackupSectionProps) {
  const [backups, setBackups] = useState<BackupFile[]>([])
  const [loading, setLoading] = useState(false)
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false)
  const [selectedBackup, setSelectedBackup] = useState<BackupFile | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const loadBackups = async () => {
    try {
      const data = await api.getBackups(serverId)
      setBackups(data)
    } catch (err) {
      logger.error('Failed to load backups', err as Error)
      setBackups([])
    }
  }

  useEffect(() => {
    loadBackups()
  }, [serverId])

  const handleBackupLdif = async () => {
    setLoading(true)
    setMessage(null)
    try {
      await api.backupLdif(serverId)
      setMessage({ type: 'success', text: 'LDIF бэкап создан успешно' })
      loadBackups()
    } catch (err) {
      logger.error('Failed to create LDIF backup', err as Error)
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Ошибка создания бэкапа' })
    } finally {
      setLoading(false)
    }
  }

  const handleBackupDhcp = async () => {
    setLoading(true)
    setMessage(null)
    try {
      await api.backupDhcp(serverId)
      setMessage({ type: 'success', text: 'DHCP бэкап создан успешно' })
      loadBackups()
    } catch (err) {
      logger.error('Failed to create DHCP backup', err as Error)
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Ошибка создания бэкапа' })
    } finally {
      setLoading(false)
    }
  }

  const handleRestore = (backup: BackupFile) => {
    setSelectedBackup(backup)
    setRestoreDialogOpen(true)
  }

  const confirmRestore = async () => {
    if (!selectedBackup) return
    setLoading(true)
    setMessage(null)
    try {
      await api.restoreBackup(serverId, selectedBackup.type, selectedBackup.filename)
      setMessage({ type: 'success', text: 'Бэкап восстановлен успешно' })
      setRestoreDialogOpen(false)
    } catch (err) {
      logger.error('Failed to restore backup', err as Error)
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Ошибка восстановления' })
    } finally {
      setLoading(false)
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const tableData = backups.map((b, i) => ({
    id: i,
    filename: b.filename,
    type: b.type === 'ldif' ? 'LDIF (AD)' : 'DHCP',
    size: formatSize(b.size),
    created: b.created,
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Резервное копирование</h2>
          <p className="text-sm text-gray-600 mt-1">Создание и восстановление бэкапов AD и DHCP</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleBackupLdif} disabled={loading} className="bg-gray-600 hover:bg-gray-700">
            Бэкап LDIF
          </Button>
          <Button onClick={handleBackupDhcp} disabled={loading} variant="outline">
            Бэкап DHCP
          </Button>
        </div>
      </div>

      {message && (
        <div className={`p-3 rounded-md text-sm ${message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {message.text}
        </div>
      )}

      <DataTable
        title="Список бэкапов"
        description="Доступные резервные копии для восстановления"
        columns={[
          { key: 'filename', label: 'Файл', width: '35%' },
          { key: 'type', label: 'Тип', width: '15%' },
          { key: 'size', label: 'Размер', width: '15%' },
          { key: 'created', label: 'Дата создания', width: '25%' },
        ]}
        data={tableData}
        onEdit={(item) => handleRestore(backups[item.id])}
        searchPlaceholder="Поиск бэкапов..."
      />

      <Dialog open={restoreDialogOpen} onOpenChange={setRestoreDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Восстановление из бэкапа</DialogTitle>
            <DialogDescription>Подтверждение восстановления данных</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-gray-700">
              Вы уверены, что хотите восстановить данные из бэкапа <span className="font-medium">{selectedBackup?.filename}</span>?
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Это действие перезапишет текущие данные.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreDialogOpen(false)}>Отмена</Button>
            <Button onClick={confirmRestore} disabled={loading} className="bg-red-600 hover:bg-red-700">
              Восстановить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
