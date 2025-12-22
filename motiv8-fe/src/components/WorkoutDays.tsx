import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './WorkoutDays.css';

const API_BASE_URL = window.location.origin;

const DAYS_OF_WEEK = [
  { key: 'monday', label: 'Monday' },
  { key: 'tuesday', label: 'Tuesday' },
  { key: 'wednesday', label: 'Wednesday' },
  { key: 'thursday', label: 'Thursday' },
  { key: 'friday', label: 'Friday' },
  { key: 'saturday', label: 'Saturday' },
  { key: 'sunday', label: 'Sunday' },
];

function WorkoutDays() {
  const { user, refreshUser } = useAuth();
  const [workoutDays, setWorkoutDays] = useState<Record<string, boolean>>({
    monday: false,
    tuesday: false,
    wednesday: false,
    thursday: false,
    friday: false,
    saturday: false,
    sunday: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load workout days from user data
  useEffect(() => {
    if (user?.workout_days) {
      setWorkoutDays(user.workout_days);
    }
  }, [user]);

  const handleToggle = async (day: string) => {
    const newWorkoutDays = {
      ...workoutDays,
      [day]: !workoutDays[day],
    };

    setWorkoutDays(newWorkoutDays);
    setError(null);
    setSaving(true);

    try {
      const token = localStorage.getItem('auth_token');
      await axios.put(
        `${API_BASE_URL}/api/workout-days`,
        { workout_days: newWorkoutDays },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      // Refresh user data to stay in sync
      await refreshUser();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update workout days');
      // Revert on error
      setWorkoutDays(user?.workout_days || workoutDays);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="workout-days-container">
      <h2>Work out days</h2>

      <div className="days-grid">
        {DAYS_OF_WEEK.map((day) => (
          <div key={day.key} className="day-toggle">
            <label className="day-label">
              <input
                type="checkbox"
                checked={workoutDays[day.key] || false}
                onChange={() => handleToggle(day.key)}
                disabled={saving}
                className="day-checkbox"
              />
              <span className="day-name">{day.label}</span>
            </label>
          </div>
        ))}
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

export default WorkoutDays;
