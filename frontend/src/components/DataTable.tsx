import { useState, useMemo } from 'react'
import { Search, Plus, Pencil, Trash2, ChevronUp, ChevronDown } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'

export interface Column {
  key: string
  label: string
  width?: string
}

export interface CustomAction<T> {
  icon: React.ReactNode
  title: string
  onClick: (item: T) => void
  className?: string
}

export interface DataTableProps<T> {
  title: string
  description: string
  columns: Column[]
  data: T[]
  onAdd?: () => void
  onEdit?: (item: T) => void
  onDelete?: (item: T) => void
  customActions?: CustomAction<T>[]
  searchPlaceholder?: string
}

type SortDirection = 'asc' | 'desc'

export function DataTable<T extends { id: string | number }>({
  title,
  description,
  columns,
  data,
  onAdd,
  onEdit,
  onDelete,
  customActions,
  searchPlaceholder = 'Поиск...',
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = useState('')
  const [sortKey, setSortKey] = useState<string>(columns[0]?.key || '')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDirection('asc')
    }
  }

  const sortedData = useMemo(() => {
    const searchLower = searchQuery.toLowerCase()
    const filtered = data.filter((item) =>
      Object.values(item).some((value) => String(value).toLowerCase().includes(searchLower))
    )

    if (!sortKey) return filtered

    return [...filtered].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey]
      const bVal = (b as Record<string, unknown>)[sortKey]
      const aStr = String(aVal ?? '').toLowerCase()
      const bStr = String(bVal ?? '').toLowerCase()

      if (sortDirection === 'asc') {
        return aStr.localeCompare(bStr, 'ru', { numeric: true })
      }
      return bStr.localeCompare(aStr, 'ru', { numeric: true })
    })
  }, [data, searchQuery, sortKey, sortDirection])

  const showActions = onAdd || onEdit || onDelete || (customActions && customActions.length > 0)

  return (
    <div className="space-y-4">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-gray-900 mb-1">{title}</h2>
        <p className="text-sm text-gray-600">{description}</p>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            type="search"
            role="searchbox"
            name="table-filter"
            placeholder={searchPlaceholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
            autoComplete="off"
            data-form-type="other"
            data-lpignore="true"
          />
        </div>
        {onAdd && (
          <Button onClick={onAdd} className="bg-blue-600 hover:bg-blue-700">
            <Plus className="w-4 h-4 mr-2" />
            Добавить
          </Button>
        )}
      </div>

      <div className="border border-gray-200 rounded-lg overflow-hidden flex flex-col" style={{ maxHeight: 'calc(100vh - 300px)' }}>
        <div className="overflow-x-auto flex-shrink-0">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className="px-4 py-3 text-left text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-100 select-none"
                    style={{ width: column.width }}
                    onClick={() => handleSort(column.key)}
                  >
                    <div className="flex items-center gap-1">
                      {column.label}
                      {sortKey === column.key && (
                        sortDirection === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                      )}
                    </div>
                  </th>
                ))}
                {showActions && <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 w-32">Действия</th>}
              </tr>
            </thead>
          </table>
        </div>
        <div className="overflow-y-auto overflow-x-auto flex-1">
          <table className="w-full">
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedData.length === 0 ? (
                <tr>
                  <td colSpan={columns.length + (showActions ? 1 : 0)} className="px-4 py-8 text-center text-gray-500">
                    {searchQuery ? 'Ничего не найдено' : 'Нет данных'}
                  </td>
                </tr>
              ) : (
                sortedData.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                    {columns.map((column) => (
                      <td key={column.key} className="px-4 py-3 text-sm text-gray-900" style={{ width: column.width }}>
                        {String((item as Record<string, unknown>)[column.key] ?? '')}
                      </td>
                    ))}
                    {showActions && (
                      <td className="px-4 py-3 w-32">
                        <div className="flex items-center gap-2">
                          {customActions?.map((action, idx) => (
                            <button key={idx} onClick={() => action.onClick(item)} className={action.className || "p-1 text-gray-600 hover:bg-gray-50 rounded transition-colors"} title={action.title}>
                              {action.icon}
                            </button>
                          ))}
                          {onEdit && (
                            <button onClick={() => onEdit(item)} className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Редактировать">
                              <Pencil className="w-4 h-4" />
                            </button>
                          )}
                          {onDelete && (
                            <button onClick={() => onDelete(item)} className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors" title="Удалить">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="text-sm text-gray-600">
        Всего записей: {sortedData.length} {searchQuery && `из ${data.length}`}
      </div>
    </div>
  )
}
