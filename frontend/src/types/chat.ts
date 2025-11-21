/**
 * Frontend chat types (local UI state)
 */

export type MessageRole = 'user' | 'assistant';

export type AgentType = 'food_agent' | 'task_agent' | 'event_agent' | 'general';

export interface Message {
  id: string;              // Frontend-generated UUID
  role: MessageRole;
  content: string;
  agent?: AgentType;       // Only for assistant messages
  timestamp: string;       // ISO string
}

export interface Conversation {
  id: string;              // Session ID (UUID)
  title: string;           // Auto-generated from first message
  messages: Message[];
  agent?: AgentType;       // Last active agent
  created_at: string;
  updated_at: string;
}

export interface ChatState {
  // Current active conversation
  currentConversation: Conversation | null;

  // All conversations (stored locally)
  conversations: Conversation[];

  // UI state
  isLoading: boolean;
  isSending: boolean;
}
