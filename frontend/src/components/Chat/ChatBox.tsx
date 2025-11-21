import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { useChat } from '../../contexts/ChatContext';

export const ChatBox: React.FC = () => {
  const { currentConversation, sendMessage, isSending } = useChat();

  const handleSend = async (message: string) => {
    await sendMessage(message);
  };

  // Show empty state if no conversation
  if (!currentConversation) {
    return (
      <div className="flex-1 flex flex-col bg-bg-secondary">
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
