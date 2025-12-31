import { useAuth } from '../contexts/AuthContext';
import './Header.css';

function Header() {
  const { user, isLoading, login, logout } = useAuth();

  return (
    <header className="app-header">
      <div className="header-container">
        <div className="header-title-section">
          <img src="/motiv8.png" alt="motiv8me Logo" className="header-logo" />
          <h1 className="app-title">motiv8me</h1>
        </div>
        <div className="auth-section">
          {isLoading ? (
            <span>Loading...</span>
          ) : user ? (
            <button onClick={logout} className="auth-button">
              Logout
            </button>
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
