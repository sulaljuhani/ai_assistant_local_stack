import { ChatProvider } from './contexts/ChatContext';
import { ToastProvider } from './contexts/ToastContext';
import { AppLayout } from './components/Layout/AppLayout';

function App() {
  return (
    <ToastProvider>
      <ChatProvider>
        <AppLayout />
      </ChatProvider>
    </ToastProvider>
  );
}

export default App;
