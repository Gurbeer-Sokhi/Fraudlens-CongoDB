import { useEffect, useState, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { api } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import RiskBadge from '../components/RiskBadge';
import { formatCurrency, severityIcon } from '../utils/helpers';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [dash, alertData] = await Promise.all([
        api.dashboard(),
        api.alerts(8),
      ]);
      setStats(dash);
      setAlerts(alertData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error) return <div className="error-banner">Failed to load dashboard: {error}</div>;

  const chartData = stats?.risk_distribution?.map((b) => ({
    name: b.label.split(' ')[0],
    count: b.count,
    color: b.color,
  })) || [];

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Total Persons</div>
          <div className="value">{stats.total_persons}</div>
        </div>
        <div className="stat-card">
          <div className="label">Transactions</div>
          <div className="value">{stats.total_transactions}</div>
        </div>
        <div className="stat-card">
          <div className="label">High Risk Persons</div>
          <div className="value danger">{stats.high_risk_persons}</div>
        </div>
        <div className="stat-card">
          <div className="label">Total Volume</div>
          <div className="value success">{formatCurrency(stats.total_volume)}</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title">Risk Score Distribution</div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                  contentStyle={{ background: '#1a2234', border: '1px solid #2d3a52', borderRadius: 8 }}
                  labelStyle={{ color: '#f1f5f9' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No risk data" />
          )}
        </div>

        <div className="card">
          <div className="card-title">Recent Alerts</div>
          {alerts.length > 0 ? (
            <div className="alert-list">
              {alerts.map((a) => (
                <div key={a.id} className={`alert-item ${a.severity}`}>
                  <div className="alert-header">
                    <span className="alert-title">
                      {severityIcon(a.severity)} {a.title}
                    </span>
                    <RiskBadge score={a.risk_score} />
                  </div>
                  <div className="alert-desc">{a.description}</div>
                  <div className="alert-type">{a.alert_type.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon="✅" title="No alerts" message="All clear — no suspicious patterns detected." />
          )}
        </div>
      </div>
    </>
  );
}
