import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Check, ChevronDown } from 'lucide-react'

interface Option {
  value: string
  label: string
}

interface MultiSelectProps {
  options: Option[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  loading?: boolean
}

export function MultiSelect({ options, selected, onChange, placeholder = 'Выберите...', loading }: MultiSelectProps) {
  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value))
    } else {
      onChange([...selected, value])
    }
  }

  const selectedLabels = options.filter((o) => selected.includes(o.value)).map((o) => o.label)

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className="w-full flex items-center gap-2 px-3 py-2 text-left bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <span className="flex-1 min-w-0 truncate text-gray-700">
            {loading ? 'Загрузка...' : selectedLabels.length > 0 ? selectedLabels.join(', ') : placeholder}
          </span>
          <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto z-[9999]"
          sideOffset={4}
          align="start"
          style={{ minWidth: 'var(--radix-dropdown-menu-trigger-width)' }}
        >
          {loading ? (
            <div className="px-3 py-2 text-sm text-gray-500">Загрузка...</div>
          ) : options.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500">Нет доступных групп</div>
          ) : (
            [...options].sort((a, b) => a.label.localeCompare(b.label, 'ru')).map((option) => (
              <DropdownMenu.CheckboxItem
                key={option.value}
                checked={selected.includes(option.value)}
                onCheckedChange={() => toggle(option.value)}
                onSelect={(e) => e.preventDefault()}
                className="flex items-center px-3 py-2 cursor-pointer hover:bg-gray-50 outline-none"
              >
                <div
                  className={`w-4 h-4 mr-2 border rounded flex items-center justify-center flex-shrink-0 ${
                    selected.includes(option.value) ? 'bg-blue-600 border-blue-600' : 'border-gray-300'
                  }`}
                >
                  {selected.includes(option.value) && <Check className="w-3 h-3 text-white" />}
                </div>
                <span className="text-sm text-gray-700">{option.label}</span>
              </DropdownMenu.CheckboxItem>
            ))
          )}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
