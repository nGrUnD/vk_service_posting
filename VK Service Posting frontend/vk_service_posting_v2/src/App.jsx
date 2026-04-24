import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import AutomatorShell from './automator/AutomatorShell.jsx';
import DashboardView from './automator/views/DashboardView.jsx';
import WorkflowView from './automator/views/WorkflowView.jsx';
import AccountsView from './automator/views/AccountsView.jsx';
import SourcesView from './automator/views/SourcesView.jsx';
import ProxyView from './automator/views/ProxyView.jsx';
import SettingsView from './automator/views/SettingsView.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';

function getBasename() {
  const base = import.meta.env.BASE_URL || '/';
  return base === '/' ? undefined : base.replace(/\/$/, '');
}

export default function App() {
  return (
    <BrowserRouter basename={getBasename()}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route path="/" element={<AutomatorShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardView />} />
          <Route path="workflow" element={<WorkflowView />} />
          <Route path="accounts" element={<AccountsView />} />
          <Route path="sources" element={<SourcesView />} />
          <Route path="proxy" element={<ProxyView />} />
          <Route path="settings" element={<SettingsView />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
