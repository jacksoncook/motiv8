import { useAuth } from '../contexts/AuthContext';
import './Login.css';

function Login() {
  const { login } = useAuth();

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <img src="/motiv8.png" alt="Motiv8 Logo" className="login-logo" />
          <h1 className="login-title">Motiv8</h1>
        </div>
        <button onClick={login} className="google-login-button">
          Login with Google
        </button>
      </div>
    </div>
  );
}

export default Login;
