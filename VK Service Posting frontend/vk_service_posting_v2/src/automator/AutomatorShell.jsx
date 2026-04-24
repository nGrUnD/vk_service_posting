import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { message, Spin } from 'antd';
import {
  BarChart3,
  Database,
  ExternalLink,
  LogOut,
  PlayCircle,
  Plus,
  RefreshCcw,
  Settings,
  ShieldCheck,
  Users,
  Zap,
} from 'lucide-react';

import api from '../api/axios';
import { AutomatorUserProvider } from './AutomatorUserContext.jsx';
import TechAccountModal from './TechAccountModal.jsx';

const nav = [
  { to: '/dashboard', id: 'dashboard', icon: BarChart3, label: 'Дашборд' },
  { to: '/workflow', id: 'workflow', icon: PlayCircle, label: 'Рабочий процесс' },
  { to: '/accounts', id: 'accounts', icon: Users, label: 'Аккаунты ВК' },
  { to: '/sources', id: 'sources', icon: Database, label: 'Базы клипов' },
  { to: '/proxy', id: 'proxy', icon: ShieldCheck, label: 'Прокси сети' },
  { to: '/settings', id: 'settings', icon: Settings, label: 'Настройки' },
];

function getV1Url() {
  return import.meta.env.VITE_V1_URL || `${window.location.protocol}//${window.location.hostname}:5173/`;
}

function routeTitle(pathname) {
  if (pathname.includes('/workflow')) return { title: 'Управление воркерами', sub: 'Создавайте и мониторьте задачи постинга' };
  if (pathname.includes('/accounts')) return { title: 'База аккаунтов', sub: 'cURL для главного аккаунта и полный список, как в V1' };
  if (pathname.includes('/sources')) return { title: 'Библиотека контента', sub: 'Списки клипов и привязка источников' };
  if (pathname.includes('/proxy')) return { title: 'Управление прокси', sub: 'Добавление и удаление прокси' };
  if (pathname.includes('/settings')) return { title: 'Системные настройки', sub: 'Категории и лимиты (API V1)' };
  return { title: 'Обзор системы', sub: 'Сводка по аккаунтам и воркерам' };
}

export default function AutomatorShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [messageApi, contextHolder] = message.useMessage();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [techOpen, setTechOpen] = useState(false);
  const [mainTeaser, setMainTeaser] = useState(null);

  useEffect(() => {
    let alive = true;
    api
      .get('/auth/only_auth')
      .then((res) => {
        if (!alive) return;
        localStorage.setItem('preferred_ui_version', 'v2');
        setUser(res.data);
      })
      .catch(() => {
        if (!alive) return;
        navigate('/login', { replace: true });
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [navigate]);

  const loadMainTeaser = useCallback(async () => {
    if (!user?.id) return;
    try {
      const { data } = await api.get(`/users/${user.id}/vk_accounts/all`);
      const accounts = Array.isArray(data) ? data : [];
      const main = accounts.find((a) => a.account_type === 'main') || null;
      setMainTeaser(main);
    } catch {
      setMainTeaser(null);
    }
  }, [user?.id]);

  useEffect(() => {
    loadMainTeaser();
  }, [loadMainTeaser]);

  const header = useMemo(() => routeTitle(location.pathname), [location.pathname]);

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
      localStorage.removeItem('access_token');
      navigate('/login', { replace: true });
    } catch {
      messageApi.error('Не удалось выйти');
    }
  };

  const openV1 = () => {
    localStorage.setItem('preferred_ui_version', 'v1');
    window.location.assign(getV1Url());
  };

  if (loading || !user) {
    return (
      <div className="vk-automator flex min-h-screen items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  const mainLabel = mainTeaser
    ? `${mainTeaser.name ?? ''} ${mainTeaser.second_name ?? ''}`.trim() || 'Главный аккаунт'
    : 'Тех. аккаунт';
  const mainInitials = mainLabel
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="vk-automator flex h-screen text-gray-900">
      {contextHolder}
      <TechAccountModal open={techOpen} onClose={() => { setTechOpen(false); loadMainTeaser(); }} userId={user.id} />

      <aside className="flex w-72 flex-col border-r border-gray-200 bg-white p-5">
        <div className="mb-10 mt-2 flex items-center space-x-3 px-2">
          <div className="rounded-xl bg-blue-600 p-2.5 shadow-md shadow-blue-200">
            <Zap className="text-white" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-black leading-tight tracking-tight">VK Automator</h1>
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Dashboard 2.0</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1.5">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  'flex w-full items-center space-x-3 rounded-xl px-4 py-3 font-semibold transition-all',
                  isActive
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-200'
                    : 'text-gray-500 hover:bg-gray-100 hover:text-gray-900',
                ].join(' ')
              }
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-2 border-t border-gray-100 pt-6">
          <button
            type="button"
            onClick={() => setTechOpen(true)}
            className="group w-full rounded-2xl bg-blue-50 p-4 text-left transition-colors hover:bg-blue-100"
          >
            <p className="mb-2 flex items-center justify-between text-[10px] font-black uppercase tracking-wider text-blue-600">
              Тех. аккаунт <ExternalLink size={12} className="opacity-0 transition-opacity group-hover:opacity-100" />
            </p>
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-200 text-sm font-black text-blue-700">
                {mainInitials}
              </div>
              <div className="min-w-0 flex-1 overflow-hidden">
                <p className="truncate text-sm font-bold text-gray-900">{mainLabel}</p>
                <p className="mt-0.5 flex items-center text-[11px] font-semibold text-green-600">
                  <span className="mr-1.5 h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
                  cURL / статус как в V1
                </p>
              </div>
            </div>
          </button>

          <button
            type="button"
            onClick={openV1}
            className="w-full rounded-xl py-2.5 text-center text-xs font-bold text-gray-500 transition-all hover:bg-gray-100 hover:text-gray-800"
          >
            Открыть интерфейс V1
          </button>

          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-bold text-gray-400 transition-all hover:bg-red-50 hover:text-red-500"
          >
            <LogOut size={16} /> Выйти
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-10">
        <header className="mb-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h2 className="mb-2 text-3xl font-black tracking-tight text-gray-800">{header.title}</h2>
            <p className="font-medium text-gray-500">{header.sub}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="flex items-center space-x-2 rounded-xl border border-gray-200 bg-white px-5 py-2.5 text-sm font-bold text-gray-700 shadow-sm transition-all hover:bg-gray-50"
            >
              <RefreshCcw size={16} />
              <span>Обновить страницу</span>
            </button>
            {!location.pathname.includes('/workflow') && (
              <button
                type="button"
                onClick={() => navigate('/workflow')}
                className="flex items-center space-x-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-blue-100 transition-all hover:bg-blue-700"
              >
                <Plus size={18} />
                <span>Рабочий процесс</span>
              </button>
            )}
          </div>
        </header>

        <AutomatorUserProvider user={user}>
          <Outlet />
        </AutomatorUserProvider>
      </main>
    </div>
  );
}
