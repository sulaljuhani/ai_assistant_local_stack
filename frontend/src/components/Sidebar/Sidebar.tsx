import { Plus, Settings } from 'lucide-react';
import { ConversationList } from './ConversationList';
import { useChat } from '../../contexts/ChatContext';

interface SidebarProps {
  onOpenSettings: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onOpenSettings }) => {
  const {
    conversations,
    currentConversation,
    createNewConversation,
    switchConversation,
    deleteConversation,
  } = useChat();

  return (
    <div className="w-64 bg-bg-primary border-r border-border flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-semibold text-text-primary">AI Stack</h1>
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg hover:bg-bg-hover transition-colors"
            aria-label="Settings"
          >
            <Settings className="w-5 h-5 text-text-secondary" />
          </button>
        </div>

        {/* New Chat Button */}
        <button
          onClick={createNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5
                   bg-accent-green hover:bg-accent-green-hover rounded-lg
                   text-white font-medium transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Chat
        </button>
      </div>

      {/* Conversations List */}
      <ConversationList
        conversations={conversations}
        currentConversationId={currentConversation?.id || null}
        onSelectConversation={switchConversation}
        onDeleteConversation={deleteConversation}
      />

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <p className="text-xs text-text-secondary text-center">
          {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
};
