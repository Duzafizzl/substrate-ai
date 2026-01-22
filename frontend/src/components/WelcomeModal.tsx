import { useState, useEffect } from 'react';

interface SetupStatus {
  needs_setup: boolean;
  has_api_key: boolean;
  api_key_valid: boolean;
  message: string;
}

interface WelcomeModalProps {
  onComplete: () => void;
  isSettingsMode?: boolean;
}

export default function WelcomeModal({ onComplete, isSettingsMode = false }: WelcomeModalProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8284';

  // Check setup status on mount
  useEffect(() => {
    // In settings mode, always show the modal immediately
    if (isSettingsMode) {
      setIsVisible(true);
      setIsLoading(false);
    } else {
      checkSetupStatus();
    }
  }, [isSettingsMode]);

  const checkSetupStatus = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_URL}/api/setup/status`);
      
      if (!response.ok) {
        // Backend might not be running yet
        setIsVisible(true);
        setError('Cannot connect to backend. Make sure the server is running.');
        return;
      }
      
      const status: SetupStatus = await response.json();
      if (status.needs_setup) {
        setIsVisible(true);
      } else {
        // Already configured, skip the modal
        onComplete();
      }
    } catch (err) {
      // Backend not reachable - show modal with connection error
      setIsVisible(true);
      setError('Cannot connect to backend. Make sure the server is running on port 8284.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveKey = async () => {
    if (!apiKey.trim()) {
      setError('Please enter your API key');
      return;
    }

    if (!apiKey.startsWith('sk-or-v1-')) {
      setError('OpenRouter API keys should start with sk-or-v1-');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/setup/api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, verify: true }),
      });

      const result = await response.json();

      if (result.success) {
        setSuccess(true);
        // Wait a moment to show success message
        setTimeout(() => {
          setIsVisible(false);
          onComplete();
        }, 1500);
      } else {
        setError(result.message || 'Failed to save API key');
      }
    } catch (err) {
      setError('Failed to save API key. Is the backend running?');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSkip = () => {
    setIsVisible(false);
    onComplete();
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      
      {/* Modal */}
      <div className="relative w-full max-w-lg bg-gradient-to-b from-slate-900 to-slate-950 rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden">
        {/* Decorative top border */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500" />
        
        {/* Content */}
        <div className="p-8">
          {/* Logo & Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 mb-4">
              <span className="text-3xl">{isSettingsMode ? '⚙️' : '🧠'}</span>
            </div>
            <h1 className="text-2xl font-bold text-white mb-2">
              {isSettingsMode ? 'Settings' : 'Welcome to Substrate AI'}
            </h1>
            <p className="text-slate-400">
              {isSettingsMode ? 'Manage your API key and configuration' : 'Your production-ready AI agent framework'}
            </p>
          </div>

          {isLoading ? (
            <div className="flex flex-col items-center py-8">
              <div className="w-8 h-8 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin mb-4" />
              <p className="text-slate-400">Checking configuration...</p>
            </div>
          ) : success ? (
            <div className="flex flex-col items-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/20 mb-4">
                <span className="text-3xl">✅</span>
              </div>
              <p className="text-green-400 text-lg font-medium">API Key Saved!</p>
              <p className="text-slate-400 mt-2">Starting Substrate AI...</p>
            </div>
          ) : (
            <>
              {/* Setup Instructions */}
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <span className="text-yellow-400">🔑</span>
                  Enter your OpenRouter API Key
                </h2>
                <p className="text-slate-400 text-sm mb-4">
                  Substrate AI uses OpenRouter to access 100+ AI models. 
                  Get your free API key at{' '}
                  <a 
                    href="https://openrouter.ai/keys" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-purple-400 hover:text-purple-300 underline"
                  >
                    openrouter.ai/keys
                  </a>
                </p>

                {/* API Key Input */}
                <div className="relative">
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => {
                      setApiKey(e.target.value);
                      setError(null);
                    }}
                    placeholder="sk-or-v1-..."
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                    disabled={isSaving}
                  />
                  {apiKey && (
                    <button
                      type="button"
                      onClick={() => setApiKey('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      ✕
                    </button>
                  )}
                </div>

                {/* Error Message */}
                {error && (
                  <div className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <p className="text-red-400 text-sm flex items-center gap-2">
                      <span>❌</span>
                      {error}
                    </p>
                  </div>
                )}
              </div>

              {/* Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleSkip}
                  className="flex-1 px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors"
                  disabled={isSaving}
                >
                  {isSettingsMode ? 'Close' : 'Skip for now'}
                </button>
                <button
                  onClick={handleSaveKey}
                  disabled={!apiKey || isSaving}
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isSaving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      Save & Continue
                      <span>→</span>
                    </>
                  )}
                </button>
              </div>

              {/* Help Text */}
              <div className="mt-6 pt-6 border-t border-slate-800">
                <h3 className="text-sm font-medium text-slate-300 mb-2">
                  💡 Don't have an API key yet?
                </h3>
                <ol className="text-sm text-slate-400 space-y-1.5 ml-4 list-decimal">
                  <li>
                    Go to{' '}
                    <a 
                      href="https://openrouter.ai" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:text-purple-300"
                    >
                      openrouter.ai
                    </a>
                  </li>
                  <li>Sign up (Google/GitHub/Email)</li>
                  <li>Navigate to API Keys section</li>
                  <li>Create a new key (it's free!)</li>
                  <li>Paste it above</li>
                </ol>
              </div>

              {/* Features Preview */}
              <div className="mt-6 p-4 bg-slate-800/50 rounded-lg">
                <h3 className="text-sm font-medium text-slate-300 mb-3">
                  ✨ What you'll get:
                </h3>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                  <div className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    100+ AI Models
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Memory System
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    30+ Built-in Tools
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Real-time Streaming
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Graph RAG
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Code Execution
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

