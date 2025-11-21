import type { Conversation } from '../types/chat';
import { MAX_CONVERSATIONS } from './constants';

// Storage keys
const STORAGE_KEYS = {
  CONVERSATIONS: 'ai_stack_conversations',
  SETTINGS: 'ai_stack_settings',
  API_SETTINGS: 'ai_stack_api_settings',
} as const;

/**
 * API Provider types
 */
export type ApiProvider = 'ollama' | 'openai';

/**
 * API Settings interface
 */
export interface ApiSettings {
  provider: ApiProvider;
  ollamaUrl: string;
  ollamaModel: string;
  openaiApiKey: string;
  openaiModel: string;
  openaiBaseUrl: string;
}

/**
 * Default API settings
 */
const DEFAULT_API_SETTINGS: ApiSettings = {
  provider: 'ollama',
  ollamaUrl: 'http://localhost:11434',
  ollamaModel: 'llama3.2:3b',
  openaiApiKey: '',
  openaiModel: 'gpt-4',
  openaiBaseUrl: 'https://api.openai.com/v1',
};

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

/**
 * Load API settings from localStorage
 */
export const loadApiSettings = (): ApiSettings => {
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.API_SETTINGS);
    if (!stored) return DEFAULT_API_SETTINGS;

    const settings = JSON.parse(stored) as Partial<ApiSettings>;

    // Merge with defaults to handle missing fields
    return {
      ...DEFAULT_API_SETTINGS,
      ...settings,
    };
  } catch (error) {
    console.error('Failed to load API settings:', error);
    return DEFAULT_API_SETTINGS;
  }
};

/**
 * Save API settings to localStorage
 */
export const saveApiSettings = (settings: ApiSettings): void => {
  try {
    localStorage.setItem(STORAGE_KEYS.API_SETTINGS, JSON.stringify(settings));
  } catch (error) {
    console.error('Failed to save API settings:', error);
  }
};
