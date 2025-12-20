import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
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
  const [open, setOpen] = useState(false)
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({})
  const containerRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node
      const clickedInContainer = containerRef.current?.contains(target)
      const clickedInDropdown = dropdownRef.current?.contains(target)
      if (!clickedInContainer && !clickedInDropdown) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect()
      setDropdownStyle({
        position: 'fixed',
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width,
        zIndex: 9999,
      })
    }
  }, [open])

  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value))
    } else {
      onChange([...selected, value])
    }
  }

  const selectedLabels = options.filter((o) => selected.includes(o.value)).map((o) => o.label)

  const dropdown = open && !loading && (
    <div
      ref={dropdownRef}
      style={dropdownStyle}
      className="bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto"
      onMouseDown={(e) => e.stopPropagation()}
    >
      {options.length === 0 ? (
        <div className="px-3 py-2 text-sm text-gray-500">Нет доступных групп</div>
      ) : (
        options.map((option) => (
          <div
            key={option.value}
            onClick={(e) => {
              e.stopPropagation()
              toggle(option.value)
            }}
            className="flex items-center px-3 py-2 cursor-pointer hover:bg-gray-50"
          >
            <div
              className={`w-4 h-4 mr-2 border rounded flex items-center justify-center flex-shrink-0 ${
                selected.includes(option.value) ? 'bg-blue-600 border-blue-600' : 'border-gray-300'
              }`}
            >
              {selected.includes(option.value) && <Check className="w-3 h-3 text-white" />}
            </div>
            <span className="text-sm text-gray-700">{option.label}</span>
          </div>
        ))
      )}
    </div>
  )

  return (
    <div ref={containerRef} className="relative w-full min-w-0">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <span className="flex-1 min-w-0 truncate text-gray-700">
          {loading ? 'Загрузка...' : selectedLabels.length > 0 ? selectedLabels.join(', ') : placeholder}
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`} />
      </button>
      {dropdown && createPortal(dropdown, document.body)}
    </div>
  )
}
