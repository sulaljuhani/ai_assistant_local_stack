import { useState, useEffect } from 'react';
import { X, CheckCircle, XCircle, Loader2, Save } from 'lucide-react';
import { useChat } from '../../contexts/ChatContext';
import { chatApi } from '../../api/chat';
import { USER_ID, WORKSPACE } from '../../utils/constants';
import { loadApiSettings, saveApiSettings, type ApiSettings } from '../../utils/storage';
import { useToast } from '../../contexts/ToastContext';

interface SettingsModalProps {
  onClose: () => void;
}

type TabType = 'general' | 'api';

export const SettingsModal: React.FC<SettingsModalProps> = ({ onClose }) => {
  const { clearAllConversations } = useChat();
  const { showSuccess, showError } = useToast();
  const [activeTab, setActiveTab] = useState<TabType>('general');
  const [backendStatus, setBackendStatus] = useState<'loading' | 'online' | 'offline'>('loading');
  const [apiSettings, setApiSettings] = useState<ApiSettings>(() => loadApiSettings());

  // Check backend health on mount
  useEffect(() => {
    let isCancelled = false;

    const checkHealth = async () => {
      try {
        await chatApi.healthCheck();
        if (!isCancelled) {
          setBackendStatus('online');
        }
      } catch {
        if (!isCancelled) {
          setBackendStatus('offline');
        }
      }
    };

    checkHealth();

    return () => {
      isCancelled = true;
    };
  }, []);

  const handleClearAll = () => {
    if (confirm('Are you sure you want to delete all conversations? This cannot be undone.')) {
      clearAllConversations();
      onClose();
    }
  };

  const handleSaveApiSettings = () => {
    try {
      // Validation
      if (apiSettings.provider === 'ollama') {
        if (!apiSettings.ollamaUrl.trim()) {
          showError('Ollama URL is required');
          return;
        }
        if (!apiSettings.ollamaModel.trim()) {
          showError('Ollama model is required');
          return;
        }
      } else if (apiSettings.provider === 'openai') {
        if (!apiSettings.openaiApiKey.trim()) {
          showError('OpenAI API key is required');
          return;
        }
        if (!apiSettings.openaiModel.trim()) {
          showError('OpenAI model is required');
          return;
        }
      }

      saveApiSettings(apiSettings);
      showSuccess('API settings saved successfully');
    } catch (error) {
      console.error('Failed to save API settings:', error);
      showError('Failed to save API settings');
    }
  };

  const updateApiSetting = <K extends keyof ApiSettings>(key: K, value: ApiSettings[K]) => {
    setApiSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-bg-secondary rounded-lg shadow-2xl">
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

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setActiveTab('general')}
            className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'general'
                ? 'text-accent-green border-b-2 border-accent-green'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            General
          </button>
          <button
            onClick={() => setActiveTab('api')}
            className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
              activeTab === 'api'
                ? 'text-accent-green border-b-2 border-accent-green'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            API Settings
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
          {/* General Tab */}
          {activeTab === 'general' && (
            <>
              {/* Backend URL */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Backend URL
                </label>
                <input
                  type="text"
                  value={import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'}
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
            </>
          )}

          {/* API Settings Tab */}
          {activeTab === 'api' && (
            <>
              <div className="space-y-4">
                {/* Provider Selection */}
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    API Provider
                  </label>
                  <div className="flex gap-3">
                    <button
                      onClick={() => updateApiSetting('provider', 'ollama')}
                      className={`flex-1 px-4 py-2.5 rounded-lg font-medium transition-colors ${
                        apiSettings.provider === 'ollama'
                          ? 'bg-accent-green text-white'
                          : 'bg-input-bg text-text-secondary hover:bg-bg-hover'
                      }`}
                    >
                      Ollama
                    </button>
                    <button
                      onClick={() => updateApiSetting('provider', 'openai')}
                      className={`flex-1 px-4 py-2.5 rounded-lg font-medium transition-colors ${
                        apiSettings.provider === 'openai'
                          ? 'bg-accent-green text-white'
                          : 'bg-input-bg text-text-secondary hover:bg-bg-hover'
                      }`}
                    >
                      OpenAI
                    </button>
                  </div>
                  <p className="text-xs text-text-secondary mt-1">
                    Choose your preferred AI provider
                  </p>
                </div>

                {/* Ollama Settings */}
                {apiSettings.provider === 'ollama' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        Ollama URL
                      </label>
                      <input
                        type="text"
                        value={apiSettings.ollamaUrl}
                        onChange={(e) => updateApiSetting('ollamaUrl', e.target.value)}
                        placeholder="http://localhost:11434"
                        className="w-full px-3 py-2 bg-input-bg border border-input-border rounded-lg
                                 text-text-primary text-sm focus:outline-none focus:ring-2
                                 focus:ring-accent-green"
                      />
                      <p className="text-xs text-text-secondary mt-1">
                        URL of your Ollama instance
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        Model
                      </label>
                      <input
                        type="text"
                        value={apiSettings.ollamaModel}
                        onChange={(e) => updateApiSetting('ollamaModel', e.target.value)}
                        placeholder="llama3.2:3b"
                        className="w-full px-3 py-2 bg-input-bg border border-input-border rounded-lg
                                 text-text-primary text-sm focus:outline-none focus:ring-2
                                 focus:ring-accent-green"
                      />
                      <p className="text-xs text-text-secondary mt-1">
                        Model name (e.g., llama3.2:3b, mistral, codellama)
                      </p>
                    </div>
                  </>
                )}

                {/* OpenAI Settings */}
                {apiSettings.provider === 'openai' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        API Key
                      </label>
                      <input
                        type="password"
                        value={apiSettings.openaiApiKey}
                        onChange={(e) => updateApiSetting('openaiApiKey', e.target.value)}
                        placeholder="sk-..."
                        className="w-full px-3 py-2 bg-input-bg border border-input-border rounded-lg
                                 text-text-primary text-sm font-mono focus:outline-none focus:ring-2
                                 focus:ring-accent-green"
                      />
                      <p className="text-xs text-text-secondary mt-1">
                        Your OpenAI API key (stored locally)
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        Model
                      </label>
                      <input
                        type="text"
                        value={apiSettings.openaiModel}
                        onChange={(e) => updateApiSetting('openaiModel', e.target.value)}
                        placeholder="gpt-4"
                        className="w-full px-3 py-2 bg-input-bg border border-input-border rounded-lg
                                 text-text-primary text-sm focus:outline-none focus:ring-2
                                 focus:ring-accent-green"
                      />
                      <p className="text-xs text-text-secondary mt-1">
                        Model name (e.g., gpt-4, gpt-3.5-turbo)
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        Base URL (Optional)
                      </label>
                      <input
                        type="text"
                        value={apiSettings.openaiBaseUrl}
                        onChange={(e) => updateApiSetting('openaiBaseUrl', e.target.value)}
                        placeholder="https://api.openai.com/v1"
                        className="w-full px-3 py-2 bg-input-bg border border-input-border rounded-lg
                                 text-text-primary text-sm focus:outline-none focus:ring-2
                                 focus:ring-accent-green"
                      />
                      <p className="text-xs text-text-secondary mt-1">
                        Custom API endpoint for OpenAI-compatible APIs
                      </p>
                    </div>
                  </>
                )}

                {/* Save Button */}
                <div className="pt-4 border-t border-border">
                  <button
                    onClick={handleSaveApiSettings}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5
                             bg-accent-green hover:bg-accent-green-hover rounded-lg
                             text-white font-medium transition-colors min-h-[44px]"
                  >
                    <Save className="w-5 h-5" />
                    Save API Settings
                  </button>
                  <p className="text-xs text-text-secondary mt-2 text-center">
                    Settings are stored locally in your browser
                  </p>
                </div>

                {/* Info */}
                <div className="pt-4 border-t border-border">
                  <div className="bg-input-bg border border-input-border rounded-lg p-3">
                    <p className="text-xs text-text-secondary">
                      <strong className="text-text-primary">Note:</strong> These settings configure
                      which AI provider the frontend will use for chat. Make sure your chosen provider
                      is running and accessible.
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
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
