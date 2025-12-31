import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './AntiMotivationMode.css';

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "https://api.motiv8me.io";

function AntiMotivationMode() {
  const { user, refreshUser } = useAuth();
  const [antiMotivationMode, setAntiMotivationMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load anti-motivation mode from user data
  useEffect(() => {
    if (user?.anti_motivation_mode !== undefined) {
      setAntiMotivationMode(user.anti_motivation_mode);
    }
  }, [user]);

  const handleToggle = async () => {
    const newMode = !antiMotivationMode;

    setAntiMotivationMode(newMode);
    setError(null);
    setSaving(true);

    try {
      const token = localStorage.getItem('auth_token');
      await axios.put(
        `${API_BASE_URL}/api/anti-motivation-mode`,
        { anti_motivation_mode: newMode },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      // Refresh user data to stay in sync
      await refreshUser();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update anti-motivation mode');
      // Revert on error
      setAntiMotivationMode(user?.anti_motivation_mode || antiMotivationMode);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="anti-motivation-container">
      <div className="header-container">
        <h2>Anti-motivation mode</h2>
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={antiMotivationMode}
            onChange={handleToggle}
            disabled={saving}
            className="toggle-checkbox"
          />
          <span className="toggle-text">
            {antiMotivationMode ? 'Enabled' : 'Disabled'}
          </span>
        </label>
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {saving && (
        <div className="saving-message">
          Saving...
        </div>
      )}
    </div>
  );
}

export default AntiMotivationMode;
