import { useEffect, useRef } from 'react';
import { Message } from './Message';
import type { Message as MessageType } from '../../types/chat';
import { Loader2 } from 'lucide-react';

interface MessageListProps {
  messages: MessageType[];
  isLoading?: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Empty state
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            Start a conversation
          </h2>
          <p className="text-text-secondary">
            Ask me anything! I can help with food logging, task management, and calendar events.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin px-6 py-6">
      <div className="flex flex-col gap-6 max-w-4xl mx-auto">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}

        {/* Typing indicator */}
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bg-hover flex items-center justify-center">
              <Loader2 className="w-5 h-5 text-text-secondary animate-spin" />
            </div>
            <div className="bg-bg-hover rounded-lg px-4 py-3">
              <p className="text-text-secondary text-sm">Agent is typing...</p>
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
