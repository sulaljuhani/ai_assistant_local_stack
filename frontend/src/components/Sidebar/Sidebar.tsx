import { Plus, Settings, X } from 'lucide-react';
import { ConversationList } from './ConversationList';
import { useChat } from '../../contexts/ChatContext';

interface SidebarProps {
  onOpenSettings: () => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onOpenSettings,
  isOpen = true,
  onClose,
}) => {
  const {
    conversations,
    currentConversation,
    createNewConversation,
    switchConversation,
    deleteConversation,
  } = useChat();

  const handleNewChat = () => {
    createNewConversation();
    onClose?.();
  };

  const handleSelectConversation = (id: string) => {
    switchConversation(id);
    onClose?.();
  };

  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && onClose && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
          fixed md:relative inset-y-0 left-0 z-50
          w-64 bg-bg-primary border-r border-border flex flex-col
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-lg font-semibold text-text-primary">AI Stack</h1>
            <div className="flex items-center gap-2">
              <button
                onClick={onOpenSettings}
                className="p-2 rounded-lg hover:bg-bg-hover transition-colors"
                aria-label="Settings"
              >
                <Settings className="w-5 h-5 text-text-secondary" />
              </button>
              {/* Close button for mobile */}
              {onClose && (
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-bg-hover transition-colors md:hidden"
                  aria-label="Close menu"
                >
                  <X className="w-5 h-5 text-text-secondary" />
                </button>
              )}
            </div>
          </div>

          {/* New Chat Button */}
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5
                     bg-accent-green hover:bg-accent-green-hover rounded-lg
                     text-white font-medium transition-colors min-h-[44px]"
          >
            <Plus className="w-5 h-5" />
            New Chat
          </button>
        </div>

        {/* Conversations List */}
        <ConversationList
          conversations={conversations}
          currentConversationId={currentConversation?.id || null}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={deleteConversation}
        />

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <p className="text-xs text-text-secondary text-center">
            {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
    </>
  );
};
