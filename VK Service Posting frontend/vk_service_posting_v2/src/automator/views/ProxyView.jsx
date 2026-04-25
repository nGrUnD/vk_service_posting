import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { AlertCircle, RefreshCcw, ShieldCheck, Trash2 } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

function parseProxyInput(value) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseHostPort(proxyValue) {
  const value = (proxyValue || '').trim().split('://').pop().split('@').pop();
  const hostPort = value.split('/')[0];
  const idx = hostPort.lastIndexOf(':');
  if (idx === -1) return { ip: hostPort, port: '' };
  return { ip: hostPort.slice(0, idx), port: hostPort.slice(idx + 1) };
}

export default function ProxyView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [inputValue, setInputValue] = useState('');
  const [proxies, setProxies] = useState([]);
  const [checkResults, setCheckResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [refreshing, setRefreshing] = useState(true);

  const loadProxies = useCallback(async () => {
    setRefreshing(true);
    try {
      const { data } = await api.get(`/proxy/${user.id}/get`);
      setProxies(Array.isArray(data) ? data : []);
    } catch {
      messageApi.error('Не удалось загрузить прокси');
    } finally {
      setRefreshing(false);
    }
  }, [messageApi, user.id]);

  useEffect(() => {
    loadProxies();
  }, [loadProxies]);

  const handleCheckAll = useCallback(async () => {
    if (!proxies.length) {
      messageApi.info('Нет прокси для проверки');
      return;
    }
    setChecking(true);
    try {
      const { data } = await api.post(`/proxy/${user.id}/check_all`);
      const rows = Array.isArray(data?.items) ? data.items : [];
      const next = {};
      rows.forEach((row) => {
        next[row.id] = row;
      });
      setCheckResults(next);
      messageApi.success('Проверка завершена');
    } catch {
      messageApi.error('Не удалось проверить прокси');
    } finally {
      setChecking(false);
    }
  }, [messageApi, proxies.length, user.id]);

  const handleAdd = async () => {
    const lines = parseProxyInput(inputValue);
    if (!lines.length) {
      messageApi.warning('Введите прокси');
      return;
    }
    setLoading(true);
    try {
      await api.post(`/proxy/${user.id}/add`, { proxys: inputValue });
      setInputValue('');
      messageApi.success('Прокси добавлены');
      await loadProxies();
      await handleCheckAll();
    } catch {
      messageApi.error('Ошибка добавления');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteOne = async (proxyRow) => {
    if (!proxyRow?.id) return;
    const ok = window.confirm(`Удалить прокси ${proxyRow.http}?\nДействие нельзя отменить.`);
    if (!ok) return;

    setLoading(true);
    try {
      await api.delete(`/proxy/${user.id}/delete`, { params: { proxy_id: proxyRow.id } });
      setCheckResults((prev) => {
        const next = { ...prev };
        delete next[proxyRow.id];
        return next;
      });
      messageApi.success('Прокси удален');
      await loadProxies();
    } catch {
      messageApi.error('Ошибка удаления');
    } finally {
      setLoading(false);
    }
  };

  const statusRows = useMemo(
    () =>
      proxies.map((proxyRow) => {
        const fallback = parseHostPort(proxyRow.http);
        const checked = checkResults[proxyRow.id] || {};
        return {
          id: proxyRow.id,
          http: proxyRow.http,
          ip: checked.ip || fallback.ip,
          port: checked.port || fallback.port,
          geo: checked.geo || '-',
          status: checked.status || 'unknown',
          ping_ms: checked.ping_ms,
        };
      }),
    [checkResults, proxies],
  );

  const onlineCount = useMemo(() => statusRows.filter((row) => row.status === 'online').length, [statusRows]);

  return (
    <div className="mx-auto max-w-7xl animate-in fade-in duration-300">
      {contextHolder}
      <div className="rounded-3xl border border-gray-100 bg-white p-8 shadow-sm lg:p-10">
        <div className="grid grid-cols-1 gap-6">
          <div className="rounded-3xl border border-gray-100 bg-white p-7">
            <div className="mb-6 inline-flex rounded-2xl bg-indigo-50 p-4 text-indigo-600 shadow-inner">
              <ShieldCheck size={32} />
            </div>
            <h3 className="mb-3 text-3xl font-black tracking-tight text-gray-800">Настройка IPv4/IPv6 прокси</h3>
            <p className="mb-8 text-sm font-medium leading-relaxed text-gray-500">
              Добавьте список мобильных или резидентных прокси. После импорта можно сразу проверить доступность и
              увидеть статус каждого шлюза в таблице.
            </p>
            <label className="mb-3 ml-1 block text-xs font-black uppercase tracking-[0.22em] text-gray-400">
              Добавить список (один на строку)
            </label>
            <textarea
              className="h-64 w-full resize-none rounded-3xl border border-gray-100 bg-gray-50 p-6 font-mono text-sm leading-relaxed outline-none transition-all focus:ring-4 focus:ring-indigo-50"
              placeholder={'http://login:pass@ip:port\nsocks5://ip:port:login:pass'}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
            <button
              type="button"
              disabled={loading}
              onClick={handleAdd}
              className="mt-6 w-full rounded-2xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition-all hover:bg-indigo-700 disabled:opacity-60"
            >
              {loading ? 'Импорт...' : 'Импортировать и проверить'}
            </button>
          </div>

          <div className="rounded-3xl border border-blue-100 bg-blue-50/50 p-6">
            <div className="flex items-start gap-3">
              <AlertCircle size={20} className="mt-0.5 shrink-0 text-blue-500" />
              <p className="text-xs font-medium leading-relaxed text-blue-800">
                Совет по безопасности: не используйте один и тот же прокси для большого числа аккаунтов.
                Оптимально держать не более 3-5 аккаунтов на один мобильный IP, чтобы снизить риск ограничений.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-3xl border border-gray-100 bg-white p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <h4 className="text-xl font-black text-gray-800">Серверы и статус шлюзов</h4>
              <span className="rounded-lg bg-green-500 px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-white shadow-sm">
                {refreshing ? '...' : `${onlineCount} online / ${proxies.length}`}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={loadProxies}
                disabled={refreshing}
                className="inline-flex items-center gap-2 rounded-xl border border-gray-200 px-4 py-2 text-sm font-bold text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-60"
              >
                Обновить список
              </button>
              <button
                type="button"
                onClick={handleCheckAll}
                disabled={checking || loading || !proxies.length}
                className="inline-flex items-center gap-2 rounded-xl border border-gray-200 px-4 py-2 text-sm font-bold text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-60"
              >
                <RefreshCcw size={15} className={checking ? 'animate-spin' : ''} />
                {checking ? 'Проверяем...' : 'Check All'}
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full overflow-hidden rounded-2xl border border-gray-100">
              <thead className="bg-gray-50 text-left text-xs font-black uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="px-4 py-3">Прокси</th>
                  <th className="px-4 py-3">IP адрес</th>
                  <th className="px-4 py-3">Пинг</th>
                  <th className="px-4 py-3">Geo</th>
                  <th className="px-4 py-3">Статус</th>
                  <th className="px-4 py-3 text-right">Действие</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {statusRows.map((row) => (
                  <tr key={row.id} className="text-sm">
                    <td className="px-4 py-3">
                      <div className="max-w-[24rem]">
                        <p className="truncate font-mono text-xs font-semibold text-gray-700" title={row.http || ''}>
                          {row.http || '-'}
                        </p>
                        <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">id {row.id}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-semibold text-gray-800">
                      {row.ip}
                      {row.port ? `:${row.port}` : ''}
                    </td>
                    <td className="px-4 py-3">
                      {row.ping_ms ? (
                        <span className="rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-700">
                          {row.ping_ms}ms
                        </span>
                      ) : (
                        <span className="rounded-md border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs font-bold text-gray-500">
                          -
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{row.geo}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 font-semibold ${
                          row.status === 'online'
                            ? 'text-green-600'
                            : row.status === 'offline'
                              ? 'text-red-500'
                              : 'text-gray-500'
                        }`}
                      >
                        <span
                          className={`h-2 w-2 rounded-full ${
                            row.status === 'online'
                              ? 'bg-green-500'
                              : row.status === 'offline'
                                ? 'bg-red-500'
                                : 'bg-gray-400'
                          }`}
                        />
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        disabled={loading}
                        onClick={() => handleDeleteOne({ id: row.id, http: row.http })}
                        className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-500 disabled:opacity-60"
                        title="Удалить прокси"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
                {!statusRows.length && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                      Добавьте прокси, чтобы увидеть статус шлюзов.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
