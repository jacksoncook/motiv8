import './App.css'
import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Header from './components/Header'
import AuthCallback from './pages/AuthCallback'
import Login from './pages/Login'
import ImageUpload from './components/ImageUpload'
import DailyMotivation from './components/DailyMotivation'
import WorkoutDays from './components/WorkoutDays'
import AntiMotivationMode from './components/AntiMotivationMode'
import Toast from './components/Toast'

type OnboardingStep = 'upload' | 'settings' | null

function AppContent() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [onboarding, setOnboarding] = useState<OnboardingStep>(null);
  const [showWelcomeToast, setShowWelcomeToast] = useState(false);

  // Determine onboarding state once user loads
  useEffect(() => {
    if (user && onboarding === null && !user.has_selfie) {
      setOnboarding('upload');
    }
  }, [user]);

  // Advance to preferences step once selfie is uploaded
  useEffect(() => {
    if (onboarding === 'upload' && user?.has_selfie) {
      setOnboarding('settings');
    }
  }, [user?.has_selfie]);

  if (isLoading || (user && !user.has_selfie && onboarding === null)) {
    return <div className="loading-container"><p>Loading...</p></div>;
  }

  if (!user) return <Login />;

  // Onboarding overrides all routes
  if (onboarding === 'upload') {
    return (
      <div className="app">
        <Header />
        <div className="screen-container">
          <ImageUpload selfieHeading="Upload a selfie" />
        </div>
      </div>
    );
  }

  if (onboarding === 'settings') {
    return (
      <div className="app">
        <Header />
        <div className="screen-container">
          <div className="settings-stack">
            <WorkoutDays />
            <AntiMotivationMode />
          </div>
          <button className="confirm-button" onClick={() => { setOnboarding(null); setShowWelcomeToast(true); navigate('/'); }}>
            Let's go
          </button>
        </div>
      </div>
    );
  }

  const onSettings = location.pathname === '/settings';

  return (
    <Routes>
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="*" element={
        <div className="app">
          <Header showNav />

          {/* Always mounted — toggled via CSS to avoid remount/refetch */}
          <div style={{ display: onSettings ? 'none' : '' }}>
            <div className="home-container">
              <DailyMotivation />
            </div>
          </div>

          <div style={{ display: onSettings ? '' : 'none' }}>
            <div className="screen-container">
              <div className="edit-settings-grid">
                <ImageUpload selfieHeading="Selfie" />
                <div className="settings-stack">
                  <WorkoutDays />
                  <AntiMotivationMode />
                </div>
              </div>
            </div>
          </div>

          {showWelcomeToast && (
            <Toast message="Welcome to motiv8me!" type="success" duration={3000} onClose={() => setShowWelcomeToast(false)} />
          )}
        </div>
      } />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
