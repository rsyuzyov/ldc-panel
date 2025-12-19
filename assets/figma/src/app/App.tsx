import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ServersSection } from './components/ServersSection';
import { UsersSection } from './components/UsersSection';
import { DNSSection } from './components/DNSSection';
import { DHCPSection } from './components/DHCPSection';
import { GPOSection } from './components/GPOSection';

export type SectionType = 'servers' | 'users' | 'dns' | 'dhcp' | 'gpo';

export default function App() {
  const [activeSection, setActiveSection] = useState<SectionType>('servers');

  const renderSection = () => {
    switch (activeSection) {
      case 'servers':
        return <ServersSection />;
      case 'users':
        return <UsersSection />;
      case 'dns':
        return <DNSSection />;
      case 'dhcp':
        return <DHCPSection />;
      case 'gpo':
        return <GPOSection />;
      default:
        return <ServersSection />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar activeSection={activeSection} onSectionChange={setActiveSection} />
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          {renderSection()}
        </div>
      </main>
    </div>
  );
}
