import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { chatApi } from '../api/chat';
import type { Conversation, Message, ChatState, AgentType } from '../types/chat';
import {
  loadConversations,
  saveConversations,
  generateTitle,
  clearAllConversations as clearStorage,
} from '../utils/storage';
import { USER_ID, WORKSPACE } from '../utils/constants';
import { useToast } from './ToastContext';

interface ChatContextType extends ChatState {
  // Actions
  sendMessage: (content: string) => Promise<void>;
  createNewConversation: () => void;
  switchConversation: (id: string) => void;
  deleteConversation: (id: string) => Promise<void>;
  clearAllConversations: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { showError, showSuccess } = useToast();
  const createConversation = (title = 'New Chat'): Conversation => ({
    id: uuidv4(),
    title,
    messages: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });

  const [state, setState] = useState<ChatState>(() => {
    const stored = loadConversations();
    const conversations = stored.length > 0 ? stored : [createConversation()];
    const lastConversation = conversations[0] || null;

    return {
      currentConversation: lastConversation,
      conversations,
      isLoading: false,
      isSending: false,
    };
  });

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    saveConversations(state.conversations);
  }, [state.conversations]);

  const sendMessage = async (content: string) => {
    if (!state.currentConversation) return;
    if (!content.trim()) return;

    setState(prev => ({ ...prev, isSending: true }));

    // Add user message immediately (optimistic update)
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...state.currentConversation.messages, userMessage];

    // Update title if this is the first message
    const isFirstMessage = state.currentConversation.messages.length === 0;
    const updatedTitle = isFirstMessage
      ? generateTitle(content)
      : state.currentConversation.title;

    // Update current conversation with user message
    const updatedConv = {
      ...state.currentConversation,
      messages: updatedMessages,
      title: updatedTitle,
      updated_at: new Date().toISOString(),
    };

    setState(prev => {
      const existing = prev.conversations.some(conv => conv.id === updatedConv.id);
      const conversations = existing
        ? prev.conversations.map(conv =>
            conv.id === updatedConv.id ? updatedConv : conv
          )
        : [updatedConv, ...prev.conversations];

      const sorted = [...conversations].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );

      return {
        ...prev,
        currentConversation: updatedConv,
        conversations: sorted,
      };
    });

    try {
      // Call backend
      const response = await chatApi.sendMessage({
        message: content.trim(),
        user_id: USER_ID,
        workspace: WORKSPACE,
        session_id: state.currentConversation.id,
      });

      // Add AI response
      const aiMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response.response,
        agent: response.agent as AgentType,
        timestamp: response.timestamp,
      };

      setState(prev => {
        if (!prev.currentConversation) return prev;

        const finalConv: Conversation = {
          ...prev.currentConversation,
          messages: [...updatedMessages, aiMessage],
          agent: response.agent as AgentType,
          updated_at: response.timestamp,
          title: updatedTitle,
        };

        // Update in conversations list
        const updatedConversations = prev.conversations.map(conv =>
          conv.id === finalConv.id ? finalConv : conv
        );

        // Sort by updated_at
        const sortedConversations = updatedConversations.sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );

        return {
          ...prev,
          currentConversation: finalConv,
          conversations: sortedConversations,
          isSending: false,
        };
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      showError('Failed to send message. Please check your connection and try again.');
      setState(prev => ({
        ...prev,
        isSending: false,
      }));
    }
  };

  const createNewConversation = () => {
    const newConversation = createConversation();

    setState(prev => ({
      ...prev,
      currentConversation: newConversation,
      conversations: [newConversation, ...prev.conversations],
    }));
  };

  const switchConversation = (id: string) => {
    const conversation = state.conversations.find(c => c.id === id);
    if (conversation) {
      setState(prev => ({
        ...prev,
        currentConversation: conversation,
      }));
    }
  };

  const deleteConversation = async (id: string) => {
    try {
      // Delete from backend (ignore errors if session doesn't exist)
      await chatApi.deleteSession(id).catch(() => {
        // Session might not exist on backend, that's ok
      });

      setState(prev => {
        const updatedConversations = prev.conversations.filter(c => c.id !== id);
        const newCurrent = prev.currentConversation?.id === id
          ? updatedConversations[0] || null
          : prev.currentConversation;

        return {
          ...prev,
          conversations: updatedConversations,
          currentConversation: newCurrent,
        };
      });

      showSuccess('Conversation deleted successfully');
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      showError('Failed to delete conversation. Please try again.');
    }
  };

  const clearAllConversations = () => {
    clearStorage();
    const newConversation = createConversation();
    setState({
      currentConversation: newConversation,
      conversations: [newConversation],
      isLoading: false,
      isSending: false,
    });
    showSuccess('All conversations cleared');
  };

  return (
    <ChatContext.Provider
      value={{
        ...state,
        sendMessage,
        createNewConversation,
        switchConversation,
        deleteConversation,
      clearAllConversations,
    }}
  >
    {children}
  </ChatContext.Provider>
  );
};

// The provider and hook live together intentionally; suppress fast refresh warning.
// eslint-disable-next-line react-refresh/only-export-components
export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within ChatProvider');
  }
  return context;
};
