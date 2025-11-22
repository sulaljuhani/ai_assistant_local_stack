import { useState } from 'react';
import { Menu } from 'lucide-react';
import { Sidebar } from '../Sidebar/Sidebar';
import { ChatBox } from '../Chat/ChatBox';
import { SettingsModal } from '../Settings/SettingsModal';

export const AppLayout: React.FC = () => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-screen bg-bg-primary overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        onOpenSettings={() => setIsSettingsOpen(true)}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header with menu button */}
        <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-border bg-bg-secondary">
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-bg-hover transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Open menu"
          >
            <Menu className="w-6 h-6 text-text-primary" />
          </button>
          <h1 className="text-lg font-semibold text-text-primary">AI Stack</h1>
          <div className="w-11" /> {/* Spacer for centering */}
        </div>

        <ChatBox onOpenSettings={() => setIsSettingsOpen(true)} />
      </div>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <SettingsModal
          onClose={() => setIsSettingsOpen(false)}
        />
      )}
    </div>
  );
};
