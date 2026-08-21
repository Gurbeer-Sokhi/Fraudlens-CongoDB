import { useEffect, useState } from 'react';
import { api } from '../api/client';
import GraphVisualization from '../components/GraphVisualization';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';

export default function NetworkPage() {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nodeLimit, setNodeLimit] = useState(150);

  useEffect(() => {
    setLoading(true);
    api.networkGraph(nodeLimit)
      .then(setGraphData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [nodeLimit]);

  return (
    <>
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', alignItems: 'center' }}>
        <label style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Nodes:</label>
        {[100, 150, 200].map((n) => (
          <button
            key={n}
            className={`btn ${nodeLimit === n ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setNodeLimit(n)}
          >
            {n}
          </button>
        ))}
      </div>

      {loading && <LoadingSpinner message="Building network graph..." />}
      {error && <div className="error-banner">{error}</div>}
      {!loading && !error && graphData?.nodes?.length > 0 && (
        <GraphVisualization data={graphData} />
      )}
      {!loading && !error && (!graphData?.nodes?.length) && (
        <EmptyState icon="🔗" title="No graph data" message="Run the seed script to populate the database." />
      )}
    </>
  );
}
