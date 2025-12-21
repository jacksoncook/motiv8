import { useAuth } from '../contexts/AuthContext';
import './Login.css';

function Login() {
  const { login } = useAuth();

  return (
    <div className="login-container">
      <div className="login-box">
        <h1 className="login-title">Motiv8</h1>
        <button onClick={login} className="google-login-button">
          Login with Google
        </button>
      </div>
    </div>
  );
}

export default Login;
