import { useAuth } from '../contexts/AuthContext';
import './Header.css';

function Header() {
  const { user, isLoading, login, logout } = useAuth();

  return (
    <header className="app-header">
      <div className="header-container">
        <h1 className="app-title">Motiv8</h1>
        <div className="auth-section">
          {isLoading ? (
            <span>Loading...</span>
          ) : user ? (
            <div className="user-info">
              <span className="user-email">{user.email}</span>
              <button onClick={logout} className="auth-button">
                Logout
              </button>
            </div>
          ) : (
            <button onClick={login} className="auth-button">
              Login with Google
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
