import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './DailyMotivation.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface DailyMotivationData {
  filename: string;
  s3_key: string;
  generated_at_millis: number;
}

function DailyMotivation() {
  const { user } = useAuth();
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [motivationData, setMotivationData] = useState<DailyMotivationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    const fetchDailyMotivation = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${API_URL}/api/daily-motivation?date_str=${selectedDate}`,
          {
            credentials: 'include',
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
  }, [user, selectedDate]);

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedDate(e.target.value);
  };

  return (
    <div className="daily-motivation-container">
      <div className="daily-motivation-section">
        <h2>Daily Motivation</h2>

        <div className="date-selector">
          <label htmlFor="motivation-date">Select Date:</label>
          <input
            type="date"
            id="motivation-date"
            value={selectedDate}
            onChange={handleDateChange}
            max={new Date().toISOString().split('T')[0]}
          />
        </div>

        {loading && (
          <div className="motivation-message loading">
            Loading...
          </div>
        )}

        {error && (
          <div className="motivation-message error">
            {error}
          </div>
        )}

        {!loading && !error && !motivationData && (
          <div className="rest-message">
            <h3>Rest Up!</h3>
          </div>
        )}

        {!loading && motivationData && (
          <div className="motivation-image-container">
            <img
              src={`${API_URL}/api/generated/${motivationData.filename}`}
              alt="Daily Motivation"
              className="motivation-image"
            />
            <div className="generated-timestamp">
              Generated: {new Date(motivationData.generated_at_millis).toLocaleString()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DailyMotivation;
