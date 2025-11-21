import { useState, useRef, type KeyboardEvent, type ChangeEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  disabled = false,
  isLoading = false,
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  const handleInput = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const target = e.target;
    setMessage(target.value);

    // Reset height to auto to get correct scrollHeight
    target.style.height = 'auto';

    // Calculate new height (min 1 line, max 5 lines ~120px)
    const newHeight = Math.min(target.scrollHeight, 120);
    target.style.height = `${newHeight}px`;
  };

  // Handle send
  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !disabled && !isLoading) {
      onSend(trimmedMessage);
      setMessage('');

      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send (without shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    // Shift+Enter for new line (default behavior)
  };

  return (
    <div className="border-t border-border bg-bg-secondary px-6 py-4">
      <div className="max-w-4xl mx-auto">
        <div className="relative flex items-end gap-3 bg-input-bg border border-input-border rounded-lg p-3">
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={disabled || isLoading}
            rows={1}
            className="flex-1 bg-transparent text-text-primary placeholder-text-secondary
                     resize-none outline-none max-h-[120px] min-h-[24px]"
            style={{ height: 'auto' }}
          />

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={!message.trim() || disabled || isLoading}
            className="flex-shrink-0 w-10 h-10 rounded-md bg-accent-green hover:bg-accent-green-hover
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                     flex items-center justify-center"
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <Send className="w-5 h-5 text-white" />
            )}
          </button>
        </div>

        {/* Hint text */}
        <p className="text-xs text-text-secondary mt-2 text-center">
          Press <kbd className="px-1.5 py-0.5 bg-bg-hover rounded text-xs">Enter</kbd> to send,{' '}
          <kbd className="px-1.5 py-0.5 bg-bg-hover rounded text-xs">Shift + Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
};
