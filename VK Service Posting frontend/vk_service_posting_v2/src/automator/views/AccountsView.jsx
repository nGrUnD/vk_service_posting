import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { ExternalLink, RefreshCcw, Search, Trash2 } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

export default function AccountsView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [curlInput, setCurlInput] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [checkingId, setCheckingId] = useState(null);
  const [reconnectId, setReconnectId] = useState(null);

  const loadAccounts = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      try {
        const { data } = await api.get(`/users/${user.id}/vk_accounts/all`);
        setAccounts(Array.isArray(data) ? data : []);
      } catch {
        messageApi.error('Не удалось загрузить аккаунты');
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [messageApi, user.id],
  );

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return accounts;
    return accounts.filter((a) =>
      [a.name, a.second_name, a.login, String(a.vk_account_id), a.account_type]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(q),
    );
  }, [accounts, search]);

  const handleCurlMain = async () => {
    if (!curlInput.trim()) {
      messageApi.warning('Вставьте curl для главного аккаунта');
      return;
    }
    setConnecting(true);
    try {
      await api.post(`/users/${user.id}/vk_accounts/curl_main`, { curl: curlInput.trim() });
      setCurlInput('');
      messageApi.success('Запущена обработка главного аккаунта');
      loadAccounts(true);
    } catch (e) {
      messageApi.error(e.response?.data?.detail || 'Ошибка curl_main');
    } finally {
      setConnecting(false);
    }
  };

  const handleCheck = async (id) => {
    setCheckingId(id);
    try {
      const { data } = await api.post(`/users/${user.id}/vk_accounts/${id}/check_curl`);
      if (data?.ok) {
        messageApi.success(data?.detail || 'curl живой');
      } else {
        messageApi.error(data?.detail || 'Не удалось получить токен');
      }
      loadAccounts(true);
    } catch (err) {
      messageApi.error(err?.response?.data?.detail || 'Ошибка проверки curl');
    } finally {
      setCheckingId(null);
    }
  };

  const handleReconnect = async (id) => {
    setReconnectId(id);
    try {
      await api.post(`/users/${user.id}/vk_accounts/${id}/reconnect_curl`);
      messageApi.success('Переподключение curl запущено');
      loadAccounts(true);
    } catch (err) {
      messageApi.error(err?.response?.data?.detail || 'Ошибка reconnect');
    } finally {
      setReconnectId(null);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Удалить этот аккаунт?')) return;
    try {
      await api.delete(`/users/${user.id}/vk_accounts/${id}`);
      messageApi.success('Аккаунт удалён');
      loadAccounts(true);
    } catch {
      messageApi.error('Ошибка удаления');
    }
  };

  return (
    <div className="grid animate-in fade-in grid-cols-1 gap-8 duration-300 lg:grid-cols-3">
      {contextHolder}

      <div className="space-y-6 lg:col-span-1">
        <div className="rounded-3xl border border-gray-100 bg-white p-8 shadow-sm">
          <h3 className="mb-4 flex items-center gap-2 text-lg font-black text-gray-800">
            <RefreshCcw size={20} className="text-blue-600" /> Подключить по cURL
          </h3>
          <p className="mb-6 text-sm font-medium leading-relaxed text-gray-500">
            Главный технический аккаунт: отправка той же команды, что и в V1 (`curl_main`).
          </p>
          <textarea
            className="h-40 w-full resize-none rounded-2xl border border-gray-100 bg-gray-50 p-4 font-mono text-[11px] leading-tight text-gray-600 outline-none focus:ring-4 focus:ring-blue-100"
            placeholder="curl 'https://vk.com/al_feed.php' -H 'cookie: ...' ..."
            value={curlInput}
            onChange={(e) => setCurlInput(e.target.value)}
          />
          <button
            type="button"
            disabled={connecting}
            onClick={handleCurlMain}
            className="mt-6 w-full rounded-2xl bg-blue-600 py-4 font-bold text-white shadow-lg shadow-blue-100 transition-all hover:bg-blue-700 disabled:opacity-60"
          >
            {connecting ? 'Отправка…' : 'Обновить сессию'}
          </button>
        </div>

        <div className="rounded-3xl bg-indigo-600 p-8 text-white shadow-lg shadow-indigo-200">
          <h3 className="mb-2 text-lg font-black">Действия как в V1</h3>
          <p className="mb-8 text-sm font-medium leading-relaxed text-indigo-100">
            Для каждой строки: проверка curl, переподключение curl, удаление — те же endpoint&apos;ы, что и в первой версии.
          </p>
          <button
            type="button"
            onClick={() => loadAccounts()}
            className="w-full rounded-xl bg-white/10 py-3 text-sm font-bold backdrop-blur-sm transition-all hover:bg-white/20"
          >
            Обновить список
          </button>
        </div>
      </div>

      <div className="flex flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm lg:col-span-2">
        <div className="z-10 flex flex-wrap items-center justify-between gap-4 border-b border-gray-100 bg-white p-8">
          <span className="text-lg font-black text-gray-800">
            Всего аккаунтов: {loading ? '…' : accounts.length}
          </span>
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              placeholder="Поиск…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64 rounded-2xl border border-gray-100 bg-gray-50 py-3 pl-11 pr-4 text-sm font-medium outline-none transition-all focus:ring-4 focus:ring-blue-100"
            />
          </div>
        </div>
        <div className="max-h-[560px] flex-1 divide-y divide-gray-100 overflow-y-auto">
          {filtered.map((a) => (
            <div key={a.id} className="flex flex-col gap-3 p-5 px-8 transition-colors hover:bg-gray-50/50 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-center gap-5">
                <img
                  src={a.avatar_url || 'https://placehold.co/48x48/f3f4f6/6b7280?text=VK'}
                  alt=""
                  className="h-12 w-12 rounded-2xl object-cover"
                />
                <div className="min-w-0">
                  <p className="mb-0.5 truncate text-sm font-bold text-gray-800">
                    {[a.name, a.second_name].filter(Boolean).join(' ') || `id ${a.id}`}
                  </p>
                  <p className="text-xs font-medium text-gray-500">
                    {a.login ? `${a.login} • ` : ''}
                    тип: <span className="font-bold text-blue-600">{a.account_type}</span>
                    {a.proxy_id ? ` • proxy #${a.proxy_id}` : ''}
                  </p>
                  {a.vk_account_url && (
                    <a
                      href={a.vk_account_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-flex items-center gap-1 text-xs font-bold text-blue-600"
                    >
                      Открыть VK <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={checkingId === a.id}
                  onClick={() => handleCheck(a.id)}
                  className="rounded-xl bg-gray-50 px-4 py-2 text-xs font-bold text-gray-600 transition-all hover:bg-gray-200 disabled:opacity-50"
                >
                  {checkingId === a.id ? '…' : 'Проверить curl'}
                </button>
                <button
                  type="button"
                  disabled={reconnectId === a.id}
                  onClick={() => handleReconnect(a.id)}
                  className="rounded-xl bg-blue-50 px-4 py-2 text-xs font-bold text-blue-700 transition-all hover:bg-blue-100 disabled:opacity-50"
                >
                  {reconnectId === a.id ? '…' : 'Переподключить'}
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(a.id)}
                  className="rounded-xl p-2 text-gray-300 transition-all hover:bg-red-50 hover:text-red-500"
                  aria-label="Удалить"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))}
          {!loading && !filtered.length && (
            <div className="p-12 text-center text-sm text-gray-500">Нет аккаунтов по фильтру.</div>
          )}
        </div>
      </div>
    </div>
  );
}
