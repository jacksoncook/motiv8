import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './DailyMotivation.css';

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "https://api.motiv8me.io";

interface DailyMotivationData {
  filename: string;
  s3_key: string;
  generated_at_millis: number;
}

// Helper function to get local date in YYYY-MM-DD format
const getLocalDateString = (date: Date = new Date()): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Helper function to get next workout day and localized time
const getNextWorkoutMessage = (workoutDays: Record<string, boolean>): string => {
  const dayOrder = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  // Get today's day index (0 = Sunday, 6 = Saturday)
  const today = new Date().getDay();

  // Find the next workout day
  let nextDayIndex = -1;
  for (let i = 1; i <= 7; i++) {
    const checkDay = (today + i) % 7;
    if (workoutDays[dayOrder[checkDay]]) {
      nextDayIndex = checkDay;
      break;
    }
  }

  if (nextDayIndex === -1) {
    return "No upcoming workout days scheduled";
  }

  // Create a date object for next workout day at 15:00 UTC
  const nextWorkoutDate = new Date();
  const daysUntilNext = (nextDayIndex - today + 7) % 7 || 7;
  nextWorkoutDate.setDate(nextWorkoutDate.getDate() + daysUntilNext);
  nextWorkoutDate.setUTCHours(15, 0, 0, 0);

  // Format the localized time
  const timeString = nextWorkoutDate.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });

  const dayName = dayNames[nextDayIndex];

  return `Next motivation arriving:\n${dayName} at ${timeString}`;
};

function DailyMotivation() {
  const { user } = useAuth();
  const [selectedDate, setSelectedDate] = useState<string>(
    getLocalDateString()
  );
  const [motivationData, setMotivationData] = useState<DailyMotivationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);

  useEffect(() => {
    if (!user) return;

    const fetchDailyMotivation = async () => {
      setLoading(true);
      setError(null);
      setImageLoaded(false);

      try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch(
          `${API_BASE_URL}/api/daily-motivation?date_str=${selectedDate}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          setMotivationData(data);
        } else if (response.status === 404) {
          // No image for this date
          setMotivationData(null);
        } else {
          const errorData = await response.json();
          setError(errorData.detail || 'Failed to fetch daily motivation');
        }
      } catch (err) {
        console.error('Error fetching daily motivation:', err);
        setError('Failed to fetch daily motivation');
      } finally {
        setLoading(false);
      }
    };

    fetchDailyMotivation();
  }, [selectedDate]);

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedDate(e.target.value);
  };

  return (
    <div className="daily-motivation-container">
      <div className="daily-motivation-section">
        <h2>Daily motivation</h2>

        {user?.workout_days && (
          <div className="next-workout-box">
            {getNextWorkoutMessage(user.workout_days)}
          </div>
        )}

        {loading && (
          <div className="motivation-image-container">
            <div className="image-loading-placeholder" />
          </div>
        )}

        {error && (
          <div className="motivation-message error">
            {error}
          </div>
        )}

        {!loading && !error && !motivationData && (
          <div className="rest-message">
            <h3>Rest up!</h3>
          </div>
        )}

        {!loading && motivationData && (
          <div className="motivation-image-container">
            {!imageLoaded && <div className="image-loading-placeholder" />}
            <img
              src={`${API_BASE_URL}/api/generated/${motivationData.filename}?token=${localStorage.getItem('auth_token')}`}
              alt="Daily motivation"
              className="motivation-image"
              onLoad={() => setImageLoaded(true)}
              style={{ display: imageLoaded ? 'block' : 'none' }}
            />
          </div>
        )}

        <div className="date-selector">
          <input
            type="date"
            id="motivation-date"
            value={selectedDate}
            onChange={handleDateChange}
            max={getLocalDateString()}
          />
        </div>
      </div>
    </div>
  );
}

export default DailyMotivation;
