import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { message, Tooltip } from 'antd';
import {
  Copy,
  ExternalLink,
  KeyRound,
  Loader2,
  Play,
  Plus,
  RefreshCcw,
  Search,
  Server,
  Trash2,
} from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';
import {
  PARSE_STATUS_FILTER_OPTIONS,
  getAccountCurl,
  matchesParseStatusFilter,
} from '../../utils/accountFilters';

/** Та же очередь, что в V1 AccountChecker (общий localStorage). */
const QUEUE_STORAGE_KEY = 'account_checker_queue_v1';
const MAX_BATCH_SIZE = 20;
const BATCH_POLL_MS = 2000;

/** После перезагрузки: не помечаем пачку ошибкой — опрос к API продолжится. «Прервано» только при сбое опроса (см. tick). */
function normalizeQueueFromStorage(items) {
  if (!Array.isArray(items)) {
    return { items: [], changed: false };
  }
  let changed = false;
  const next = items.map((b) => {
    if (b.status === 'running' && !b.serverBatchId) {
      changed = true;
      return {
        ...b,
        status: 'pending',
        detail: undefined,
      };
    }
    return b;
  });
  return { items: next, changed };
}

function isBatchPollServiceUnreachable(error) {
  if (!error?.response) {
    return error?.code === 'ERR_NETWORK' || error?.message === 'Network Error';
  }
  const s = error.response.status;
  return s === 502 || s === 503 || s === 504;
}

async function waitForServerBatchComplete(apiInstance, userId, batchId) {
  if (!batchId) return null;
  for (;;) {
    const { data } = await apiInstance.get(`/tools/${userId}/account_checker/batch/${batchId}`);
    if (data?.status === 'completed') {
      return data;
    }
    await new Promise((r) => setTimeout(r, BATCH_POLL_MS));
  }
}

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

function batchStripeClass(batchId) {
  if (batchId == null || batchId === undefined) return '';
  const idx = Math.abs(Number(batchId)) % 4;
  const stripe = [
    'border-l-[5px] border-l-sky-500 bg-sky-50/50',
    'border-l-[5px] border-l-violet-500 bg-violet-50/50',
    'border-l-[5px] border-l-amber-500 bg-amber-50/50',
    'border-l-[5px] border-l-emerald-500 bg-emerald-50/50',
  ];
  return stripe[idx];
}

function loginPassLine(account) {
  const login = (account.login || '').trim();
  const password = (account.password || '').trim();
  if (login && password) return `${login}:${password}`;
  if (login) return login;
  return '—';
}

function vkFullName(account) {
  const s = [account.name, account.second_name].filter(Boolean).join(' ').trim();
  return s || 'Имя и фамилия VK ещё не подтянулись';
}

function formatDuration(msValue) {
  const totalSeconds = Math.max(0, Math.floor(msValue / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function formatDurationSeconds(sec) {
  if (sec == null || Number.isNaN(Number(sec))) return '—';
  return formatDuration(Number(sec) * 1000);
}

function batchStatusMeta(status) {
  const map = {
    pending: { label: 'В ожидании', color: 'bg-amber-100 text-amber-900' },
    running: { label: 'На подключении', color: 'bg-blue-100 text-blue-900' },
    success: { label: 'Готово', color: 'bg-green-100 text-green-900' },
    error: { label: 'Ошибка', color: 'bg-red-100 text-red-900' },
  };
  return map[status] || { label: String(status), color: 'bg-gray-100 text-gray-800' };
}

/** Типы с паролем в БД: смена через API (как backup), включая Account Checker (checker / connect). */
const ACCOUNT_TYPES_WITH_PASSWORD_CHANGE = new Set(['backup', 'checker', 'connect', 'posting']);

function canShowChangePasswordButton(account) {
  if (account?.parse_status !== 'success') return false;
  return ACCOUNT_TYPES_WITH_PASSWORD_CHANGE.has(String(account.account_type || '').toLowerCase());
}

export default function AccountsView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [checkingId, setCheckingId] = useState(null);
  const [reconnectId, setReconnectId] = useState(null);
  const [reconnectingAll, setReconnectingAll] = useState(false);

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

  const [checkerInputAccounts, setCheckerInputAccounts] = useState('');
  const [batchNote, setBatchNote] = useState('');
  /** После успешного прогона пачки — сменить пароль на сервере. */
  const [batchAutoChangePassword, setBatchAutoChangePassword] = useState(false);
  const [connectingBatchId, setConnectingBatchId] = useState(null);
  const [batchQueue, setBatchQueue] = useState(() => {
    try {
      const raw = localStorage.getItem(QUEUE_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      const { items, changed } = normalizeQueueFromStorage(parsed);
      if (changed) {
        try {
          localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(items));
        } catch {
          /* ignore */
        }
      }
      return items;
    } catch {
      return [];
    }
  });
  const batchQueueRef = useRef(batchQueue);
  useEffect(() => {
    batchQueueRef.current = batchQueue;
  }, [batchQueue]);

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
    const SERVICE_DOWN_DETAIL =
      'Подключение прервано: сервер недоступен или сервис остановлен. Удалите запись или добавьте пачку заново.';

    const tick = async () => {
      const q = batchQueueRef.current;
      const toPoll = q.filter((b) => b.status === 'running' && b.serverBatchId);
      if (!toPoll.length) return;
      for (const b of toPoll) {
        try {
          const { data } = await api.get(`/tools/${user.id}/account_checker/batch/${b.serverBatchId}`);
          if (!data) continue;
          if (data.status === 'completed') {
            const sec = data.duration_seconds ?? data.elapsed_seconds;
            setBatchQueue((prev) => {
              const next = prev.map((item) => {
                if (item.id !== b.id || item.status !== 'running') return item;
                return {
                  ...item,
                  status: 'success',
                  serverDurationSeconds: data.duration_seconds ?? sec,
                  serverPoll: data,
                };
              });
              try {
                localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(next));
              } catch {
                /* ignore */
              }
              return next;
            });
            void loadAccounts(true);
          } else {
            setBatchQueue((prev) => {
              const next = prev.map((item) => (item.id === b.id ? { ...item, serverPoll: data } : item));
              try {
                localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(next));
              } catch {
                /* ignore */
              }
              return next;
            });
          }
        } catch (e) {
          console.error(e);
          const status = e.response?.status;
          let detail = null;
          if (status === 404) {
            detail = 'Батч не найден на сервере. Удалите запись из очереди.';
          } else if (isBatchPollServiceUnreachable(e)) {
            detail = SERVICE_DOWN_DETAIL;
          }
          if (detail) {
            setBatchQueue((prev) => {
              const next = prev.map((item) =>
                item.id === b.id
                  ? {
                      ...item,
                      status: 'error',
                      detail,
                      serverPoll: undefined,
                    }
                  : item,
              );
              try {
                localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(next));
              } catch {
                /* ignore */
              }
              return next;
            });
          }
        }
      }
    };
    void tick();
    const id = setInterval(tick, BATCH_POLL_MS);
    return () => clearInterval(id);
  }, [user.id, loadAccounts]);

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
    let list = accounts.filter((a) => matchesParseStatusFilter(statusFilter, a.parse_status));
    if (q) {
      list = list.filter((a) =>
        [
          a.name,
          a.second_name,
          loginPassLine(a),
          a.login,
          a.password,
          String(a.vk_account_id),
          a.account_type,
          a.checker_batch_label,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(q),
      );
    }
    list.sort((a, b) => (Number(b.id) || 0) - (Number(a.id) || 0));
    return list;
  }, [accounts, search, statusFilter]);

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

  const saveBatchQueue = useCallback((nextQueue) => {
    setBatchQueue(nextQueue);
    try {
      localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(nextQueue));
    } catch {
      /* ignore */
    }
  }, []);

  const parseCheckerAccounts = () =>
    checkerInputAccounts
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

  const validateBatchLimit = (accLines) => {
    if (accLines.length > MAX_BATCH_SIZE) {
      messageApi.warning(`Максимум ${MAX_BATCH_SIZE} аккаунтов в одной пачке.`);
      return false;
    }
    return true;
  };

  const handleAddCheckerBatch = () => {
    const accLines = parseCheckerAccounts();
    if (!accLines.length) {
      messageApi.warning('Нельзя добавить пустую пачку.');
      return;
    }
    if (!validateBatchLimit(accLines)) return;
    const batch = {
      id: Date.now(),
      note: batchNote.trim(),
      accounts: accLines,
      status: 'pending',
      createdAt: new Date().toISOString(),
    };
    saveBatchQueue([batch, ...batchQueue]);
    setCheckerInputAccounts('');
    setBatchNote('');
    messageApi.success('Пачка в очереди. Запустите кнопкой «Запустить» на карточке.');
  };

  const handleRemoveCheckerBatch = (batchId) => {
    saveBatchQueue(batchQueue.filter((item) => item.id !== batchId));
  };

  const handleRunCheckerBatch = async (batchId) => {
    const nextQueue = [...batchQueueRef.current];
    const index = nextQueue.findIndex((item) => item.id === batchId);
    if (index < 0) return;
    const batch = nextQueue[index];
    if (batch.status !== 'pending') {
      messageApi.info('Пачка уже не в ожидании.');
      return;
    }
    setConnectingBatchId(batchId);
    nextQueue[index] = { ...nextQueue[index], status: 'running' };
    saveBatchQueue([...nextQueue]);
    const runBatchPw = batchAutoChangePassword;
    let serverBatchIdForPw = null;
    try {
      const { data: submit } = await api.post(`/tools/${user.id}/account_checker`, {
        accounts: batch.accounts,
        batch_label: batch.note || undefined,
      });
      if (submit.batch_id) {
        serverBatchIdForPw = submit.batch_id;
        nextQueue[index] = {
          ...nextQueue[index],
          status: 'running',
          serverBatchId: submit.batch_id,
        };
        saveBatchQueue([...nextQueue]);
        const final = await waitForServerBatchComplete(api, user.id, submit.batch_id);
        const sec = final.duration_seconds ?? final.elapsed_seconds;
        nextQueue[index] = {
          ...nextQueue[index],
          status: 'success',
          serverBatchId: submit.batch_id,
          serverDurationSeconds: final.duration_seconds ?? sec,
          serverPoll: final,
        };
      } else {
        nextQueue[index] = {
          ...nextQueue[index],
          status: 'success',
          serverBatchId: null,
          serverDurationSeconds: null,
          noNewAccounts: true,
        };
      }
    } catch (error) {
      console.error(error);
      nextQueue[index] = {
        ...nextQueue[index],
        status: 'error',
        detail: error?.response?.data?.detail || 'Ошибка отправки пачки',
      };
    }
    saveBatchQueue([...nextQueue]);
    setConnectingBatchId(null);
    const result = nextQueue[index];
    if (result.status === 'success') {
      if (result.noNewAccounts) {
        messageApi.success('Нет новых аккаунтов (все логины уже в базе).');
        await loadAccounts(true);
      } else {
        let list = await loadAccounts(true);
        let pwToast = false;
        if (runBatchPw && serverBatchIdForPw != null) {
          const bid = Number(serverBatchIdForPw);
          const ids = list
            .filter(
              (a) =>
                Number(a.account_checker_batch_id) === bid &&
                String(a.parse_status).toLowerCase() === 'success',
            )
            .map((a) => a.id);
          if (ids.length) {
            try {
              const { data } = await api.post(`/users/${user.id}/vk_accounts/change_passwords_by_ids`, {
                vk_account_ids: ids,
              });
              for (const r of data?.results || []) {
                if (!r.ok)
                  messageApi.warning(
                    `Смена пароля #${r.vk_account_id}${r.login ? ` (${r.login})` : ''}: ${r.detail || 'ошибка'}`,
                  );
              }
              pwToast = true;
            } catch (e) {
              messageApi.error(e.response?.data?.detail || 'Ошибка авто-смены пароля для пачки');
            }
            await loadAccounts(true);
          }
        }
        messageApi.success(
          pwToast ? 'Пачка подключена. Пароли сменены на сервере (где удалось).' : 'Пачка подключена.',
        );
      }
    } else if (result.status === 'error') {
      messageApi.error(result.detail || 'Ошибка подключения пачки');
    }
  };

  const getBatchDurationInfo = (batch) => {
    if (batch.status === 'error' && batch.detail) {
      return { label: '—', sub: batch.detail };
    }
    if (batch.serverDurationSeconds != null) {
      return {
        label: formatDurationSeconds(batch.serverDurationSeconds),
        sub: 'фон (сервер): от приёма до готовности',
      };
    }
    if (batch.status === 'success' && batch.noNewAccounts) {
      return { label: '—', sub: 'все логины уже в базе' };
    }
    if (batch.status === 'running') {
      const sec =
        batch.serverPoll?.elapsed_seconds != null
          ? batch.serverPoll.elapsed_seconds
          : batch.serverPoll?.duration_seconds;
      if (sec != null && !Number.isNaN(Number(sec))) {
        return {
          label: formatDurationSeconds(sec),
          sub: 'время с момента приёма пачки (сервер)',
        };
      }
      if (batch.serverBatchId) {
        return { label: '00:00', sub: 'подключение на сервере…' };
      }
      return { label: '—', sub: 'отправка запроса…' };
    }
    if (batch.status === 'pending') {
      return { label: '—', sub: 'нажмите «Запустить»' };
    }
    return { label: '—', sub: '—' };
  };

  const handleBulkCreate = async () => {
    if (!bulkCreds.trim()) {
      messageApi.warning('Вставьте список log:pass');
      return;
    }
    setBulkSubmitting(true);
    passwordChangedRef.current = new Set();
    try {
      await api.post(`/users/${user.id}/vk_accounts/create_accounts`, { creds: bulkCreds.trim() });
      messageApi.success('Аккаунты поставлены в очередь импорта');
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

  const copyLoginPass = (account) => {
    const t = loginPassLine(account);
    if (!t || t === '—') {
      messageApi.warning('Нечего копировать');
      return;
    }
    navigator.clipboard.writeText(t).then(
      () => messageApi.success('log:pass скопирован'),
      () => messageApi.error('Не удалось скопировать'),
    );
  };

  const copyCurl = (account) => {
    const curl = getAccountCurl(account);
    if (!curl) return;
    navigator.clipboard.writeText(curl).then(
      () => messageApi.success('cURL скопирован в буфер'),
      () => messageApi.error('Не удалось скопировать'),
    );
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

  const pendingCount = useMemo(
    () => accounts.filter((a) => a.parse_status === 'pending').length,
    [accounts],
  );

  const handleReconnectAllPending = async () => {
    if (pendingCount === 0) {
      messageApi.info('Нет аккаунтов в статусе Pending');
      return;
    }
    if (
      !window.confirm(
        `Переподключить ${pendingCount} аккаунтов в статусе Pending? Старые задачи Celery будут отменены.`,
      )
    ) {
      return;
    }
    setReconnectingAll(true);
    try {
      const body = {};
      if (autocurlCategoryId) {
        body.category_id = Number(autocurlCategoryId);
      }
      const { data } = await api.post(`/users/${user.id}/vk_accounts/reconnect_pending`, body);
      const parts = [`В очередь: ${data.queued ?? 0}`];
      if (data.queued_autocurl) parts.push(`autocurl: ${data.queued_autocurl}`);
      if (data.queued_checker) parts.push(`checker: ${data.queued_checker}`);
      if (data.skipped_no_credentials) {
        parts.push(`без login:pass: ${data.skipped_no_credentials}`);
      }
      messageApi.success(parts.join(', '));
      await loadAccounts(true);
    } catch (err) {
      messageApi.error(err?.response?.data?.detail || 'Ошибка массового переподключения');
    } finally {
      setReconnectingAll(false);
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
        <h3 className="mb-2 text-lg font-black text-gray-800">Очередь пачек</h3>
        <p className="mb-4 text-sm text-gray-500">
          Импорт по login:password пачками: подпись, список строк, «Добавить в очередь», затем «Запустить» на карточке.
          Очередь хранится в браузере и совпадает с интерфейсом V1.
        </p>
        <div className="grid gap-8 xl:grid-cols-2">
          <div className="space-y-3">
            <label className="block text-xs font-black uppercase tracking-widest text-gray-400">
              Подпись пачки (заметка)
            </label>
            <input
              type="text"
              className="w-full rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm outline-none focus:ring-4 focus:ring-blue-100"
              placeholder="Например: клиент А, 12.05"
              value={batchNote}
              onChange={(e) => setBatchNote(e.target.value)}
            />
            <label className="block text-xs font-black uppercase tracking-widest text-gray-400">
              Аккаунты login:pass (до {MAX_BATCH_SIZE} строк)
            </label>
            <textarea
              className="h-44 w-full resize-none rounded-2xl border border-gray-100 bg-gray-50 p-4 font-mono text-sm outline-none focus:ring-4 focus:ring-blue-100"
              placeholder={'login1:pass1\nlogin2:pass2'}
              value={checkerInputAccounts}
              onChange={(e) => setCheckerInputAccounts(e.target.value)}
            />
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-100 bg-gray-50/80 p-4">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                checked={batchAutoChangePassword}
                onChange={(e) => setBatchAutoChangePassword(e.target.checked)}
              />
              <span>
                <span className="font-bold text-gray-900">Авто-смена пароля после пачки</span>
                <span className="mt-1 block text-xs font-medium text-gray-500">
                  После успешной пачки сменить пароль на сервере для аккаунтов со статусом success, без ручного
                  копирования.
                </span>
              </span>
            </label>
            <button
              type="button"
              onClick={handleAddCheckerBatch}
              className="inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-md hover:bg-blue-700"
            >
              <Plus size={16} />
              Добавить в очередь
            </button>
          </div>
          <div>
            <h4 className="mb-3 text-sm font-black uppercase tracking-widest text-gray-400">Очередь пачек</h4>
            <div className="max-h-[min(420px,50vh)] space-y-2 overflow-y-auto rounded-2xl border border-gray-100 bg-gray-50/50 p-3">
              {!batchQueue.length && (
                <p className="py-8 text-center text-sm text-gray-400">Очередь пуста</p>
              )}
              {batchQueue.map((item) => {
                const dur = getBatchDurationInfo(item);
                const st = batchStatusMeta(item.status);
                return (
                  <div
                    key={item.id}
                    className="flex flex-col gap-2 rounded-xl border border-gray-100 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-bold text-gray-900">{item.note || 'Без подписи'}</div>
                      <div className="text-xs text-gray-500">{item.accounts?.length ?? 0} аккаунтов</div>
                      <div className="mt-1 text-xs text-gray-500">
                        <span className="font-mono">{dur.label}</span>
                        <span> — {dur.sub}</span>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-lg px-2 py-1 text-xs font-bold ${st.color}`}>{st.label}</span>
                      {item.status === 'pending' && (
                        <button
                          type="button"
                          disabled={connectingBatchId === item.id}
                          onClick={() => void handleRunCheckerBatch(item.id)}
                          className="inline-flex items-center gap-1 rounded-xl bg-blue-600 px-3 py-2 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-60"
                        >
                          {connectingBatchId === item.id ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            <Play size={14} />
                          )}
                          Запустить
                        </button>
                      )}
                      <button
                        type="button"
                        disabled={connectingBatchId === item.id}
                        onClick={() => handleRemoveCheckerBatch(item.id)}
                        className="rounded-xl border border-red-100 px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-50 disabled:opacity-50"
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <details className="group rounded-3xl border border-gray-200 bg-gray-50/60 shadow-sm open:bg-white">
        <summary className="cursor-pointer list-none px-6 py-4 text-sm font-black text-gray-700 marker:content-none [&::-webkit-details-marker]:hidden">
          <span className="inline-flex items-center gap-2">
            Дополнительные способы добавления аккаунтов
            <span className="text-xs font-bold text-gray-400">(развернуть)</span>
          </span>
        </summary>
        <div className="space-y-8 border-t border-gray-200 px-6 pb-8 pt-2">
          <section className="rounded-3xl border border-gray-100 bg-white p-8 shadow-sm">
            <h3 className="mb-2 flex items-center gap-2 text-xl font-black text-gray-800">
              <Server size={22} className="text-blue-600" />
              Импорт log:pass
            </h3>
            <p className="mb-6 text-sm font-medium text-gray-500">
              Список backup-аккаунтов в формате login:password (по строке). Дальше — то же подключение, что у пачек
              выше. При включённой опции пароль после успешного входа обновится на сервере сам.
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
                      После успешного входа пароль обновится на сервере, без ручного копирования.
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
        </div>
      </details>

      <div className="flex w-full flex-col overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
        <div className="z-10 flex flex-wrap items-center justify-between gap-4 border-b border-gray-100 bg-white p-8">
          <span className="text-lg font-black text-gray-800">
            Всего аккаунтов: {loading ? '…' : accounts.length}
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => loadAccounts()}
              className="inline-flex items-center gap-2 rounded-2xl border border-gray-200 bg-white px-4 py-2.5 text-xs font-bold text-gray-700 transition-all hover:bg-gray-50"
            >
              <RefreshCcw size={14} />
              Обновить список
            </button>
            <button
              type="button"
              disabled={reconnectingAll || pendingCount === 0}
              onClick={handleReconnectAllPending}
              title={
                pendingCount === 0
                  ? 'Нет аккаунтов в статусе Pending'
                  : 'Повторно поставить в очередь все Pending (после сбоя сервера)'
              }
              className="inline-flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs font-bold text-amber-900 transition-all hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {reconnectingAll ? <Loader2 size={14} className="animate-spin" /> : <RefreshCcw size={14} />}
              Переподключить Pending{pendingCount > 0 ? ` (${pendingCount})` : ''}
            </button>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm font-bold text-gray-700 outline-none transition-all focus:ring-4 focus:ring-blue-100"
              aria-label="Фильтр по статусу"
            >
              {PARSE_STATUS_FILTER_OPTIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
              <input
                type="text"
                placeholder="Имя, login, пароль или login:pass…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-64 min-w-[12rem] rounded-2xl border border-gray-100 bg-gray-50 py-3 pl-11 pr-4 text-sm font-medium outline-none transition-all focus:ring-4 focus:ring-blue-100"
              />
            </div>
          </div>
        </div>
        <div className="max-h-[640px] flex-1 divide-y divide-gray-100 overflow-y-auto">
          {filtered.map((a) => (
            <div
              key={a.id}
              className={`flex flex-col gap-3 p-5 px-8 transition-colors hover:bg-gray-50/50 sm:flex-row sm:items-center sm:justify-between ${batchStripeClass(a.account_checker_batch_id)}`}
            >
              <div className="flex min-w-0 flex-1 items-center gap-5">
                <img
                  src={a.avatar_url || 'https://placehold.co/48x48/f3f4f6/6b7280?text=VK'}
                  alt=""
                  className="h-12 w-12 shrink-0 rounded-2xl object-cover"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Tooltip title={vkFullName(a)} placement="topLeft">
                      <span className="cursor-default font-mono text-sm font-bold tracking-tight text-gray-900 select-all">
                        {loginPassLine(a)}
                      </span>
                    </Tooltip>
                    <button
                      type="button"
                      onClick={() => copyLoginPass(a)}
                      className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-blue-600"
                      title="Копировать log:pass"
                      aria-label="Копировать log:pass"
                    >
                      <Copy size={16} />
                    </button>
                  </div>
                  <p className="mt-1 text-xs font-medium text-gray-500">
                    тип: <span className="font-bold text-blue-600">{a.account_type}</span>
                    {a.proxy_id ? ` • proxy #${a.proxy_id}` : ''}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-lg border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${statusBadgeClass(a.parse_status)}`}
                    >
                      {a.parse_status || '—'}
                    </span>
                    {a.checker_batch_label ? (
                      <span className="max-w-[14rem] truncate rounded-md bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-900">
                        {a.checker_batch_label}
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
                {getAccountCurl(a) ? (
                  <button
                    type="button"
                    onClick={() => copyCurl(a)}
                    className="rounded-xl bg-slate-50 px-4 py-2 text-xs font-bold text-slate-700 transition-all hover:bg-slate-200"
                  >
                    Копировать cURL
                  </button>
                ) : null}
                {canShowChangePasswordButton(a) && (
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
  );
}
