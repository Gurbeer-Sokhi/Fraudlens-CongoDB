import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', icon: '📊', label: 'Dashboard' },
  { path: '/network', icon: '🔗', label: 'Network Graph' },
  { path: '/alerts', icon: '🚨', label: 'Alerts' },
  { path: '/search', icon: '🔍', label: 'Search' },
  { path: '/timeline', icon: '📅', label: 'Timeline' },
];

export default function Sidebar({ dbStatus }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="icon">🛡️</div>
        <h1>FraudLens</h1>
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="db-status">
          <div className={`dot${dbStatus !== 'connected' ? ' disconnected' : ''}`} />
          CognoDB: {dbStatus || 'checking...'}
        </div>
      </div>
    </aside>
  );
}
