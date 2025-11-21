import { Settings } from 'lucide-react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { useChat } from '../../contexts/ChatContext';

interface ChatBoxProps {
  onOpenSettings?: () => void;
}

export const ChatBox: React.FC<ChatBoxProps> = ({ onOpenSettings }) => {
  const { currentConversation, sendMessage, isSending } = useChat();

  const handleSend = async (message: string) => {
    await sendMessage(message);
  };

  // Show empty state if no conversation
  if (!currentConversation) {
    return (
      <div className="flex-1 flex flex-col bg-bg-secondary">
        {/* Header with settings button */}
        {onOpenSettings && (
          <div className="flex items-center justify-end px-4 py-3 border-b border-border bg-bg-secondary">
            <button
              onClick={onOpenSettings}
              className="p-2 rounded-lg hover:bg-bg-hover transition-colors"
              aria-label="Settings"
              title="Settings"
            >
              <Settings className="w-5 h-5 text-text-secondary hover:text-text-primary transition-colors" />
            </button>
          </div>
        )}

        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              Welcome to AI Stack
            </h2>
            <p className="text-text-secondary">
              Create a new chat to get started
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-bg-secondary">
      {/* Header with settings button */}
      {onOpenSettings && (
        <div className="flex items-center justify-end px-4 py-3 border-b border-border bg-bg-secondary">
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg hover:bg-bg-hover transition-colors"
            aria-label="Settings"
            title="Settings"
          >
            <Settings className="w-5 h-5 text-text-secondary hover:text-text-primary transition-colors" />
          </button>
        </div>
      )}

      {/* Messages area */}
      <MessageList
        messages={currentConversation.messages}
        isLoading={isSending}
      />

      {/* Input area */}
      <MessageInput
        onSend={handleSend}
        disabled={false}
        isLoading={isSending}
      />
    </div>
  );
};
