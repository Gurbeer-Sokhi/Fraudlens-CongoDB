import { riskLabel } from '../utils/helpers';

export default function RiskBadge({ score }) {
  const label = riskLabel(score);
  return (
    <span className={`risk-badge ${label}`}>
      {score ?? '—'} {label}
    </span>
  );
}
