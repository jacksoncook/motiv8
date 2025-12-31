import { useAuth } from '../contexts/AuthContext';
import './Login.css';

function Login() {
  const { login } = useAuth();

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <img src="/motiv8.png" alt="motiv8me Logo" className="login-logo" />
        </div>
        <p className="login-tagline">
          Personalized motivational emails to help you reach new heights
        </p>
        <button onClick={login} className="google-login-button">
          Continue with Google
        </button>
        <p className="login-footer">
          Free to use · No spam · Private by default
        </p>
      </div>
    </div>
  );
}

export default Login;
