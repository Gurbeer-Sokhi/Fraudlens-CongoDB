import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import RiskBadge from '../components/RiskBadge';
import { severityIcon } from '../utils/helpers';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await api.alerts(50);
      setAlerts(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const handleClick = (alert) => {
    if (alert.entity_type === 'person') {
      navigate(`/search?person=${alert.entity_id}`);
    }
  };

  if (loading) return <LoadingSpinner message="Scanning for fraud patterns..." />;
  if (error) return <div className="error-banner">{error}</div>;

  const grouped = {
    critical: alerts.filter((a) => a.severity === 'critical'),
    high: alerts.filter((a) => a.severity === 'high'),
    medium: alerts.filter((a) => ['medium', 'low'].includes(a.severity)),
  };

  return (
    <>
      <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="stat-card">
          <div className="label">Total Alerts</div>
          <div className="value">{alerts.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Critical</div>
          <div className="value danger">{grouped.critical.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">High</div>
          <div className="value warning">{grouped.high.length}</div>
        </div>
        <div className="stat-card">
          <div className="label">Medium / Low</div>
          <div className="value">{grouped.medium.length}</div>
        </div>
      </div>

      {alerts.length === 0 ? (
        <EmptyState icon="✅" title="No alerts" message="No suspicious patterns detected." />
      ) : (
        <div className="alert-list">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={`alert-item ${a.severity}`}
              onClick={() => handleClick(a)}
            >
              <div className="alert-header">
                <span className="alert-title">
                  {severityIcon(a.severity)} {a.title}
                </span>
                <RiskBadge score={a.risk_score} />
              </div>
              <div className="alert-desc">{a.description}</div>
              <div className="alert-type">
                {a.alert_type.replace(/_/g, ' ')} · {a.entity_type}: {a.entity_id}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
