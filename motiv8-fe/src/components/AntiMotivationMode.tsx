import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import Toast from './Toast';
import './AntiMotivationMode.css';

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "https://api.motiv8me.io";

function AntiMotivationMode() {
  const { user, updateUser } = useAuth();
  const [antiMotivationMode, setAntiMotivationMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);

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

      // Update user data in context to stay in sync
      updateUser({ anti_motivation_mode: newMode });

      // Show success toast
      setShowToast(true);
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
      <div className="header-with-tooltip">
        <h2>Shame mode</h2>
        <div className="tooltip-container">
          <span className="info-icon">ⓘ</span>
          <div className="tooltip-content">
            When enabled, you will receive harrowing images of what would happen if you skipped your daily workout.
          </div>
        </div>
        <input
          type="checkbox"
          checked={antiMotivationMode}
          onChange={handleToggle}
          disabled={saving}
          className="toggle-checkbox"
        />
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {showToast && (
        <Toast
          message="Settings saved"
          type="success"
          duration={2500}
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
}

export default AntiMotivationMode;
