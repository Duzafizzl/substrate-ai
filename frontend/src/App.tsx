import { useEffect, useState } from 'react';
import ChatScreen from './screens/ChatScreen';
import RoomsScreen from './screens/RoomsScreen';
import TasksScreen from './screens/TasksScreen';
import { setupNotifications } from './lib/notify';
import { ChatProvider } from './contexts/ChatContext';
import RadialBackground from './components/ui/RadialBackground';
import WelcomeModal from './components/WelcomeModal';

type ViewType = 'chat' | 'rooms' | 'tasks';

function App() {
  const [setupComplete, setSetupComplete] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [currentView, setCurrentView] = useState<ViewType>('chat');

  useEffect(() => {
    // Request notification permission and setup
    setupNotifications();
  }, []);

  const handleSetupComplete = () => {
    setSetupComplete(true);
    setShowSettings(false);
  };

  const handleOpenSettings = () => {
    setShowSettings(true);
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'rooms':
        return <RoomsScreen onBack={() => setCurrentView('chat')} />;
      case 'tasks':
        return <TasksScreen onBack={() => setCurrentView('chat')} />;
      default:
        return (
          <ChatScreen 
            onNavigateToRooms={() => setCurrentView('rooms')} 
            onNavigateToTasks={() => setCurrentView('tasks')}
            onOpenSettings={handleOpenSettings}
          />
        );
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <RadialBackground />
      
      {/* Welcome/Settings Modal - show on first setup OR when settings opened */}
      {(!setupComplete || showSettings) && (
        <WelcomeModal onComplete={handleSetupComplete} isSettingsMode={showSettings} />
      )}
      
      {/* Main App - only show after setup */}
      {setupComplete && (
        <ChatProvider>
          {renderCurrentView()}
        </ChatProvider>
      )}
    </div>
  );
}

export default App;

