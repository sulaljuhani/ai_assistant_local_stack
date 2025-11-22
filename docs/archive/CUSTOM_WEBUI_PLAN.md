# 🎨 Custom WebUI Implementation Plan

> **Goal:** Build a modern, dark-mode chat interface to replace AnythingLLM with seamless backend integration

**Status:** Planning Complete ✅
**Target Timeline:** 4 days
**Mobile App Ready:** API designed for future mobile app integration

---

## 📋 Overview

### Key Requirements
✅ **Dark mode only** - No light mode, optimized for low-light usage
✅ **Monochrome icons** - Clean, minimalist icon design
✅ **Mobile-first API** - Backend integration ready for future mobile app
✅ **Simple & focused** - Chat interface with essential features
✅ **Backend integration** - Seamless connection to LangGraph FastAPI

### Design Philosophy
- **ChatGPT-inspired dark theme** - Proven, comfortable color palette
- **Minimalist UI** - Focus on conversation, reduce distractions
- **Responsive** - Works on desktop, tablet, mobile (foundation for future app)
- **Fast** - Optimized bundle, <100ms UI interactions

---

## 🎨 Design System

### Color Palette

```css
/* Background Colors */
--color-bg-primary: #343541;        /* Main background (dark gray-blue) */
--color-bg-secondary: #40414f;      /* Chat area / card background */
--color-bg-hover: #444654;          /* Hover states (buttons, inputs) */

/* Text Colors */
--color-text-primary: #ececf1;      /* Main text (high contrast) */
--color-text-secondary: #acacbe;    /* Subtle text (timestamps, labels) */

/* Accent Colors */
--color-accent-green: #10a37f;      /* Primary action (send button, active states) */
--color-accent-green-hover: #1a7f64;/* Hovered actions */
--color-accent-blue: #19c37d;       /* Links, secondary accents */

/* UI Elements */
--color-border: #565869;            /* Dividers, borders */
--color-input-bg: #40414f;          /* Input backgrounds */
--color-input-border: #565869;      /* Input borders */

/* Status Colors */
--color-link: #19c37d;              /* Interactive elements */
--color-error: #ef4444;             /* Errors, warnings */
```

### Typography
```css
/* Font Stack */
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;

/* Text Sizes */
--text-xs: 0.75rem;    /* 12px - timestamps, labels */
--text-sm: 0.875rem;   /* 14px - secondary text */
--text-base: 1rem;     /* 16px - main text */
--text-lg: 1.125rem;   /* 18px - headings */
--text-xl: 1.25rem;    /* 20px - titles */
```

### Spacing Scale
```css
--space-1: 0.25rem;    /* 4px */
--space-2: 0.5rem;     /* 8px */
--space-3: 0.75rem;    /* 12px */
--space-4: 1rem;       /* 16px */
--space-6: 1.5rem;     /* 24px */
--space-8: 2rem;       /* 32px */
```

### Border Radius
```css
--radius-sm: 0.375rem;  /* 6px - buttons */
--radius-md: 0.5rem;    /* 8px - cards */
--radius-lg: 0.75rem;   /* 12px - modals */
--radius-full: 9999px;  /* Fully rounded */
```

### Icons
- **Style:** Monochrome, outline-based
- **Library:** Lucide React (consistent, customizable)
- **Size:** 20px default, 24px for prominent actions
- **Color:** Inherit from text color (--color-text-secondary)

**Key Icons:**
- Message Square - Chat/conversations
- Plus - New chat
- Settings - Settings
- Trash - Delete
- Send - Send message
- User - User messages
- Bot - AI messages
- Sparkles - Agent badges

---

## 🏗️ Architecture

### Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Framework** | React 18 + TypeScript | Type safety, component reuse, mobile app compatibility |
| **Build Tool** | Vite | Fast HMR, optimized builds, modern |
| **Styling** | Tailwind CSS | Utility-first, dark mode support, small bundle |
| **HTTP Client** | Axios | Error handling, interceptors, mobile app ready |
| **State** | React Context + Hooks | Simple, no over-engineering |
| **Icons** | Lucide React | 1000+ icons, tree-shakeable, monochrome |
| **Deployment** | Docker + Nginx | Production-ready, unRAID compatible |

### Backend Integration Points

**Existing FastAPI Endpoints** (`http://localhost:8080`):

| Endpoint | Method | Purpose | Request | Response |
|----------|--------|---------|---------|----------|
| `/chat` | POST | Send message | `ChatRequest` | `ChatResponse` |
| `/chat/stream` | POST | Streaming (future) | `ChatRequest` | SSE stream |
| `/session/{id}` | GET | Get session info | - | `SessionInfo` |
| `/session/{id}` | DELETE | Delete conversation | - | `{message}` |
| `/health` | GET | Health check | - | `{status}` |

**Mobile App Ready:** All endpoints use standard REST/JSON, ready for React Native or Flutter

---

## 📁 Project Structure

```
/home/user/ai_stack/
├── containers/
│   ├── langgraph-agents/           # Existing backend
│   └── ...
├── frontend/                        # 🆕 NEW FRONTEND FOLDER
│   ├── README.md                   # Frontend-specific docs
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js          # Dark theme config
│   ├── index.html
│   ├── .env.example
│   ├── public/
│   │   └── favicon.ico
│   ├── src/
│   │   ├── main.tsx               # Entry point
│   │   ├── App.tsx                # Root component
│   │   │
│   │   ├── api/                   # Backend API client (mobile-ready)
│   │   │   ├── client.ts          # Axios instance with interceptors
│   │   │   └── chat.ts            # Chat API methods
│   │   │
│   │   ├── components/            # React components
│   │   │   ├── Layout/
│   │   │   │   └── AppLayout.tsx         # Main layout wrapper
│   │   │   │
│   │   │   ├── Chat/
│   │   │   │   ├── ChatBox.tsx           # Main chat interface
│   │   │   │   ├── MessageList.tsx       # Message display area
│   │   │   │   ├── Message.tsx           # Individual message
│   │   │   │   ├── MessageInput.tsx      # User input with send button
│   │   │   │   ├── TypingIndicator.tsx   # "Agent is typing..."
│   │   │   │   └── AgentBadge.tsx        # Agent type indicator
│   │   │   │
│   │   │   ├── Sidebar/
│   │   │   │   ├── Sidebar.tsx           # Left sidebar container
│   │   │   │   ├── ConversationList.tsx  # Recent chats list
│   │   │   │   ├── ConversationItem.tsx  # Single conversation
│   │   │   │   ├── NewChatButton.tsx     # Create new chat
│   │   │   │   └── SettingsButton.tsx    # Open settings
│   │   │   │
│   │   │   ├── Settings/
│   │   │   │   └── SettingsModal.tsx     # Settings dialog
│   │   │   │
│   │   │   └── UI/                       # Reusable UI components
│   │   │       ├── Button.tsx            # Styled button
│   │   │       ├── Input.tsx             # Styled input
│   │   │       ├── Modal.tsx             # Modal wrapper
│   │   │       └── Toast.tsx             # Error/success toasts
│   │   │
│   │   ├── contexts/              # State management
│   │   │   ├── ChatContext.tsx           # Chat state & actions
│   │   │   └── SettingsContext.tsx       # App settings
│   │   │
│   │   ├── types/                 # TypeScript definitions
│   │   │   ├── chat.ts                   # Chat/message types
│   │   │   └── api.ts                    # API request/response types
│   │   │
│   │   ├── utils/                 # Helper functions
│   │   │   ├── storage.ts                # localStorage wrapper
│   │   │   ├── uuid.ts                   # Session ID generation
│   │   │   ├── time.ts                   # Date/time formatting
│   │   │   └── constants.ts              # App constants
│   │   │
│   │   └── styles/
│   │       └── index.css                 # Global styles + Tailwind
│   │
│   ├── nginx.conf                 # Nginx config for production
│   ├── Dockerfile                 # Production build
│   └── .dockerignore
│
├── docker-compose.yml             # Add frontend service
└── unraid-templates/
    └── my-frontend.xml            # 🆕 unRAID template
```

---

## 🎨 UI/UX Design

### Desktop Layout (1920x1080)

```
┌────────────────────────────────────────────────────────────────────┐
│  [☰ AI Stack]                                         [⚙️ Settings] │  #343541
├──────────────┬─────────────────────────────────────────────────────┤
│              │                                                      │
│  Sidebar     │                 Chat Area                            │
│  #343541     │                 #40414f                              │
│              │                                                      │
│ ┌──────────┐ │  ┌────────────────────────────────────────────┐    │
│ │ + New    │ │  │  [User Icon] Your message here             │    │
│ │  Chat    │ │  │  9:41 AM                                   │    │
│ └──────────┘ │  └────────────────────────────────────────────┘    │
│              │                                                      │
│ Recent Chats │  ┌────────────────────────────────────────────┐    │
│              │  │  [Bot Icon] Agent response                 │    │
│ ○ Chat 1     │  │  Food Agent • 9:42 AM                      │    │
│   Food log..  │  └────────────────────────────────────────────┘    │
│              │                                                      │
│ ○ Chat 2     │                    ...                               │
│   Task list.. │                                                      │
│              │                                                      │
│ ○ Chat 3     │  ┌───────────────────────────────────────────────┐ │
│   Calendar... │  │ Type a message...                    [Send →] │ │
│              │  └───────────────────────────────────────────────┘ │
│              │                                                      │
│ [⚙️]         │                                                      │
└──────────────┴──────────────────────────────────────────────────────┘
```

### Mobile Layout (375x812)

```
┌──────────────────────┐
│ [☰] AI Stack    [⚙️] │  Compact header
├──────────────────────┤
│                      │
│  Chat Messages       │  Full width
│  (scrollable)        │
│                      │
│  [User] Message      │
│                      │
│  [Bot] Response      │
│  Food Agent          │
│                      │
├──────────────────────┤
│ ┌──────────────────┐ │  Fixed input
│ │ Type...   [Send] │ │
│ └──────────────────┘ │
└──────────────────────┘
```

### Component Specifications

#### 1. Sidebar (`250px` fixed width on desktop)

**Header:**
- App logo/icon + "AI Stack" title
- Settings icon (top-right)
- Background: `#343541`

**New Chat Button:**
- Full width, prominent
- Icon: `Plus` (monochrome)
- Background: `#10a37f`
- Hover: `#1a7f64`
- Text: "New Chat"

**Conversation List:**
- Scrollable list of recent chats
- Max 20 conversations shown
- Each item:
  - Title (first message truncated)
  - Timestamp (relative: "2h ago")
  - Active state: border-left `#10a37f`
  - Hover: background `#444654`
  - Delete icon on hover

**Mobile:**
- Drawer overlay (slide from left)
- Backdrop blur + dim
- Swipe to close

#### 2. Chat Area

**Message List:**
- Background: `#40414f`
- Padding: `24px`
- Auto-scroll to latest message
- Gap between messages: `16px`

**User Message:**
- Align: Right
- Background: `#343541`
- Text: `#ececf1`
- Border-radius: `8px`
- Icon: User (monochrome)
- Max-width: `70%`

**AI Message:**
- Align: Left
- Background: `#444654`
- Text: `#ececf1`
- Border-radius: `8px`
- Icon: Bot (monochrome)
- Agent badge: "Food Agent" (text + icon)
- Max-width: `70%`

**Timestamp:**
- Color: `#acacbe`
- Size: `12px`
- Show on hover or always on mobile

#### 3. Message Input

**Design:**
- Fixed at bottom (sticky)
- Background: `#40414f`
- Border-top: `1px solid #565869`
- Padding: `16px 24px`
- Shadow: `0 -2px 10px rgba(0,0,0,0.3)`

**Input Box:**
- Background: `#343541`
- Border: `1px solid #565869`
- Border-radius: `8px`
- Padding: `12px 16px`
- Color: `#ececf1`
- Placeholder: `#acacbe`
- Auto-resize: 1-5 lines
- Focus: border `#10a37f`

**Send Button:**
- Position: Right inside input
- Icon: Send (arrow) monochrome
- Background: `#10a37f`
- Size: `40px x 40px`
- Border-radius: `6px`
- Disabled: opacity `0.5`
- Loading: spinner

**Keyboard:**
- `Enter` to send
- `Shift + Enter` for new line
- `Ctrl/Cmd + K` for new chat (future)

#### 4. Settings Modal

**Trigger:** Settings icon in sidebar

**Content:**
- **Backend URL:** Text input (for testing)
- **User ID:** Display only (hardcoded UUID)
- **Workspace:** Display or input (default: "default")
- **Clear All Chats:** Danger button with confirmation
- **About:** App version, backend status
- **Close:** X button or backdrop click

**Style:**
- Modal overlay: backdrop blur
- Modal: `#40414f`, centered
- Max-width: `500px`
- Border-radius: `12px`
- Shadow: `0 20px 60px rgba(0,0,0,0.5)`

#### 5. Agent Badge

**Position:** Below AI message (left-aligned)

**Design:**
- Small pill shape
- Background: transparent
- Border: `1px solid #565869`
- Text: `12px`, `#acacbe`
- Icon + text: "🍽️ Food Agent"

**Agents:**
- Food Agent: Bowl icon (monochrome)
- Task Agent: Check icon (monochrome)
- Event Agent: Calendar icon (monochrome)
- General: Bot icon (monochrome)

#### 6. Loading States

**Typing Indicator:**
- Three dots animation
- Color: `#acacbe`
- Position: Bottom of message list
- Text: "Agent is typing..."

**Send Button:**
- Replace send icon with spinner
- Disable input during send

**Initial Load:**
- Full-screen centered spinner
- Background: `#343541`

---

## 🔌 Backend Integration

### API Client

#### `src/api/client.ts`
```typescript
import axios from 'axios';

// Environment variable or fallback
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8080';

// Create axios instance
export const apiClient = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor (for future auth tokens)
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available (future)
    // const token = localStorage.getItem('auth_token');
    // if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;

      if (status === 429) {
        console.error('Rate limit exceeded');
      } else if (status === 500) {
        console.error('Server error:', data.detail);
      } else if (status === 422) {
        console.error('Validation error:', data.detail);
      }
    } else if (error.request) {
      // Request made but no response
      console.error('Network error: No response from server');
    } else {
      console.error('Request setup error:', error.message);
    }

    return Promise.reject(error);
  }
);
```

#### `src/api/chat.ts`
```typescript
import { apiClient } from './client';
import type {
  ChatRequest,
  ChatResponse,
  SessionInfo,
  HealthResponse
} from '../types/api';

export const chatApi = {
  /**
   * Send a message to the multi-agent system
   */
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const { data } = await apiClient.post<ChatResponse>('/chat', request);
    return data;
  },

  /**
   * Get session/conversation details
   */
  getSession: async (sessionId: string): Promise<SessionInfo> => {
    const { data } = await apiClient.get<SessionInfo>(`/session/${sessionId}`);
    return data;
  },

  /**
   * Delete a session/conversation
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/session/${sessionId}`);
  },

  /**
   * Check backend health
   */
  healthCheck: async (): Promise<HealthResponse> => {
    const { data } = await apiClient.get<HealthResponse>('/health');
    return data;
  },
};
```

### TypeScript Types

#### `src/types/api.ts`
```typescript
/**
 * Backend API request/response types
 * Match FastAPI Pydantic models exactly
 */

// ============================================================================
// Chat Endpoints
// ============================================================================

export interface ChatRequest {
  message: string;
  user_id: string;
  workspace: string;
  session_id: string;
}

export interface ChatResponse {
  response: string;
  agent: string;
  session_id: string;
  turn_count: number;
  timestamp: string;
}

// ============================================================================
// Session Endpoints
// ============================================================================

export interface SessionInfo {
  session_id: string;
  user_id: string;
  workspace: string;
  current_agent: string;
  turn_count: number;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Health Endpoint
// ============================================================================

export interface HealthResponse {
  status: string;
  timestamp: string;
  llm_provider: string;
}
```

#### `src/types/chat.ts`
```typescript
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
  error: string | null;
}
```

---

## 💾 State Management

### Chat Context

#### `src/contexts/ChatContext.tsx`
```typescript
import { createContext, useContext, useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { chatApi } from '../api/chat';
import {
  Conversation,
  Message,
  ChatState
} from '../types/chat';
import {
  loadConversations,
  saveConversations,
  USER_ID,
  WORKSPACE
} from '../utils/storage';

interface ChatContextType extends ChatState {
  // Actions
  sendMessage: (content: string) => Promise<void>;
  createNewConversation: () => void;
  switchConversation: (id: string) => void;
  deleteConversation: (id: string) => Promise<void>;
  clearAllConversations: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<ChatState>({
    currentConversation: null,
    conversations: [],
    isLoading: true,
    isSending: false,
    error: null,
  });

  // Load conversations from localStorage on mount
  useEffect(() => {
    const conversations = loadConversations();
    const lastConversation = conversations[0] || null;

    setState(prev => ({
      ...prev,
      conversations,
      currentConversation: lastConversation,
      isLoading: false,
    }));
  }, []);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    if (!state.isLoading) {
      saveConversations(state.conversations);
    }
  }, [state.conversations, state.isLoading]);

  const sendMessage = async (content: string) => {
    if (!state.currentConversation) return;

    setState(prev => ({ ...prev, isSending: true, error: null }));

    // Add user message immediately (optimistic update)
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...state.currentConversation.messages, userMessage];

    setState(prev => ({
      ...prev,
      currentConversation: {
        ...prev.currentConversation!,
        messages: updatedMessages,
        updated_at: new Date().toISOString(),
      },
    }));

    try {
      // Call backend
      const response = await chatApi.sendMessage({
        message: content,
        user_id: USER_ID,
        workspace: WORKSPACE,
        session_id: state.currentConversation.id,
      });

      // Add AI response
      const aiMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response.response,
        agent: response.agent as any,
        timestamp: response.timestamp,
      };

      setState(prev => {
        const updatedConv = {
          ...prev.currentConversation!,
          messages: [...updatedMessages, aiMessage],
          agent: response.agent as any,
          updated_at: response.timestamp,
        };

        // Update in conversations list
        const updatedConversations = prev.conversations.map(conv =>
          conv.id === updatedConv.id ? updatedConv : conv
        );

        return {
          ...prev,
          currentConversation: updatedConv,
          conversations: updatedConversations,
          isSending: false,
        };
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        isSending: false,
        error: 'Failed to send message. Please try again.',
      }));
    }
  };

  const createNewConversation = () => {
    const newConversation: Conversation = {
      id: uuidv4(),
      title: 'New Chat',
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

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
      // Delete from backend
      await chatApi.deleteSession(id);

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
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const clearAllConversations = () => {
    setState({
      currentConversation: null,
      conversations: [],
      isLoading: false,
      isSending: false,
      error: null,
    });
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

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within ChatProvider');
  }
  return context;
};
```

### Local Storage

#### `src/utils/storage.ts`
```typescript
import type { Conversation } from '../types/chat';

// Storage keys
const STORAGE_KEYS = {
  CONVERSATIONS: 'ai_stack_conversations',
  SETTINGS: 'ai_stack_settings',
} as const;

// Hardcoded constants (single-user system)
export const USER_ID = '00000000-0000-0000-0000-000000000001';
export const WORKSPACE = 'default';

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
    // Keep only last 50 conversations (prevent storage bloat)
    const toSave = conversations.slice(0, 50);
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
```

---

## 🚀 Implementation Phases

### Phase 1: MVP - Basic Chat (Days 1-2)

**Goal:** Working chat interface that connects to LangGraph backend

#### Tasks:
- [ ] **Project Setup**
  - [ ] Initialize Vite + React + TypeScript project
  - [ ] Install dependencies (axios, tailwind, lucide-react, uuid)
  - [ ] Configure Tailwind with dark theme colors
  - [ ] Setup ESLint + Prettier
  - [ ] Create `.env.example` with backend URL

- [ ] **API Layer**
  - [ ] Create API client (`src/api/client.ts`)
  - [ ] Implement chat methods (`src/api/chat.ts`)
  - [ ] Define TypeScript types (`src/types/`)
  - [ ] Test API connection with backend

- [ ] **State Management**
  - [ ] Create ChatContext (`src/contexts/ChatContext.tsx`)
  - [ ] Implement localStorage utilities (`src/utils/storage.ts`)
  - [ ] Add conversation CRUD operations

- [ ] **Core Components**
  - [ ] Build AppLayout (sidebar + chat area)
  - [ ] Create MessageList component
  - [ ] Create Message component (user/assistant)
  - [ ] Build MessageInput with auto-resize
  - [ ] Add send button with loading state

- [ ] **Integration**
  - [ ] Connect MessageInput to ChatContext
  - [ ] Display messages from state
  - [ ] Handle errors gracefully
  - [ ] Auto-scroll to latest message

- [ ] **Testing**
  - [ ] Test sending messages
  - [ ] Verify agent responses display correctly
  - [ ] Test error handling
  - [ ] Check localStorage persistence

**Deliverable:** Working chat that successfully communicates with LangGraph agents

---

### Phase 2: Polish & UX (Day 3)

**Goal:** Production-ready UI with all features

#### Tasks:
- [ ] **Sidebar**
  - [ ] Create Sidebar component with New Chat button
  - [ ] Build ConversationList with recent chats
  - [ ] Add ConversationItem with delete on hover
  - [ ] Implement active state highlighting
  - [ ] Add empty state (no conversations)

- [ ] **Agent Features**
  - [ ] Create AgentBadge component
  - [ ] Add agent icons (Food/Task/Event)
  - [ ] Display agent in AI messages
  - [ ] Color-code by agent type (subtle)

- [ ] **UI Enhancements**
  - [ ] Add TypingIndicator component
  - [ ] Implement Toast notifications
  - [ ] Add message timestamps (relative)
  - [ ] Create loading skeleton screens
  - [ ] Add smooth animations (fade in/out)

- [ ] **Settings**
  - [ ] Build SettingsModal component
  - [ ] Add backend URL configuration
  - [ ] Display user ID (read-only)
  - [ ] Implement "Clear All Chats" with confirmation
  - [ ] Show backend health status

- [ ] **Responsive Design**
  - [ ] Mobile layout (drawer sidebar)
  - [ ] Tablet breakpoints
  - [ ] Touch-friendly tap targets (44px min)
  - [ ] Test on various screen sizes

- [ ] **Polish**
  - [ ] Keyboard shortcuts (Enter, Shift+Enter)
  - [ ] Focus management (auto-focus input)
  - [ ] Smooth scrolling
  - [ ] Loading states for all actions

**Deliverable:** Polished, user-friendly interface ready for production

---

### Phase 3: Docker & Deployment (Day 4)

**Goal:** Containerized frontend integrated with AI Stack

#### Tasks:
- [ ] **Docker Configuration**
  - [ ] Create production Dockerfile (multi-stage)
  - [ ] Configure Nginx for SPA routing
  - [ ] Optimize build size
  - [ ] Add health check endpoint

- [ ] **Integration**
  - [ ] Add frontend service to `docker-compose.yml`
  - [ ] Configure environment variables
  - [ ] Setup network connectivity
  - [ ] Test full stack deployment

- [ ] **CORS Configuration**
  - [ ] Update backend `.env` with frontend origin
  - [ ] Test cross-origin requests
  - [ ] Verify rate limiting works

- [ ] **unRAID Template**
  - [ ] Create `my-frontend.xml` template
  - [ ] Add configuration options
  - [ ] Document installation steps
  - [ ] Test on unRAID (if available)

- [ ] **Documentation**
  - [ ] Write frontend README.md
  - [ ] Update main README with frontend instructions
  - [ ] Document environment variables
  - [ ] Add screenshots/demo
  - [ ] Create troubleshooting guide

- [ ] **Testing**
  - [ ] Full stack integration test
  - [ ] Multi-agent conversation test
  - [ ] Error handling verification
  - [ ] Performance check (bundle size, load time)

**Deliverable:** Production-ready frontend deployed with AI Stack

---

### Phase 4: Future Enhancements

**Mobile App Foundation:**
- [ ] Streaming responses (`/chat/stream` with SSE)
- [ ] Markdown rendering for AI messages
- [ ] Code syntax highlighting
- [ ] Export conversation as markdown
- [ ] Search conversations (local)
- [ ] Keyboard shortcuts (Cmd+K, Cmd+N)
- [ ] Voice input (Web Speech API)
- [ ] PWA support (offline caching)

**Mobile App Readiness:**
- API already mobile-ready (REST + JSON)
- State management patterns transferable
- UI components can inform mobile design
- Color system documented for mobile

---

## 🐳 Docker Configuration

### Dockerfile

**File:** `frontend/Dockerfile`

```dockerfile
# ============================================================================
# Build Stage
# ============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build for production
RUN npm run build

# ============================================================================
# Production Stage
# ============================================================================
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3001 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

**File:** `frontend/nginx.conf`

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/x-javascript application/javascript application/xml+rss
               application/json;

    server {
        listen 3001;
        server_name _;
        root /usr/share/nginx/html;
        index index.html;

        # SPA routing - serve index.html for all routes
        location / {
            try_files $uri $uri/ /index.html;
        }

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
    }
}
```

### Docker Compose Integration

**Update:** `docker-compose.yml`

```yaml
services:
  # ... existing services ...

  frontend:
    container_name: ai-stack-frontend
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3001:3001"
    environment:
      - VITE_BACKEND_URL=http://langgraph-agents:8080
    networks:
      - ai-stack-network
    restart: unless-stopped
    depends_on:
      - langgraph-agents
    labels:
      - "com.centurylinklabs.watchtower.enable=true"

networks:
  ai-stack-network:
    external: true
```

### Backend CORS Update

**File:** `containers/langgraph-agents/.env`

```bash
# Add frontend origin to CORS
CORS_ALLOWED_ORIGINS=http://localhost:3001,http://your-server-ip:3001
```

---

## 📝 Frontend README Structure

**File:** `frontend/README.md`

```markdown
# 🎨 AI Stack - Custom WebUI

Modern dark-mode chat interface for AI Stack multi-agent system.

## Features

- 🌙 Dark mode only (ChatGPT-inspired theme)
- 🤖 Multi-agent support (Food, Task, Event)
- 💬 Real-time chat with LangGraph backend
- 💾 Local conversation persistence
- 📱 Responsive design (mobile-ready)
- 🎨 Monochrome icons, minimalist UI

## Quick Start

### Development
```bash
npm install
npm run dev
```

Visit: http://localhost:5173

### Build
```bash
npm run build
```

### Docker
```bash
docker build -t ai-stack-frontend .
docker run -p 3001:3001 -e VITE_BACKEND_URL=http://localhost:8080 ai-stack-frontend
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_BACKEND_URL` | `http://localhost:8080` | LangGraph API URL |

## Project Structure

```
src/
├── api/          # Backend integration
├── components/   # React components
├── contexts/     # State management
├── types/        # TypeScript definitions
├── utils/        # Helper functions
└── styles/       # Global styles
```

## Backend Integration

Connects to LangGraph FastAPI backend:
- `POST /chat` - Send messages
- `GET /session/{id}` - Get session
- `DELETE /session/{id}` - Delete conversation

See main AI Stack README for backend setup.

## Development

**Tech Stack:**
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Axios (HTTP client)
- Lucide React (icons)

**Commands:**
```bash
npm run dev      # Start dev server
npm run build    # Production build
npm run preview  # Preview production build
npm run lint     # Lint code
```

## Deployment

Included in AI Stack docker-compose:
```bash
docker-compose up -d frontend
```

See `../unraid-templates/my-frontend.xml` for unRAID deployment.

## Mobile App

This WebUI is designed with mobile app development in mind:
- API client ready for React Native/Flutter
- State management patterns transferable
- Design system documented in `docs/CUSTOM_WEBUI_PLAN.md`
```

---

## ✅ Success Criteria

### Functional Requirements
- ✅ Send messages to LangGraph backend via `/chat`
- ✅ Display AI responses with agent identification
- ✅ Create new conversations
- ✅ Switch between conversations
- ✅ Delete conversations (backend + local)
- ✅ Persist conversations in localStorage
- ✅ Show loading/sending states
- ✅ Handle errors gracefully
- ✅ Auto-scroll to latest message

### UI/UX Requirements
- ✅ Dark mode only (ChatGPT color palette)
- ✅ Monochrome icons (Lucide React)
- ✅ Responsive layout (desktop, tablet, mobile)
- ✅ Smooth animations and transitions
- ✅ Keyboard shortcuts (Enter, Shift+Enter)
- ✅ Touch-friendly (44px tap targets)
- ✅ Auto-focus input after send
- ✅ Relative timestamps ("2h ago")

### Integration Requirements
- ✅ Compatible with existing FastAPI backend
- ✅ Respects CORS configuration
- ✅ Handles rate limiting (20 req/min)
- ✅ Uses hardcoded user ID correctly
- ✅ Works with all agents (Food, Task, Event)

### Deployment Requirements
- ✅ Dockerized with Nginx
- ✅ Integrated with docker-compose
- ✅ unRAID template available
- ✅ Health check endpoint
- ✅ Environment variables documented
- ✅ Frontend README complete

### Mobile App Readiness
- ✅ API client is framework-agnostic
- ✅ State patterns transferable to mobile
- ✅ Design system documented
- ✅ Color palette exported
- ✅ Component architecture modular

---

## 🎯 Configuration

### Environment Variables

**Frontend** (`.env`):
```bash
# Backend API URL
VITE_BACKEND_URL=http://localhost:8080

# Note: User ID and workspace are hardcoded in code (single-user system)
```

**Backend** (update `containers/langgraph-agents/.env`):
```bash
# Add frontend origin to CORS
CORS_ALLOWED_ORIGINS=http://localhost:3001,http://your-server-ip:3001,http://your-domain.com
```

### Hardcoded Constants

**File:** `src/utils/constants.ts`

```typescript
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
```

---

## 📊 Bundle Size Target

| Asset | Target | Strategy |
|-------|--------|----------|
| **JS Bundle** | < 200 KB | Code splitting, tree shaking |
| **CSS** | < 20 KB | Tailwind purge, critical CSS |
| **Icons** | < 10 KB | Lucide tree-shaking |
| **Total** | < 250 KB | Gzip compression |

**Optimization:**
- Vite automatic code splitting
- Tailwind CSS purge unused classes
- Lucide React tree-shakeable imports
- Nginx gzip compression
- Static asset caching (1 year)

---

## 🧪 Testing Checklist

### Functional Tests
- [ ] Send message and receive response
- [ ] Agent correctly identified (Food/Task/Event)
- [ ] Create new conversation
- [ ] Switch between conversations
- [ ] Delete conversation
- [ ] Settings modal opens/closes
- [ ] Backend health check works

### UI Tests
- [ ] Dark mode colors correct
- [ ] Icons render as monochrome
- [ ] Messages align correctly (user right, AI left)
- [ ] Input auto-resizes (1-5 lines)
- [ ] Auto-scroll works on new message
- [ ] Timestamps display relatively
- [ ] Loading states show during send
- [ ] Error messages display in toast

### Integration Tests
- [ ] API calls succeed with 200 status
- [ ] Rate limiting handled (429 error)
- [ ] Network errors show user-friendly message
- [ ] CORS allows frontend origin
- [ ] Backend `/health` accessible

### Responsive Tests
- [ ] Desktop (1920x1080) layout correct
- [ ] Tablet (768x1024) layout adapts
- [ ] Mobile (375x812) drawer works
- [ ] Touch targets ≥ 44px
- [ ] Landscape orientation works

### Performance Tests
- [ ] Initial load < 2 seconds
- [ ] Bundle size < 250 KB
- [ ] Lighthouse score > 90
- [ ] No memory leaks (check DevTools)

---

## 📱 Mobile App Considerations

### API Compatibility
✅ **REST API** - Standard HTTP, works with any framework
✅ **JSON Payloads** - Universal data format
✅ **Stateless** - Each request independent
✅ **Error Handling** - Standard HTTP status codes

### State Management Transfer
- ChatContext → Zustand/Redux (mobile)
- localStorage → AsyncStorage (React Native)
- axios → same or fetch API

### UI Components Transfer
- Layout patterns → React Native Views
- Color system → StyleSheet constants
- Icons → react-native-vector-icons
- Animations → Animated API

### Future Mobile Endpoints (Optional)
```typescript
// Push notifications
POST /api/notifications/register
POST /api/notifications/unregister

// Mobile-specific
GET /api/conversations/summary  // Lighter payload
POST /api/conversations/sync    // Sync state
```

---

## 🔧 Development Commands

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Type check
npm run type-check

# Lint code
npm run lint

# Format code
npm run format

# Build for production
npm run build

# Preview production build
npm run preview

# Docker build
docker build -t ai-stack-frontend .

# Docker run
docker run -p 3001:3001 ai-stack-frontend
```

---

## 📚 Dependencies

### Core
- `react` ^18.3.0
- `react-dom` ^18.3.0
- `typescript` ^5.5.0

### API & State
- `axios` ^1.7.0
- `uuid` ^10.0.0

### UI & Styling
- `tailwindcss` ^3.4.0
- `lucide-react` ^0.400.0

### Build Tools
- `vite` ^5.4.0
- `@vitejs/plugin-react` ^4.3.0

### Dev Tools
- `eslint` ^9.0.0
- `prettier` ^3.3.0
- `@types/react` ^18.3.0
- `@types/uuid` ^10.0.0

**Total:** ~15 dependencies (lightweight)

---

## 🎓 Learning Resources

### React + TypeScript
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Vite Guide](https://vitejs.dev/guide/)

### Tailwind CSS
- [Tailwind Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [Tailwind Custom Colors](https://tailwindcss.com/docs/customizing-colors)

### Backend Integration
- [Axios Interceptors](https://axios-http.com/docs/interceptors)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)

---

## 🚀 Next Steps

1. ✅ **Review Plan** - Confirm approach and design
2. **Initialize Project** - Setup Vite + React + TypeScript
3. **Phase 1 Implementation** - Build MVP chat interface
4. **Phase 2 Implementation** - Polish UI/UX
5. **Phase 3 Implementation** - Dockerize and deploy
6. **Testing** - Verify all functionality
7. **Documentation** - Complete README and guides
8. **Launch** - Replace AnythingLLM

---

**Timeline:** 4 days for production-ready WebUI
**Mobile App:** API ready, foundation in place
**Design:** Dark mode, monochrome, ChatGPT-inspired

Ready to build! 🎨🚀
