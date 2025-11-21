import { ConversationItem } from './ConversationItem';
import type { Conversation } from '../../types/chat';

interface ConversationListProps {
  conversations: Conversation[];
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  currentConversationId,
  onSelectConversation,
  onDeleteConversation,
}) => {
  if (conversations.length === 0) {
    return (
      <div className="px-3 py-6 text-center">
        <p className="text-sm text-text-secondary">
          No conversations yet
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin px-2 py-2">
      <div className="flex flex-col gap-1">
        {conversations.map((conversation) => (
          <ConversationItem
            key={conversation.id}
            conversation={conversation}
            isActive={conversation.id === currentConversationId}
            onClick={() => onSelectConversation(conversation.id)}
            onDelete={onDeleteConversation}
          />
        ))}
      </div>
    </div>
  );
};
