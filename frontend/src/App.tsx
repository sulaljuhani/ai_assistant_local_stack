import { ChatProvider } from './contexts/ChatContext';
import { AppLayout } from './components/Layout/AppLayout';

function App() {
  return (
    <ChatProvider>
      <AppLayout />
    </ChatProvider>
  );
}

export default App;
