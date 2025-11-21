# 🎨 AI Stack - Custom WebUI

Modern dark-mode chat interface for AI Stack multi-agent system.

## ✨ Features

- 🌙 **Dark mode only** - ChatGPT-inspired color palette
- 🤖 **Multi-agent support** - Food, Task, Event agents
- 💬 **Real-time chat** - Seamless LangGraph backend integration
- 💾 **Local persistence** - Conversations stored in browser
- 📱 **Responsive design** - Mobile-ready interface
- 🎨 **Monochrome icons** - Clean, minimalist UI
- ⌨️ **Keyboard shortcuts** - Enter to send, Shift+Enter for new line

## 🚀 Quick Start

### Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

Visit: http://localhost:5173

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## 🔧 Environment Variables

Create a `.env` file (see `.env.example`):

```bash
# Backend API URL
VITE_BACKEND_URL=http://localhost:8080
```

**Note:** User ID and workspace are hardcoded in code for single-user system.

## 📁 Project Structure

```
src/
├── api/                    # Backend integration
│   ├── client.ts          # Axios instance with interceptors
│   └── chat.ts            # Chat API methods
│
├── components/             # React components
│   ├── Chat/              # Chat interface
│   │   ├── ChatBox.tsx
│   │   ├── MessageList.tsx
│   │   ├── Message.tsx
│   │   └── MessageInput.tsx
│   ├── Sidebar/           # Navigation sidebar
│   │   ├── Sidebar.tsx
│   │   ├── ConversationList.tsx
│   │   └── ConversationItem.tsx
│   ├── Settings/          # Settings modal
│   │   └── SettingsModal.tsx
│   └── Layout/            # Main layout
│       └── AppLayout.tsx
│
├── contexts/              # State management
│   └── ChatContext.tsx    # Chat state & actions
│
├── types/                 # TypeScript definitions
│   ├── api.ts            # Backend API types
│   └── chat.ts           # Frontend chat types
│
├── utils/                 # Helper functions
│   ├── constants.ts      # App constants
│   ├── storage.ts        # localStorage helpers
│   └── time.ts           # Time formatting
│
├── styles/
│   └── index.css         # Global styles + Tailwind
│
├── App.tsx               # Root component
└── main.tsx              # Entry point
```

## 🎨 Design System

### Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| **Background Primary** | `#343541` | Main background |
| **Background Secondary** | `#40414f` | Chat area, cards |
| **Background Hover** | `#444654` | Hover states |
| **Text Primary** | `#ececf1` | Main text |
| **Text Secondary** | `#acacbe` | Subtle text, timestamps |
| **Accent Green** | `#10a37f` | Primary actions, buttons |
| **Accent Blue** | `#19c37d` | Links, interactive |
| **Border** | `#565869` | Dividers, borders |
| **Error** | `#ef4444` | Errors, warnings |

### Typography

- **Font Family:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ...`
- **Sizes:** 12px (xs) → 16px (base) → 20px (xl)

### Icons

- **Library:** Lucide React
- **Style:** Monochrome, outline-based
- **Default Size:** 20px
- **Color:** Inherits from text color

## 🔌 Backend Integration

Connects to LangGraph FastAPI backend at `http://localhost:8080`:

### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Send message, get AI response |
| `/session/{id}` | GET | Get conversation details |
| `/session/{id}` | DELETE | Delete conversation |
| `/health` | GET | Backend health check |

### Request/Response Flow

1. User types message → MessageInput
2. ChatContext sends to `/chat` endpoint
3. Backend routes to appropriate agent (Food/Task/Event)
4. Response displayed in MessageList
5. Conversation saved to localStorage

## 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Framework** | React | 18.3+ |
| **Language** | TypeScript | 5.5+ |
| **Build Tool** | Vite | 5.4+ |
| **Styling** | Tailwind CSS | 3.4+ |
| **HTTP Client** | Axios | 1.7+ |
| **Icons** | Lucide React | 0.400+ |
| **State** | React Context | - |
| **Storage** | localStorage | - |

## 📱 Mobile App Ready

This WebUI is designed with future mobile app development in mind:

- ✅ **REST API** - Standard HTTP/JSON, framework-agnostic
- ✅ **State patterns** - Transferable to React Native/Flutter
- ✅ **Design system** - Documented colors, spacing, typography
- ✅ **Component architecture** - Modular, reusable

## 🧪 Development Commands

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Type check
npm run type-check

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## 🐳 Docker Deployment

See main AI Stack README for Docker deployment instructions.

Quick start:
```bash
# Build
docker build -t ai-stack-frontend .

# Run
docker run -p 3001:3001 -e VITE_BACKEND_URL=http://localhost:8080 ai-stack-frontend
```

## ⌨️ Keyboard Shortcuts

- **Enter** - Send message
- **Shift + Enter** - New line in message
- **Escape** - Close settings modal

## 🔒 Privacy

- ✅ **100% local** - All data in browser localStorage
- ✅ **No tracking** - Zero telemetry or analytics
- ✅ **Single-user** - Designed for personal use
- ✅ **No cloud** - Communicates only with local backend

## 📊 Bundle Size

Target: **< 250 KB** (gzipped)

Optimization strategies:
- Vite automatic code splitting
- Tailwind CSS purge unused classes
- Lucide React tree-shakeable imports
- No heavy dependencies

## 🐛 Troubleshooting

### Backend Connection Failed

**Issue:** "Network error: No response from server"

**Solutions:**
1. Check backend is running: `curl http://localhost:8080/health`
2. Verify `VITE_BACKEND_URL` in `.env`
3. Check CORS configuration in backend
4. Ensure ports are not blocked

### Conversations Not Persisting

**Issue:** Conversations disappear on refresh

**Solutions:**
1. Check browser localStorage is enabled
2. Check console for storage errors
3. Clear browser cache and try again
4. Check localStorage quota (max 5-10 MB)

### Build Errors

**Issue:** TypeScript or build errors

**Solutions:**
1. Delete `node_modules` and `package-lock.json`
2. Run `npm install` again
3. Clear Vite cache: `rm -rf node_modules/.vite`
4. Check Node.js version (requires 18+)

## 📚 Resources

- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Lucide Icons](https://lucide.dev/)

## 🤝 Contributing

This is a personal project, but suggestions are welcome! See main AI Stack README for development guidelines.

## 📄 License

MIT License - See main AI Stack repository

## 🔗 Related

- **Main README:** `../README.md`
- **Implementation Plan:** `../docs/CUSTOM_WEBUI_PLAN.md`
- **Backend Documentation:** `../containers/langgraph-agents/README.md`

---

**Built with ❤️ for AI Stack - 100% local, privacy-first AI assistant**
