import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import Toast from './Toast';
import './AntiMotivationMode.css';

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "https://api.motiv8me.io";

type Mode = 'shame' | 'toned' | 'ripped';

const MODE_INFO: Record<Mode, { label: string; description: string; emoji: string }> = {
  shame: {
    label: 'Shame',
    description: 'Receive harrowing images of what would happen if you skipped your daily workout.',
    emoji: '💀',
  },
  toned: {
    label: 'Toned',
    description: 'Get motivated with images showing a fit, toned physique.',
    emoji: '🦵',
  },
  ripped: {
    label: 'Ripped',
    description: 'Push yourself with images of a muscular, ripped physique.',
    emoji: '💪',
  },
};

function AntiMotivationMode() {
  const { user, updateUser } = useAuth();
  const [mode, setMode] = useState<Mode | null>(null);
  const [showOptions, setShowOptions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);

  // Load mode from user data
  useEffect(() => {
    if (user?.mode) {
      setMode(user.mode as Mode);
    }
  }, [user]);

  const handleModeChange = async (newMode: Mode) => {
    setMode(newMode);
    setError(null);
    setSaving(true);
    setShowOptions(false);

    try {
      const token = localStorage.getItem('auth_token');
      await axios.put(
        `${API_BASE_URL}/api/mode`,
        { mode: newMode },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      // Update user data in context to stay in sync
      updateUser({ mode: newMode });

      // Show success toast
      setShowToast(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update mode');
      // Revert on error
      setMode(user?.mode as Mode || mode);
    } finally {
      setSaving(false);
    }
  };

  const currentModeInfo = mode ? MODE_INFO[mode] : null;

  return (
    <div className="anti-motivation-container">
      {currentModeInfo && (
        <div className="mode-display">
          <button
            className="mode-button"
            onClick={() => setShowOptions(!showOptions)}
            disabled={saving}
            title={currentModeInfo.description}
          >
            <span className="mode-label">
              <span className="mode-emoji">{currentModeInfo.emoji}</span>
              {currentModeInfo.label} mode
            </span>
          </button>
        </div>
      )}

      {showOptions && (
        <div className="mode-options">
          {(Object.keys(MODE_INFO) as Mode[])
            .filter((m) => m !== mode)
            .map((m) => (
              <button
                key={m}
                className="mode-option"
                onClick={() => handleModeChange(m)}
                disabled={saving}
              >
                <span className="mode-option-label">
                  <span className="mode-emoji">{MODE_INFO[m].emoji}</span>
                  {MODE_INFO[m].label}
                </span>
                <span className="mode-option-description">{MODE_INFO[m].description}</span>
              </button>
            ))}
        </div>
      )}

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {showToast && (
        <Toast
          message="Mode updated"
          type="success"
          duration={2500}
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
}

export default AntiMotivationMode;
