import { User, Bot } from 'lucide-react';
import type { Message as MessageType } from '../../types/chat';
import { formatTime } from '../../utils/time';
import { AGENT_INFO } from '../../utils/constants';

interface MessageProps {
  message: MessageType;
}

export const Message: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const agentInfo = message.agent ? AGENT_INFO[message.agent] : null;

  return (
    <div
      className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* Avatar - left side for assistant */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bg-hover flex items-center justify-center">
          <Bot className="w-5 h-5 text-text-secondary" />
        </div>
      )}

      {/* Message content */}
      <div className={`flex flex-col max-w-[70%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Message bubble */}
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-bg-primary text-text-primary'
              : 'bg-bg-hover text-text-primary'
          }`}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>

        {/* Metadata (timestamp + agent badge for assistant) */}
        <div className="flex items-center gap-2 mt-1 px-1">
          <span className="text-xs text-text-secondary">
            {formatTime(message.timestamp)}
          </span>

          {/* Agent badge for assistant messages */}
          {!isUser && agentInfo && (
            <>
              <span className="text-xs text-text-secondary">•</span>
              <span className="text-xs text-text-secondary">
                {agentInfo.emoji} {agentInfo.name}
              </span>
            </>
          )}
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
