import { useState, useEffect } from 'react';
import { X, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { useChat } from '../../contexts/ChatContext';
import { chatApi } from '../../api/chat';
import { USER_ID, WORKSPACE } from '../../utils/constants';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { clearAllConversations } = useChat();
  const [backendStatus, setBackendStatus] = useState<'loading' | 'online' | 'offline'>('loading');

  // Check backend health when modal opens
  useEffect(() => {
    if (isOpen) {
      setBackendStatus('loading');
      chatApi.healthCheck()
        .then(() => setBackendStatus('online'))
        .catch(() => setBackendStatus('offline'));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleClearAll = () => {
    if (confirm('Are you sure you want to delete all conversations? This cannot be undone.')) {
      clearAllConversations();
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md mx-4 bg-bg-secondary rounded-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-semibold text-text-primary">Settings</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-bg-hover transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-text-secondary" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Backend URL */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              Backend URL
            </label>
            <input
              type="text"
              value={import.meta.env.VITE_BACKEND_URL || 'http://localhost:8080'}
              disabled
              className="w-full px-3 py-2 bg-input-bg border border-input-border rounded-lg
                       text-text-secondary text-sm"
            />
            <p className="text-xs text-text-secondary mt-1">
              Configure in .env file
            </p>
          </div>

          {/* User ID */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              User ID
            </label>
            <input
              type="text"
              value={USER_ID}
              disabled
              className="w-full px-3 py-2 bg-input-bg border border-input-border rounded-lg
                       text-text-secondary text-sm font-mono"
            />
            <p className="text-xs text-text-secondary mt-1">
              Single-user system (hardcoded)
            </p>
          </div>

          {/* Workspace */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              Workspace
            </label>
            <input
              type="text"
              value={WORKSPACE}
              disabled
              className="w-full px-3 py-2 bg-input-bg border border-input-border rounded-lg
                       text-text-secondary text-sm"
            />
          </div>

          {/* Backend Status */}
          <div className="pt-4 border-t border-border">
            <label className="block text-sm font-medium text-text-primary mb-2">
              Backend Status
            </label>
            <div className="flex items-center gap-2 px-3 py-2 bg-input-bg border border-input-border rounded-lg">
              {backendStatus === 'loading' && (
                <>
                  <Loader2 className="w-4 h-4 text-text-secondary animate-spin" />
                  <span className="text-sm text-text-secondary">Checking...</span>
                </>
              )}
              {backendStatus === 'online' && (
                <>
                  <CheckCircle className="w-4 h-4 text-accent-green" />
                  <span className="text-sm text-accent-green">Connected</span>
                </>
              )}
              {backendStatus === 'offline' && (
                <>
                  <XCircle className="w-4 h-4 text-error" />
                  <span className="text-sm text-error">Offline</span>
                </>
              )}
            </div>
          </div>

          {/* Clear All */}
          <div className="pt-4 border-t border-border">
            <button
              onClick={handleClearAll}
              className="w-full px-4 py-2.5 bg-error hover:bg-error/90 rounded-lg
                       text-white font-medium transition-colors min-h-[44px]"
            >
              Clear All Conversations
            </button>
            <p className="text-xs text-text-secondary mt-2 text-center">
              This will delete all local conversations
            </p>
          </div>

          {/* About */}
          <div className="pt-4 border-t border-border text-center">
            <p className="text-sm text-text-primary font-medium">AI Stack WebUI</p>
            <p className="text-xs text-text-secondary mt-1">
              Version 1.0.0
            </p>
            <p className="text-xs text-text-secondary mt-2">
              Multi-agent chat interface for LangGraph backend
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-border">
          <button
            onClick={onClose}
            className="w-full px-4 py-2.5 bg-accent-green hover:bg-accent-green-hover
                     rounded-lg text-white font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
