import { useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

const GROUP_COLORS = {
  Person: '#3b82f6',
  BankAccount: '#8b5cf6',
  Transaction: '#06b6d4',
  Merchant: '#f59e0b',
  Device: '#64748b',
  IPAddress: '#94a3b8',
};

export default function GraphVisualization({ data, height = 600 }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !data?.nodes?.length) return;

    const nodes = new DataSet(
      data.nodes.map((n) => ({
        id: n.id,
        label: n.label,
        group: n.group,
        title: n.title,
        color: n.color || GROUP_COLORS[n.group] || '#64748b',
        font: { color: '#f1f5f9', size: 12 },
        shape: n.group === 'Person' ? 'dot' : n.group === 'Transaction' ? 'diamond' : 'box',
        size: n.group === 'Person' ? 20 : 14,
      }))
    );

    const edges = new DataSet(
      data.edges.map((e) => ({
        id: e.id,
        from: e.from,
        to: e.to,
        label: e.label,
        dashes: e.dashes,
        font: { color: '#94a3b8', size: 9, strokeWidth: 0 },
        color: { color: '#475569', highlight: '#3b82f6' },
        arrows: 'to',
        smooth: { type: 'curvedCW', roundness: 0.15 },
      }))
    );

    const options = {
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -3000,
          springLength: 150,
          springConstant: 0.04,
        },
        stabilization: { iterations: 150 },
      },
      interaction: { hover: true, tooltipDelay: 200, navigationButtons: true },
      groups: Object.fromEntries(
        Object.entries(GROUP_COLORS).map(([k, v]) => [k, { color: { background: v, border: v } }])
      ),
    };

    if (networkRef.current) {
      networkRef.current.destroy();
    }

    networkRef.current = new Network(containerRef.current, { nodes, edges }, options);

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [data]);

  return (
    <>
      <div className="graph-legend">
        {Object.entries(GROUP_COLORS).map(([label, color]) => (
          <div key={label} className="legend-item">
            <div className="legend-dot" style={{ background: color }} />
            {label}
          </div>
        ))}
      </div>
      <div className="graph-container" ref={containerRef} style={{ height }} />
    </>
  );
}
