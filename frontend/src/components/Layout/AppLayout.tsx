import { useState } from 'react';
import { Sidebar } from '../Sidebar/Sidebar';
import { ChatBox } from '../Chat/ChatBox';
import { SettingsModal } from '../Settings/SettingsModal';
import { useChat } from '../../contexts/ChatContext';
import { AlertCircle } from 'lucide-react';

export const AppLayout: React.FC = () => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const { error, clearError } = useChat();

  return (
    <div className="flex h-screen w-screen bg-bg-primary">
      {/* Sidebar */}
      <Sidebar onOpenSettings={() => setIsSettingsOpen(true)} />

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Error banner */}
        {error && (
          <div className="bg-error/10 border-b border-error/20 px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-error" />
              <p className="text-sm text-error">{error}</p>
            </div>
            <button
              onClick={clearError}
              className="text-xs text-error hover:text-error/80 font-medium"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Chat area */}
        <ChatBox />
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
};
