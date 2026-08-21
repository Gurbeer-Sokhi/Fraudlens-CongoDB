import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import RiskBadge from '../components/RiskBadge';
import GraphVisualization from '../components/GraphVisualization';
import { formatCurrency, formatDate } from '../utils/helpers';

export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const personParam = searchParams.get('person');

  useEffect(() => {
    if (personParam) {
      loadPerson(personParam);
    }
  }, [personParam]);

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setSelected(null);
    setDetail(null);
    setGraphData(null);
    try {
      const data = await api.search(query);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadPerson = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const [person, graph] = await Promise.all([
        api.person(id),
        api.personGraph(id).catch(() => null),
      ]);
      setSelected({ entity_type: 'person', id });
      setDetail(person);
      setGraphData(graph);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadTransaction = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const tx = await api.transaction(id);
      setSelected({ entity_type: 'transaction', id });
      setDetail(tx);
      setGraphData(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (item) => {
    if (item.entity_type === 'person') loadPerson(item.id);
    else if (item.entity_type === 'transaction') loadTransaction(item.id);
    else setSelected(item);
  };

  return (
    <>
      <form className="search-bar" onSubmit={handleSearch}>
        <input
          className="search-input"
          placeholder="Search by person name, email, account number, or transaction ID..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" className="btn btn-primary">Search</button>
      </form>

      {error && <div className="error-banner">{error}</div>}
      {loading && <LoadingSpinner message="Searching..." />}

      {!loading && results.length > 0 && !detail && (
        <div className="card">
          <div className="card-title">Results ({results.length})</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>ID</th>
                <th>Name / Label</th>
                <th>Details</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={`${r.entity_type}-${r.id}`} onClick={() => handleSelect(r)}>
                  <td><span className="chip">{r.entity_type}</span></td>
                  <td style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.8125rem' }}>{r.id}</td>
                  <td>{r.label}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{r.subtitle}</td>
                  <td>{r.risk_score != null ? <RiskBadge score={r.risk_score} /> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && results.length === 0 && query && !detail && (
        <EmptyState icon="🔍" title="No results" message={`Nothing found for "${query}"`} />
      )}

      {detail && selected?.entity_type === 'person' && (
        <div style={{ marginTop: '1.5rem' }}>
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3>{detail.name}</h3>
              <RiskBadge score={detail.risk_score} />
            </div>
            <div className="detail-grid">
              <div className="detail-field">
                <div className="field-label">ID</div>
                <div className="field-value">{detail.id}</div>
              </div>
              <div className="detail-field">
                <div className="field-label">Email</div>
                <div className="field-value">{detail.email}</div>
              </div>
              <div className="detail-field">
                <div className="field-label">Phone</div>
                <div className="field-value">{detail.phone}</div>
              </div>
              <div className="detail-field">
                <div className="field-label">Created</div>
                <div className="field-value">{formatDate(detail.created_at)}</div>
              </div>
            </div>
            <div style={{ marginTop: '1rem' }}>
              <div className="field-label">Accounts ({detail.accounts?.length || 0})</div>
              {detail.accounts?.map((a) => (
                <span key={a.id} className="chip">{a.account_number} — {a.bank_name}</span>
              ))}
            </div>
            <div style={{ marginTop: '0.75rem' }}>
              <div className="field-label">Devices ({detail.devices?.length || 0})</div>
              {detail.devices?.map((d) => (
                <span key={d.id} className="chip">{d.fingerprint?.slice(0, 8)}... ({d.os})</span>
              ))}
            </div>
          </div>

          {graphData?.nodes?.length > 0 && (
            <div className="card">
              <div className="card-title">Connection Graph</div>
              <GraphVisualization data={graphData} height={450} />
            </div>
          )}
        </div>
      )}

      {detail && selected?.entity_type === 'transaction' && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>Transaction {detail.id}</h3>
          <div className="detail-grid">
            <div className="detail-field">
              <div className="field-label">Amount</div>
              <div className="field-value">{formatCurrency(detail.amount)}</div>
            </div>
            <div className="detail-field">
              <div className="field-label">Type</div>
              <div className="field-value">{detail.transaction_type}</div>
            </div>
            <div className="detail-field">
              <div className="field-label">Timestamp</div>
              <div className="field-value">{formatDate(detail.timestamp)}</div>
            </div>
            <div className="detail-field">
              <div className="field-label">Performer</div>
              <div className="field-value">{detail.performer?.name || '—'}</div>
            </div>
            <div className="detail-field">
              <div className="field-label">From Account</div>
              <div className="field-value">{detail.from_account?.account_number || '—'}</div>
            </div>
            <div className="detail-field">
              <div className="field-label">Merchant</div>
              <div className="field-value">{detail.merchant?.name || '—'}</div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
