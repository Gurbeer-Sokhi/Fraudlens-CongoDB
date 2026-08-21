import { useEffect, useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import NetworkPage from './pages/NetworkPage';
import AlertsPage from './pages/AlertsPage';
import SearchPage from './pages/SearchPage';
import TimelinePage from './pages/TimelinePage';
import { api } from './api/client';

const PAGE_TITLES = {
  '/': { title: 'Dashboard', subtitle: 'Overview of fraud detection metrics and risk distribution' },
  '/network': { title: 'Transaction Network', subtitle: 'Interactive graph visualization of entity relationships' },
  '/alerts': { title: 'Fraud Alerts', subtitle: 'Real-time suspicious pattern detection' },
  '/search': { title: 'Search & Investigate', subtitle: 'Search persons, accounts, and transactions' },
  '/timeline': { title: 'Transaction Timeline', subtitle: 'Chronological view of person transaction history' },
};

export default function App() {
  const location = useLocation();
  const [dbStatus, setDbStatus] = useState('checking');

  useEffect(() => {
    api.health()
      .then((h) => setDbStatus(h.database))
      .catch(() => setDbStatus('disconnected'));
  }, []);

  const pageInfo = PAGE_TITLES[location.pathname] || PAGE_TITLES['/'];

  return (
    <div className="app-layout">
      <Sidebar dbStatus={dbStatus} />
      <main className="main-content">
        <header className="page-header">
          <h2>{pageInfo.title}</h2>
          <p>{pageInfo.subtitle}</p>
        </header>
        <div className="page-body">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/network" element={<NetworkPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/timeline" element={<TimelinePage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
