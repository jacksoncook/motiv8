import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "https://api.motiv8me.io";

interface User {
  id: string;
  email: string;
  created_at: string;
  has_selfie: boolean;
  selfie_filename: string | null;
  selfie_embedding_filename: string | null;
  gender: string | null;
  workout_days: Record<string, boolean>;
  anti_motivation_mode: boolean;
  mode: string | null;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  setToken: (token: string) => void;
  refreshUser: () => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load user from token on mount, check URL first for OAuth callback
  useEffect(() => {
    // Check if there's a token in the URL (OAuth callback)
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token');

    if (tokenFromUrl) {
      // Save token and remove from URL
      localStorage.setItem('auth_token', tokenFromUrl);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
      fetchUser(tokenFromUrl);
      return;
    }

    // Otherwise check localStorage
    const token = localStorage.getItem('auth_token');
    if (token) {
      fetchUser(token);
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchUser = async (token: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      localStorage.removeItem('auth_token');
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUser = async () => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      await fetchUser(token);
    }
  };

  const login = () => {
    // Redirect to backend OAuth login
    window.location.href = `${API_BASE_URL}/auth/login`;
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
  };

  const setToken = (token: string) => {
    localStorage.setItem('auth_token', token);
    fetchUser(token);
  };

  const updateUser = (updates: Partial<User>) => {
    setUser((prevUser) => {
      if (!prevUser) return prevUser;
      return { ...prevUser, ...updates };
    });
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, setToken, refreshUser, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
