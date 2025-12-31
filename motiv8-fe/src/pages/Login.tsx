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
        <h1 className="login-headline">
          A little motivation—
          <br />
          right when you need it most
        </h1>
        <p className="login-tagline">
          Short, encouraging emails tailored to your schedule
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
