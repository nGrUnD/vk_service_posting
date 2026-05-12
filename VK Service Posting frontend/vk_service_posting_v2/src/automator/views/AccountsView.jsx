import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { message } from 'antd';
import {
  ExternalLink,
  KeyRound,
  Loader2,
  Plus,
  RefreshCcw,
  Search,
  Server,
  Trash2,
} from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

function parseLoginsFromCreds(creds) {
  const logins = [];
  for (const line of creds.split(/\r?\n/)) {
    const t = line.trim();
    if (!t || !t.includes(':')) continue;
    logins.push(t.split(':', 1)[0].trim());
  }
  return logins;
}

function statusBadgeClass(parseStatus) {
  if (parseStatus === 'success') return 'bg-green-100 text-green-800 border-green-200';
  if (parseStatus === 'failure') return 'bg-red-100 text-red-800 border-red-200';
  return 'bg-amber-100 text-amber-900 border-amber-200';
}

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

  const [bulkCreds, setBulkCreds] = useState('');
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [autoChangePassword, setAutoChangePassword] = useState(true);
  const [watchedIds, setWatchedIds] = useState([]);
  const [importPolling, setImportPolling] = useState(false);
  const passwordChangedRef = useRef(new Set());
  const watchedIdSet = useMemo(() => new Set(watchedIds), [watchedIds]);

  const [categories, setCategories] = useState([]);
  const [autocurlCreds, setAutocurlCreds] = useState('');
  const [autocurlGroups, setAutocurlGroups] = useState('');
  const [autocurlCategoryId, setAutocurlCategoryId] = useState('');
  const [autocurlSubmitting, setAutocurlSubmitting] = useState(false);

  const [changingPwId, setChangingPwId] = useState(null);

  const loadAccounts = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      let rows = [];
      try {
        const { data } = await api.get(`/users/${user.id}/vk_accounts/all`);
        rows = Array.isArray(data) ? data : [];
        setAccounts(rows);
      } catch {
        messageApi.error('Не удалось загрузить аккаунты');
      } finally {
        if (!silent) setLoading(false);
      }
      return rows;
    },
    [messageApi, user.id],
  );

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/users/${user.id}/categories/get_all`);
        if (!cancelled) setCategories(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setCategories([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user.id]);

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

  const pendingWatchCount = useMemo(() => {
    let n = 0;
    for (const a of accounts) {
      if (!watchedIdSet.has(a.id)) continue;
      const done =
        a.parse_status === 'failure' ||
        (a.parse_status === 'success' && passwordChangedRef.current.has(a.id));
      if (!done) n += 1;
    }
    return n;
  }, [accounts, watchedIdSet]);

  useEffect(() => {
    if (!importPolling || watchedIds.length === 0) return undefined;
    const watchedSet = new Set(watchedIds);

    const tick = async () => {
      let list = await loadAccounts(true);
      if (!autoChangePassword) {
        const allTerminal = watchedIds.every((accId) => {
          const a = list.find((x) => x.id === accId);
          return a && (a.parse_status === 'success' || a.parse_status === 'failure');
        });
        if (allTerminal) {
          setWatchedIds([]);
          setImportPolling(false);
          messageApi.info('Обработка импортированных аккаунтов завершена');
        }
        return;
      }
      const readyIds = list
        .filter(
          (a) =>
            watchedSet.has(a.id) &&
            a.parse_status === 'success' &&
            !passwordChangedRef.current.has(a.id),
        )
        .map((a) => a.id);
      if (readyIds.length) {
        try {
          const { data } = await api.post(`/users/${user.id}/vk_accounts/change_passwords_by_ids`, {
            vk_account_ids: readyIds,
          });
          for (const r of data?.results || []) {
            if (r.ok) passwordChangedRef.current.add(r.vk_account_id);
            else
              messageApi.warning(
                `Смена пароля #${r.vk_account_id}${r.login ? ` (${r.login})` : ''}: ${r.detail || 'ошибка'}`,
              );
          }
        } catch (e) {
          messageApi.error(e.response?.data?.detail || 'Ошибка смены пароля');
        }
        list = await loadAccounts(true);
      }
      const allDone = watchedIds.every((accId) => {
        const a = list.find((x) => x.id === accId);
        if (!a) return true;
        if (a.parse_status === 'failure') return true;
        return a.parse_status === 'success' && passwordChangedRef.current.has(accId);
      });
      if (allDone && watchedIds.length) {
        setWatchedIds([]);
        setImportPolling(false);
        messageApi.success('Импорт и смена паролей завершены');
      }
    };

    const id = setInterval(tick, 3500);
    tick();
    return () => clearInterval(id);
  }, [importPolling, watchedIds, autoChangePassword, loadAccounts, messageApi, user.id]);

  const handleBulkCreate = async () => {
    if (!bulkCreds.trim()) {
      messageApi.warning('Вставьте список log:pass');
      return;
    }
    setBulkSubmitting(true);
    passwordChangedRef.current = new Set();
    try {
      await api.post(`/users/${user.id}/vk_accounts/create_accounts`, { creds: bulkCreds.trim() });
      messageApi.success('Аккаунты поставлены в очередь Selenium');
      const list = await loadAccounts(true);
      const logins = new Set(parseLoginsFromCreds(bulkCreds));
      const ids = list.filter((a) => a.login && logins.has(String(a.login).trim())).map((a) => a.id);
      setWatchedIds(ids);
      setImportPolling(ids.length > 0);
      setBulkCreds('');
    } catch (e) {
      messageApi.error(e.response?.data?.detail || 'Ошибка create_accounts');
    } finally {
      setBulkSubmitting(false);
    }
  };

  const handleAutocurl = async () => {
    if (!autocurlCreds.trim() || !autocurlGroups.trim()) {
      messageApi.warning('Нужны и log:pass, и ссылки на паблики (по одной на строку, zip 1:1)');
      return;
    }
    const cid = Number(autocurlCategoryId);
    if (!cid) {
      messageApi.warning('Выберите категорию');
      return;
    }
    setAutocurlSubmitting(true);
    try {
      await api.post(`/users/${user.id}/vk_accounts/create_accounts_autocurl_backup`, {
        creds: autocurlCreds.trim(),
        groups: autocurlGroups.trim(),
        category_id: cid,
      });
      messageApi.success('Парный импорт (autocurl) запущен');
      setAutocurlCreds('');
      setAutocurlGroups('');
      await loadAccounts(true);
    } catch (e) {
      messageApi.error(e.response?.data?.detail || 'Ошибка autocurl');
    } finally {
      setAutocurlSubmitting(false);
    }
  };

  const handleChangePasswordOne = async (accountId) => {
    setChangingPwId(accountId);
    try {
      const { data } = await api.post(`/users/${user.id}/vk_accounts/change_passwords_by_ids`, {
        vk_account_ids: [accountId],
      });
      const r = data?.results?.[0];
      if (r?.ok) messageApi.success('Пароль обновлён на сервере');
      else messageApi.error(r?.detail || 'Не удалось сменить пароль');
      await loadAccounts(true);
    } catch (e) {
      messageApi.error(e.response?.data?.detail || 'Ошибка смены пароля');
    } finally {
      setChangingPwId(null);
    }
  };

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

  const queueLabel =
    watchedIds.length > 0
      ? `Отслеживание импорта: ${pendingWatchCount} из ${watchedIds.length}`
      : null;

  return (
    <div className="animate-in fade-in space-y-8 duration-300">
      {contextHolder}

      <section className="rounded-3xl border border-gray-100 bg-white p-8 shadow-sm">
        <h3 className="mb-2 flex items-center gap-2 text-xl font-black text-gray-800">
          <Server size={22} className="text-blue-600" />
          Импорт log:pass (очередь Selenium)
        </h3>
        <p className="mb-6 text-sm font-medium text-gray-500">
          Аккаунты попадают в БД и обрабатываются в фоне. Новые пароли хранятся на сервере — копировать их не нужно.
        </p>
        <div className="flex flex-col gap-6 lg:flex-row">
          <div className="min-w-0 flex-1">
            <label className="mb-2 block text-xs font-black uppercase tracking-widest text-gray-400">
              Список (логин:пароль, по строке)
            </label>
            <textarea
              className="h-40 w-full resize-none rounded-2xl border border-gray-100 bg-gray-50 p-4 font-mono text-sm text-gray-800 outline-none focus:ring-4 focus:ring-blue-100"
              placeholder={'79001234567:password\n79007654321:password'}
              value={bulkCreds}
              onChange={(e) => setBulkCreds(e.target.value)}
            />
          </div>
          <div className="flex w-full shrink-0 flex-col justify-end gap-4 rounded-2xl border border-gray-100 bg-gray-50/80 p-6 lg:w-80">
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-blue-100 bg-white p-4 shadow-sm">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                checked={autoChangePassword}
                onChange={(e) => setAutoChangePassword(e.target.checked)}
              />
              <span>
                <span className="font-bold text-gray-900">Авто-смена пароля</span>
                <span className="mt-1 block text-xs font-medium text-gray-500">
                  После успешного входа (parse_status=success) пароль меняется на сервере по API, без ручного
                  копирования.
                </span>
              </span>
            </label>
            <button
              type="button"
              disabled={bulkSubmitting}
              onClick={handleBulkCreate}
              className="flex items-center justify-center gap-2 rounded-2xl bg-blue-600 py-4 font-bold text-white shadow-lg shadow-blue-100 transition-all hover:bg-blue-700 disabled:opacity-60"
            >
              {bulkSubmitting ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
              Поставить в очередь
            </button>
            {queueLabel && (
              <p className="text-center text-xs font-semibold text-amber-800">{queueLabel}</p>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-dashed border-indigo-200 bg-indigo-50/40 p-6 shadow-sm">
        <h3 className="mb-2 text-lg font-black text-indigo-950">Парный импорт (log:pass + паблик, как в V1)</h3>
        <p className="mb-4 text-sm text-indigo-900/80">
          Если паблики ещё не привязаны к backup-аккаунтам, используйте zip: одна строка log:pass на одну строку
          ссылки.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <textarea
            className="h-32 w-full resize-none rounded-xl border border-indigo-100 bg-white p-3 font-mono text-xs"
            placeholder="log:pass по строкам"
            value={autocurlCreds}
            onChange={(e) => setAutocurlCreds(e.target.value)}
          />
          <textarea
            className="h-32 w-full resize-none rounded-xl border border-indigo-100 bg-white p-3 font-mono text-xs"
            placeholder="https://vk.com/public… по строкам"
            value={autocurlGroups}
            onChange={(e) => setAutocurlGroups(e.target.value)}
          />
        </div>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs font-bold text-indigo-900">Категория</label>
            <select
              className="min-w-[200px] rounded-xl border border-indigo-100 bg-white px-3 py-2 text-sm"
              value={autocurlCategoryId}
              onChange={(e) => setAutocurlCategoryId(e.target.value)}
            >
              <option value="">—</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} (#{c.id})
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            disabled={autocurlSubmitting}
            onClick={handleAutocurl}
            className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {autocurlSubmitting ? 'Отправка…' : 'Запустить autocurl'}
          </button>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
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
              Проверка curl, переподключение, удаление — те же endpoint&apos;ы. Статусы парсинга обновляются при
              «Обновить список» и во время отслеживания импорта.
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
          <div className="max-h-[640px] flex-1 divide-y divide-gray-100 overflow-y-auto">
            {filtered.map((a) => (
              <div
                key={a.id}
                className="flex flex-col gap-3 p-5 px-8 transition-colors hover:bg-gray-50/50 sm:flex-row sm:items-center sm:justify-between"
              >
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
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-lg border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${statusBadgeClass(a.parse_status)}`}
                      >
                        {a.parse_status || '—'}
                      </span>
                      {a.task_id ? (
                        <span className="font-mono text-[10px] text-gray-400" title="Celery task id">
                          task {String(a.task_id).slice(0, 12)}…
                        </span>
                      ) : null}
                    </div>
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
                  {a.account_type === 'backup' && a.parse_status === 'success' && (
                    <button
                      type="button"
                      disabled={changingPwId === a.id}
                      onClick={() => handleChangePasswordOne(a.id)}
                      className="rounded-xl bg-violet-50 px-3 py-2 text-xs font-bold text-violet-800 transition-all hover:bg-violet-100 disabled:opacity-50"
                      title="Сменить пароль на сервере (старый пароль из БД)"
                    >
                      {changingPwId === a.id ? (
                        '…'
                      ) : (
                        <>
                          <KeyRound size={14} className="mr-1 inline" />
                          Сменить пароль
                        </>
                      )}
                    </button>
                  )}
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
    </div>
  );
}
