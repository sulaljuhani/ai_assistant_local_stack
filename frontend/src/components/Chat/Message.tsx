import { User, Bot } from 'lucide-react';
import type { Message as MessageType } from '../../types/chat';
import { formatTime } from '../../utils/time';
import { AgentBadge } from './AgentBadge';

interface MessageProps {
  message: MessageType;
}

export const Message: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}
    >
      {/* Avatar - left side for assistant */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bg-hover flex items-center justify-center">
          <Bot className="w-5 h-5 text-text-secondary" />
        </div>
      )}

      {/* Message content */}
      <div className={`flex flex-col max-w-[70%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Agent badge above message for assistant */}
        {!isUser && message.agent && (
          <div className="mb-1.5">
            <AgentBadge agent={message.agent} size="sm" />
          </div>
        )}

        {/* Message bubble */}
        <div
          className={`rounded-lg px-4 py-3 shadow-sm ${
            isUser
              ? 'bg-bg-primary text-text-primary'
              : 'bg-bg-hover text-text-primary'
          }`}
        >
          <p className="whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
        </div>

        {/* Timestamp */}
        <div className="flex items-center gap-2 mt-1 px-1">
          <span className="text-xs text-text-secondary">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>

      {/* Avatar - right side for user */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-green flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
};
