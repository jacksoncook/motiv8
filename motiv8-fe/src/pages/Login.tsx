import { useAuth } from '../contexts/AuthContext';
import './Login.css';

function Login() {
  const { login, loginWithApple } = useAuth();

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
        <div className="login-buttons">
          <button onClick={login} className="social-login-button">
            <svg className="social-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
              <path fill="none" d="M0 0h48v48H0z"/>
            </svg>
            <span>Continue with Google</span>
          </button>
          <button onClick={loginWithApple} className="social-login-button">
            <svg className="social-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
              <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.7 9.05 7.4c1.39.07 2.35.74 3.15.8 1.19-.24 2.33-.93 3.6-.84 1.54.12 2.7.72 3.44 1.84-3.16 1.89-2.4 6.02.7 7.18-.57 1.52-1.32 3.01-2.89 3.9zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
            </svg>
            <span>Continue with Apple</span>
          </button>
        </div>
        <p className="login-footer">
          Free to use · No spam · Private by default
        </p>
      </div>
    </div>
  );
}

export default Login;
