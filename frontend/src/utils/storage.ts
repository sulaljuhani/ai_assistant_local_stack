import type { Conversation } from '../types/chat';
import { MAX_CONVERSATIONS } from './constants';

// Storage keys
const STORAGE_KEYS = {
  CONVERSATIONS: 'ai_stack_conversations',
  SETTINGS: 'ai_stack_settings',
} as const;

/**
 * Load conversations from localStorage
 */
export const loadConversations = (): Conversation[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.CONVERSATIONS);
    if (!stored) return [];

    const conversations = JSON.parse(stored) as Conversation[];

    // Sort by updated_at (most recent first)
    return conversations.sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );
  } catch (error) {
    console.error('Failed to load conversations:', error);
    return [];
  }
};

/**
 * Save conversations to localStorage
 */
export const saveConversations = (conversations: Conversation[]): void => {
  try {
    // Keep only last N conversations (prevent storage bloat)
    const toSave = conversations.slice(0, MAX_CONVERSATIONS);
    localStorage.setItem(STORAGE_KEYS.CONVERSATIONS, JSON.stringify(toSave));
  } catch (error) {
    console.error('Failed to save conversations:', error);
  }
};

/**
 * Generate conversation title from first message
 */
export const generateTitle = (firstMessage: string, maxLength = 40): string => {
  if (firstMessage.length <= maxLength) {
    return firstMessage;
  }
  return firstMessage.slice(0, maxLength).trim() + '...';
};

/**
 * Clear all conversations from localStorage
 */
export const clearAllConversations = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEYS.CONVERSATIONS);
  } catch (error) {
    console.error('Failed to clear conversations:', error);
  }
};
