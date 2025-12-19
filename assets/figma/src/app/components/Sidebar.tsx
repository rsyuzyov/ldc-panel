import { Server, Users, Network, Settings, Shield, ChevronRight, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import type { SectionType } from '../App';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface SidebarProps {
  activeSection: SectionType;
  onSectionChange: (section: SectionType) => void;
}

export function Sidebar({ activeSection, onSectionChange }: SidebarProps) {
  const [currentServer, setCurrentServer] = useState('dc1');

  const menuItems = [
    { id: 'users' as SectionType, label: 'AD', icon: Users },
    { id: 'dns' as SectionType, label: 'DNS', icon: Network },
    { id: 'dhcp' as SectionType, label: 'DHCP', icon: Settings },
    { id: 'gpo' as SectionType, label: 'GPO', icon: Shield },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex-shrink-0">
      <div className="p-4 border-b border-gray-200">
        <h1 className="font-semibold text-gray-900">LDC Panel</h1>
      </div>
      
      <div className="p-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs text-gray-600">Текущий сервер</label>
          <button
            onClick={() => onSectionChange('servers')}
            className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
            title="Управление серверами"
          >
            <Server className="w-4 h-4" />
          </button>
        </div>
        <Select value={currentServer} onValueChange={setCurrentServer}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="dc1">DC1.domain.local</SelectItem>
            <SelectItem value="dc2">DC2.domain.local</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      <nav className="p-2">
        {menuItems.map((item) => (
          <div key={item.id}>
            <button
              onClick={() => onSectionChange(item.id)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-md transition-colors ${
                activeSection === item.id
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <item.icon className="w-4 h-4" />
              <span>{item.label}</span>
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}