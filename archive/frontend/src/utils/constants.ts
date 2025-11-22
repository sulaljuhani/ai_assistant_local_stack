/**
 * Application constants
 */

// Single-user system constants
export const USER_ID = '00000000-0000-0000-0000-000000000001';
export const WORKSPACE = 'default';

// UI constants
export const MAX_CONVERSATIONS = 50;
export const MESSAGE_POLL_INTERVAL = 5000; // Future: for updates
export const TYPING_INDICATOR_DELAY = 500; // ms

// Agent types
export const AGENTS = {
  FOOD: 'food_agent',
  TASK: 'task_agent',
  EVENT: 'event_agent',
  GENERAL: 'general',
} as const;

// Agent display names and icons
export const AGENT_INFO = {
  food_agent: {
    name: 'Food Agent',
    emoji: '🍽️',
  },
  task_agent: {
    name: 'Task Agent',
    emoji: '✅',
  },
  event_agent: {
    name: 'Event Agent',
    emoji: '📅',
  },
  general: {
    name: 'General',
    emoji: '🤖',
  },
} as const;
