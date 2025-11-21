import { useState } from 'react';
import { MessageSquare, Trash2 } from 'lucide-react';
import type { Conversation } from '../../types/chat';
import { formatRelativeTime } from '../../utils/time';

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onClick: () => void;
  onDelete: (id: string) => void;
}

export const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  isActive,
  onClick,
  onDelete,
}) => {
  const [showDelete, setShowDelete] = useState(false);

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Delete this conversation?')) {
      onDelete(conversation.id);
    }
  };

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
                 ${isActive
                   ? 'bg-bg-hover border-l-2 border-accent-green'
                   : 'hover:bg-bg-hover border-l-2 border-transparent'
                 }`}
    >
      {/* Icon */}
      <MessageSquare className="w-4 h-4 text-text-secondary flex-shrink-0" />

      {/* Content */}
      <div className="flex-1 min-w-0 text-left">
        <p className={`text-sm truncate ${
          isActive ? 'text-text-primary' : 'text-text-secondary'
        }`}>
          {conversation.title}
        </p>
        <p className="text-xs text-text-secondary">
          {formatRelativeTime(conversation.updated_at)}
        </p>
      </div>

      {/* Delete button (show on hover) */}
      {showDelete && (
        <button
          onClick={handleDelete}
          className="flex-shrink-0 p-1 rounded hover:bg-bg-primary transition-colors"
          aria-label="Delete conversation"
        >
          <Trash2 className="w-4 h-4 text-text-secondary hover:text-error" />
        </button>
      )}
    </button>
  );
};
