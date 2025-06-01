import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { message } from 'antd'; // Добавляем импорт message

import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';

import MainTab from './components/Tab.jsx';
import DashboardAccount from './pages/DashboardAccount.jsx';
import ConnectAccountPage from './pages/ConnectAccountPage.jsx';
import ConnectBackupAccountPage from './pages/ConnectBackupAccountPage.jsx';
import SourceGroupPage from './pages/SourceGroupPage.jsx';
import CatergorySettingsPage from './pages/CatergorySettingsPage.jsx';
import WorkflowStatusPage from './pages/WorkflowStatusPage.jsx';

import 'antd/dist/reset.css';
import './index.css';

const container = document.getElementById('root');
const root = createRoot(container);

// Конфигурация message перед рендером
message.config({
    top: 24,
    duration: 3,
    maxCount: 3,
});

root.render(
    <React.StrictMode>
        <ConfigProvider
            getPopupContainer={() => document.body}>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Navigate to="/login" replace />} />

                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />

                    <Route path="/dashboard/*" element={<MainTab />}>
                        <Route index element={<Navigate to="main-account" replace />} />
                        <Route path="main-account" element={<DashboardAccount />} />
                        <Route path="connect-account" element={<ConnectAccountPage />} />
                        <Route path="connect-backup-account" element={<ConnectBackupAccountPage />} />
                        <Route path="connect-source-group" element={<SourceGroupPage />} />
                        <Route path="category-settings" element={<CatergorySettingsPage />} />
                        <Route path="workflow-status" element={<WorkflowStatusPage />} />
                    </Route>
                </Routes>
            </BrowserRouter>
        </ConfigProvider>
    </React.StrictMode>
);