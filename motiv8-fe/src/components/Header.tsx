import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Header.css';

function Header({ showNav }: { showNav?: boolean }) {
  const { user, isLoading, login, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <header className="app-header">
      <div className="header-container">
        <div className="header-title-section" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <img src="/motiv8.png" alt="motiv8me Logo" className="header-logo" />
          <h1 className="app-title">motiv8me</h1>
        </div>
        <div className="auth-section">
          {isLoading ? (
            <span>Loading...</span>
          ) : user ? (
            <>
              {showNav && (
                <>
                  <button
                    onClick={() => navigate('/')}
                    className={`auth-button secondary-button${location.pathname === '/' ? ' active' : ''}`}
                  >
                    Home
                  </button>
                  <button
                    onClick={() => navigate('/settings')}
                    className={`auth-button secondary-button${location.pathname === '/settings' ? ' active' : ''}`}
                  >
                    Settings
                  </button>
                </>
              )}
              <button onClick={logout} className="auth-button">
                Logout
              </button>
            </>
          ) : (
            <button onClick={login} className="auth-button">
              Login with google
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
