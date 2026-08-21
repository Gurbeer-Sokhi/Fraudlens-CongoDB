import { useState } from 'react';
import { api } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import { formatCurrency, formatDate } from '../utils/helpers';

export default function TimelinePage() {
  const [personId, setPersonId] = useState('');
  const [events, setEvents] = useState([]);
  const [personName, setPersonName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleLoad = async (e) => {
    e.preventDefault();
    if (!personId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const [timeline, person] = await Promise.all([
        api.timeline(personId.trim()),
        api.person(personId.trim()).catch(() => null),
      ]);
      setEvents(timeline);
      setPersonName(person?.name || personId);
    } catch (err) {
      setError(err.message);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <form className="search-bar" onSubmit={handleLoad}>
        <input
          className="search-input"
          placeholder="Enter Person ID (e.g. P-RING-A-0, P-SUSPECT-01)..."
          value={personId}
          onChange={(e) => setPersonId(e.target.value)}
        />
        <button type="submit" className="btn btn-primary">Load Timeline</button>
      </form>

      <div style={{ marginBottom: '1rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
        Try: P-RING-A-0 (money laundering), P-RING-B-0 (identity fraud), P-SUSPECT-01 (suspicious transfers)
      </div>

      {error && <div className="error-banner">{error}</div>}
      {loading && <LoadingSpinner message="Loading timeline..." />}

      {!loading && events.length > 0 && (
        <div className="card">
          <div className="card-title">Transaction Timeline — {personName}</div>
          <div className="timeline">
            {events.map((ev) => (
              <div key={ev.id} className={`timeline-item ${ev.risk_indicator}`}>
                <div className="time">{formatDate(ev.timestamp)}</div>
                <div className="event-title">
                  {formatCurrency(ev.amount)} — {ev.transaction_type}
                </div>
                <div className="event-detail">
                  {ev.merchant_name && `at ${ev.merchant_name} · `}
                  {ev.id}
                  {ev.risk_indicator !== 'normal' && (
                    <span style={{ color: 'var(--red)', marginLeft: '0.5rem' }}>
                      ⚠ {ev.risk_indicator.replace('_', ' ')}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && events.length === 0 && personId && !error && (
        <EmptyState icon="📅" title="No transactions" message="No transactions found for this person." />
      )}
    </>
  );
}
