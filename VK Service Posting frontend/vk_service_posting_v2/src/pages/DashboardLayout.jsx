import React, { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Spin, message } from 'antd';

import api from '../api/axios';

const navItems = [
  { to: '/overview', label: 'Overview', description: 'Сводка по аккаунтам' },
  { to: '/accounts', label: 'Accounts', description: 'Новый список аккаунтов' },
  { to: '/proxy', label: 'Proxy', description: 'Управление прокси' },
  { to: '/workflows', label: 'Workflows', description: 'Заготовка под V2 flow' },
  { to: '/sources', label: 'Sources', description: 'Точка входа для источников' },
  { to: '/categories', label: 'Categories', description: 'Будущая страница категорий' },
  { to: '/checker', label: 'Checker', description: 'Будущий checker UI' },
];

function getV1Url() {
  return (
    import.meta.env.VITE_V1_URL ||
    `${window.location.protocol}//${window.location.hostname}:5173/`
  );
}

export default function DashboardLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [messageApi, contextHolder] = message.useMessage();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    api.get('/auth/only_auth')
      .then((res) => {
        if (!isMounted) {
          return;
        }
        localStorage.setItem('preferred_ui_version', 'v2');
        setUser(res.data);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        navigate('/login', { replace: true });
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [navigate]);

  const activeItem = useMemo(
    () => navItems.find((item) => location.pathname.startsWith(item.to)),
    [location.pathname],
  );

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
      localStorage.removeItem('access_token');
      navigate('/login', { replace: true });
    } catch {
      messageApi.error('Не удалось завершить сессию');
    }
  };

  const openV1 = () => {
    localStorage.setItem('preferred_ui_version', 'v1');
    window.location.assign(getV1Url());
  };

  if (loading) {
    return (
      <div className="v2-shell flex items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="v2-shell">
      {contextHolder}

      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 px-4 py-4 lg:px-6">
        <aside className="v2-card hidden w-[290px] rounded-[28px] p-5 lg:flex lg:flex-col">
          <div className="mb-8">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-indigo-300">
              VK Service
            </p>
            <h1 className="m-0 text-2xl font-semibold text-white">Control Center V2</h1>
            <p className="v2-muted mt-2 text-sm">
              Новый frontend живет отдельно от V1 и использует тот же backend.
            </p>
          </div>

          <nav className="flex flex-1 flex-col gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    'rounded-2xl border px-4 py-3 transition',
                    isActive
                      ? 'border-indigo-400/50 bg-indigo-500/12 text-white'
                      : 'border-transparent bg-slate-900/30 text-slate-300 hover:border-slate-700 hover:bg-slate-900/50',
                  ].join(' ')
                }
              >
                <div className="text-sm font-semibold">{item.label}</div>
                <div className="mt-1 text-xs text-slate-400">{item.description}</div>
              </NavLink>
            ))}
          </nav>

          <div className="v2-card rounded-3xl p-4">
            <div className="text-sm font-semibold text-white">Версии интерфейса</div>
            <p className="v2-muted mb-3 mt-2 text-sm">
              `V1` остается доступен как старый интерфейс, а `V2` развиваем отдельно.
            </p>
            <div className="flex gap-3">
              <button type="button" className="v2-button v2-button-primary flex-1" onClick={() => window.location.assign(window.location.href)}>
                V2
              </button>
              <button type="button" className="v2-button v2-button-secondary flex-1" onClick={openV1}>
                V1
              </button>
            </div>
          </div>
        </aside>

        <main className="flex-1">
          <header className="v2-card mb-6 rounded-[28px] p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                  {activeItem?.label || 'Dashboard'}
                </div>
                <h2 className="mt-2 text-2xl font-semibold text-white">
                  {activeItem?.description || 'Изолированная V2-панель'}
                </h2>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Link
                  to="/overview"
                  className="rounded-2xl border border-slate-800 bg-slate-900/50 px-4 py-2 text-sm text-slate-200"
                >
                  Главная V2
                </Link>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 px-4 py-2 text-sm text-slate-200">
                  {user?.email || `User #${user?.id ?? ''}`}
                </div>
                <button type="button" className="v2-button v2-button-secondary" onClick={handleLogout}>
                  Выйти
                </button>
              </div>
            </div>
          </header>

          <section>
            <Outlet context={{ user }} />
          </section>
        </main>
      </div>
    </div>
  );
}
