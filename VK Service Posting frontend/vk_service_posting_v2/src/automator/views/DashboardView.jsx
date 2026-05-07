import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { Activity, AlertCircle, Database, TrendingUp, Search, Download, X, Filter, ChevronRight } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

const HISTORY_MODAL_HOURS = 24;

function clipsWord(n) {
  const m = n % 100;
  const m10 = n % 10;
  if (m >= 11 && m <= 14) return 'клипов';
  if (m10 === 1) return 'клип';
  if (m10 >= 2 && m10 <= 4) return 'клипа';
  return 'клипов';
}

function formatHourLabel(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' });
}

function logLine(item) {
  if (item.message) return item.message;
  const g = item.group_name || '—';
  if (item.status === 'success') return `Опубликован клип в «${g}»`;
  if (item.status === 'starting') return `В очереди на публикацию в «${g}»`;
  return `Событие в «${g}» (${item.status})`;
}

function logDotClass(status, group) {
  if (group === 'error' || status === 'error' || status === 'failure' || status === 'failed') return 'bg-red-500';
  if (group === 'warning' || status === 'warning') return 'bg-amber-500';
  if (group === 'info' || status === 'info') return 'bg-blue-500';
  if (group === 'proxy') return 'bg-violet-500';
  if (group === 'worker') return 'bg-cyan-500';
  if (group === 'workerpost') return 'bg-cyan-500';
  if (group === 'posting') return 'bg-green-500';
  if (group === 'schedule') return 'bg-slate-500';
  if (group === 'source') return 'bg-indigo-500';
  if (group === 'account_checker') return 'bg-orange-500';
  if (group === 'account') return 'bg-amber-500';
  if (group === 'group') return 'bg-indigo-500';
  if (group === 'clip') return 'bg-fuchsia-500';
  if (status === 'success') return 'bg-green-500';
  if (status === 'starting') return 'bg-blue-500';
  return 'bg-red-500';
}

function groupLabel(group) {
  const map = {
    post: 'Post',
    worker: 'Worker',
    account: 'Account',
    group: 'Group',
    clip: 'Clip',
    proxy: 'Proxy',
    task: 'Task',
    error: 'Error',
    warning: 'Warning',
    info: 'Info',
    manual: 'Manual',
    source: 'Source',
    workerpost: 'Workerpost',
    posting: 'Posting',
    schedule: 'Schedule',
    account_checker: 'Checker',
  };
  return map[group] || group;
}

function formatHistoryTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/** Короткий ID для бейджа в полной истории */
function historyEventId(item) {
  if (item.live_log_id != null) return `LOG-${item.live_log_id}`;
  if (item.group === 'post' && item.workerpost_id != null) return `POST-${item.workerpost_id}`;
  if (item.group === 'worker' && item.workerpost_id != null) return `WRK-${item.workerpost_id}`;
  if (item.vk_account_id != null) return `ACC-${item.vk_account_id}`;
  if (item.proxy_id != null) return `PRX-${item.proxy_id}`;
  if (item.task_id != null) {
    const tid = String(item.task_id);
    return tid.length > 12 ? `TSK-${tid.slice(0, 8)}` : `TSK-${tid}`;
  }
  return '—';
}

function getHistoryBadgeType(item) {
  const status = (item.status || '').toLowerCase();
  const group = (item.group || '').toLowerCase();

  if (group === 'error' || status === 'error' || status === 'failure' || status === 'failed') return 'error';
  if (group === 'warning' || status === 'warning') return 'error';

  if (status === 'success' || status === 'active') return 'success';
  if (group === 'post' && status === 'success') return 'success';

  if (group === 'post' && status && status !== 'starting' && status !== 'success') return 'error';
  if (group === 'account') {
    if (status && /fail|error|flood|ban|invalid|blocked/i.test(status)) return 'error';
    if (status === 'success' || status === 'valid') return 'success';
  }

  return 'info';
}

function historyBadgeClass(badgeType) {
  if (badgeType === 'success') return 'bg-green-100 text-green-700';
  if (badgeType === 'error') return 'bg-red-100 text-red-700';
  return 'bg-blue-100 text-blue-700';
}

function historyTargetLabel(item) {
  if (item.group_name) return item.group_name;
  return groupLabel(item.group || 'post');
}

function matchesHistorySearch(item, q) {
  const hay = [
    item.message,
    item.description,
    item.logdescription,
    item.group,
    item.status,
    item.group_name,
    historyEventId(item),
    item.live_log_id,
    item.workerpost_id,
    item.vk_account_id,
    item.proxy_id,
    item.task_id,
  ]
    .filter((v) => v != null && v !== '')
    .map((v) => String(v).toLowerCase())
    .join(' ');
  return hay.includes(q);
}

function historyQuickFilterPass(item, quick) {
  if (quick === 'all') return true;
  const t = getHistoryBadgeType(item);
  if (quick === 'success') return t === 'success';
  if (quick === 'errors') return t === 'error';
  if (quick === 'system') return t === 'info';
  return true;
}

function buildHistoryLogFileContent(items) {
  return items
    .map((item) => {
      const t = item.at ? new Date(item.at).toISOString() : '—';
      const id = historyEventId(item);
      const msg = item.message || logLine(item);
      const tgt = historyTargetLabel(item);
      const desc = item.description || item.logdescription || '';
      const line = `[${t}] ${id} | ${msg}`;
      return desc ? `${line} | ${desc} | ${tgt}` : `${line} | ${tgt}`;
    })
    .join('\n');
}

function downloadHistoryLog(items) {
  const text = buildHistoryLogFileContent(items);
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `vk-automator-events-${new Date().toISOString().slice(0, 10)}.log`;
  a.click();
  URL.revokeObjectURL(url);
}

function LoadingValue() {
  return <span className="inline-block h-8 w-16 animate-pulse rounded-lg bg-gray-100 align-middle" />;
}

function StatCard({ stat }) {
  const hasError = stat.status === 'error';

  return (
    <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="mb-4 flex items-start justify-between">
        <div className={`rounded-2xl p-3.5 ${stat.bg} ${stat.color}`}>
          <stat.icon size={24} />
        </div>
        <span className={`rounded-xl px-2.5 py-1.5 text-[11px] font-black uppercase tracking-wider ${stat.bg} ${stat.color}`}>
          {hasError ? 'ошибка' : stat.change}
        </span>
      </div>
      <h4 className="mb-1 text-sm font-bold text-gray-500">{stat.label}</h4>
      <p className="text-3xl font-black text-gray-800">
        {stat.status === 'loading' ? <LoadingValue /> : stat.value}
      </p>
      {hasError && <p className="mt-2 text-xs font-semibold text-red-500">Не удалось загрузить данные</p>}
    </div>
  );
}

function ActivitySkeleton() {
  return (
    <div className="flex h-52 items-end justify-between gap-1 px-1">
      {Array.from({ length: 24 }, (_, index) => (
        <div
          key={index}
          className="min-h-[10px] flex-1 animate-pulse rounded-t-sm bg-blue-50"
          style={{ height: `${18 + ((index * 17) % 58)}%` }}
        />
      ))}
    </div>
  );
}

function LogSkeleton() {
  return (
    <ul className="max-h-[min(22rem,55vh)] space-y-4 overflow-y-auto pr-1">
      {Array.from({ length: 5 }, (_, index) => (
        <li key={index} className="flex gap-3 text-sm">
          <span className="mt-1.5 h-2 w-2 shrink-0 animate-pulse rounded-full bg-blue-100" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="h-4 w-11/12 animate-pulse rounded bg-gray-100" />
            <div className="h-3 w-1/3 animate-pulse rounded bg-gray-100" />
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function DashboardView() {
  const user = useAutomatorUser();
  const [, contextHolder] = message.useMessage();
  const [summary, setSummary] = useState(null);
  const [clipsTotal, setClipsTotal] = useState(0);
  const [buckets, setBuckets] = useState([]);
  const [logItems, setLogItems] = useState([]);
  const [logGroupsAvailable, setLogGroupsAvailable] = useState(['post', 'worker', 'account', 'group', 'clip', 'proxy', 'task']);
  const [selectedLogGroups, setSelectedLogGroups] = useState(['post', 'worker', 'account', 'group', 'clip', 'proxy', 'task']);
  const [summaryStatus, setSummaryStatus] = useState('loading');
  const [clipsStatus, setClipsStatus] = useState('loading');
  const [activityStatus, setActivityStatus] = useState('loading');
  const [logStatus, setLogStatus] = useState('loading');
  const [liveLogErrorCount, setLiveLogErrorCount] = useState(0);
  const [showLogModal, setShowLogModal] = useState(false);
  const [historyItems, setHistoryItems] = useState([]);
  const [historyStatus, setHistoryStatus] = useState('idle');
  const [historySearch, setHistorySearch] = useState('');
  const [historySelectedGroups, setHistorySelectedGroups] = useState([]);
  const [historyQuickFilter, setHistoryQuickFilter] = useState('all');
  const [historyLastRefresh, setHistoryLastRefresh] = useState(null);

  const loadSummary = useCallback(async (isCurrent = () => true) => {
    setSummaryStatus('loading');
    try {
      const { data } = await api.get(`/users/${user.id}/vk_accounts/v2_summary`);
      if (!isCurrent()) return;
      setSummary(data);
      setSummaryStatus('success');
    } catch {
      if (!isCurrent()) return;
      setSummary(null);
      setSummaryStatus('error');
    }
  }, [user.id]);

  const loadClipsTotal = useCallback(async (isCurrent = () => true) => {
    setClipsStatus('loading');
    try {
      const { data } = await api.get(`/users/${user.id}/clip_list/get_all`);
      if (!isCurrent()) return;
      const lists = Array.isArray(data) ? data : [];
      setClipsTotal(lists.reduce((acc, row) => acc + (Number(row.count) || 0), 0));
      setClipsStatus('success');
    } catch {
      if (!isCurrent()) return;
      setClipsTotal(0);
      setClipsStatus('error');
    }
  }, [user.id]);

  const loadPostingActivity = useCallback(async (isCurrent = () => true) => {
    setActivityStatus('loading');
    try {
      const { data } = await api.get(`/users/${user.id}/dashboard/v2/posting_activity`, { params: { hours: 24 } });
      if (!isCurrent()) return;
      setBuckets(Array.isArray(data?.buckets) ? data.buckets : []);
      setActivityStatus('success');
    } catch {
      if (!isCurrent()) return;
      setBuckets([]);
      setActivityStatus('error');
    }
  }, [user.id]);

  const loadActivityLog = useCallback(async (isCurrent = () => true) => {
    setLogStatus('loading');
    try {
      const { data } = await api.get(`/users/${user.id}/dashboard/v2/activity_log`, { params: { limit: 25 } });
      if (!isCurrent()) return;
      const apiItems = Array.isArray(data?.items) ? data.items : [];
      const apiGroups = Array.isArray(data?.groups_available)
        ? data.groups_available
        : ['post', 'worker', 'account', 'group', 'clip', 'proxy', 'task'];
      setLogItems(apiItems);
      setLiveLogErrorCount(Number(data?.error_count) || 0);
      setLogGroupsAvailable(apiGroups);
      setSelectedLogGroups((prev) => {
        if (!Array.isArray(prev) || prev.length === 0) return apiGroups;
        const keep = prev.filter((g) => apiGroups.includes(g));
        const newlyAvailable = apiGroups.filter((g) => !prev.includes(g));
        const next = [...keep, ...newlyAvailable];
        return next.length > 0 ? next : apiGroups;
      });
      setLogStatus('success');
    } catch {
      if (!isCurrent()) return;
      setLogItems([]);
      setLiveLogErrorCount(0);
      setLogGroupsAvailable(['post', 'worker', 'account', 'group', 'clip', 'proxy', 'task']);
      setLogStatus('error');
    }
  }, [user.id]);

  const fetchHistoryForModal = useCallback(
    async ({ silent = false, isCurrent = () => true } = {}) => {
      if (!silent) setHistoryStatus('loading');
      try {
        const params = { limit: 500, hours: HISTORY_MODAL_HOURS };
        if (historySelectedGroups.length > 0) {
          params.groups = historySelectedGroups;
        }
        const { data } = await api.get(`/users/${user.id}/dashboard/v2/activity_log`, { params });
        if (!isCurrent()) return;
        setHistoryItems(Array.isArray(data?.items) ? data.items : []);
        setHistoryStatus('success');
        setHistoryLastRefresh(new Date());
      } catch {
        if (!isCurrent()) return;
        if (!silent) {
          setHistoryItems([]);
          setHistoryStatus('error');
        }
      }
    },
    [historySelectedGroups, user.id],
  );

  useEffect(() => {
    if (!showLogModal) return undefined;
    let cancelled = false;
    const isCurrent = () => !cancelled;

    fetchHistoryForModal({ isCurrent });
    const intervalId = setInterval(() => fetchHistoryForModal({ silent: true, isCurrent }), 5000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [showLogModal, fetchHistoryForModal]);

  const openHistoryModal = () => {
    const next = selectedLogGroups.filter((g) => logGroupsAvailable.includes(g));
    setHistorySelectedGroups(next.length > 0 ? next : [...logGroupsAvailable]);
    setHistorySearch('');
    setHistoryQuickFilter('all');
    setShowLogModal(true);
  };

  const closeHistoryModal = () => setShowLogModal(false);

  const toggleHistoryModalGroup = (group) => {
    setHistorySelectedGroups((prev) => {
      if (prev.includes(group)) {
        const next = prev.filter((g) => g !== group);
        return next.length > 0 ? next : [...logGroupsAvailable];
      }
      return [...prev, group];
    });
  };

  useEffect(() => {
    if (!showLogModal) return undefined;
    const Esc = (e) => {
      if (e.key === 'Escape') setShowLogModal(false);
    };
    window.addEventListener('keydown', Esc);
    return () => window.removeEventListener('keydown', Esc);
  }, [showLogModal]);

  useEffect(() => {
    let isMounted = true;
    const isCurrent = () => isMounted;

    loadSummary(isCurrent);
    loadClipsTotal(isCurrent);
    loadPostingActivity(isCurrent);
    loadActivityLog(isCurrent);

    return () => {
      isMounted = false;
    };
  }, [loadActivityLog, loadClipsTotal, loadPostingActivity, loadSummary]);

  const maxPosted = useMemo(() => {
    const m = Math.max(0, ...buckets.map((b) => Number(b.posted) || 0));
    return m > 0 ? m : 1;
  }, [buckets]);

  const filteredLogItems = useMemo(
    () => logItems.filter((item) => selectedLogGroups.includes(item.group || 'post')),
    [logItems, selectedLogGroups],
  );

  const historyDisplayItems = useMemo(() => {
    const q = historySearch.trim().toLowerCase();
    return historyItems.filter((item) => {
      if (!historyQuickFilterPass(item, historyQuickFilter)) return false;
      if (!q) return true;
      return matchesHistorySearch(item, q);
    });
  }, [historyItems, historyQuickFilter, historySearch]);

  const historyErrorCount = useMemo(
    () => historyDisplayItems.filter((item) => getHistoryBadgeType(item) === 'error').length,
    [historyDisplayItems],
  );

  const toggleLogGroup = (group) => {
    setSelectedLogGroups((prev) => {
      if (prev.includes(group)) return prev.filter((g) => g !== group);
      return [...prev, group];
    });
  };

  const stats = [
    {
      label: 'Аккаунтов ВК',
      value: summary?.total_accounts ?? '—',
      change: `${summary?.by_status?.success ?? 0} success`,
      icon: TrendingUp,
      color: 'text-green-600',
      bg: 'bg-green-50',
      status: summaryStatus,
    },
    {
      label: 'Активных воркеров',
      value: summary?.workflow_count ?? '—',
      change: 'workerpost',
      icon: Activity,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      status: summaryStatus,
    },
    {
      label: 'Клипов в базах',
      value: clipsTotal.toLocaleString('ru-RU'),
      change: 'сумма по спискам',
      icon: Database,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
      status: clipsStatus,
    },
    {
      label: 'Проблемы',
      value: liveLogErrorCount,
      change: 'в ленте событий',
      icon: AlertCircle,
      color: 'text-red-600',
      bg: 'bg-red-50',
      status: logStatus,
    },
  ];

  return (
    <div className="space-y-8">
      {contextHolder}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
        <div className="self-start rounded-3xl border border-gray-100 bg-white p-8 shadow-sm lg:col-span-2">
          <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-gray-800">Детализация</h3>
              <p className="mt-1 text-sm font-medium text-gray-500">Активность постинга (24ч), успешные публикации по часам (UTC)</p>
            </div>
          </div>
          {activityStatus === 'loading' ? (
            <ActivitySkeleton />
          ) : activityStatus === 'error' ? (
            <div className="flex h-52 items-center justify-center rounded-2xl border border-dashed border-red-100 bg-red-50/40 px-4 text-center text-sm font-semibold text-red-500">
              Не удалось загрузить активность постинга
            </div>
          ) : (
            <div className="flex h-52 items-end justify-between gap-1 px-1">
              {buckets.length === 0 ? (
                <p className="m-auto text-sm text-gray-500">Нет данных активности за выбранный период</p>
              ) : buckets.map((b, i) => {
                const n = Number(b.posted) || 0;
                const pct = Math.max(4, (n / maxPosted) * 100);
                const hour = formatHourLabel(b.hour_start);
                const nextIso = buckets[i + 1]?.hour_start;
                const hourEnd = nextIso
                  ? formatHourLabel(nextIso)
                  : b.hour_start
                    ? formatHourLabel(new Date(new Date(b.hour_start).getTime() + 3600000).toISOString())
                    : '';
                const range = hour && hourEnd ? `${hour}–${hourEnd}` : hour;
                const tip = `${n} ${clipsWord(n)}${range ? ` · ${range}` : ''}`;
                return (
                  <div key={`${b.hour_start}-${i}`} className="group relative flex h-full min-w-0 flex-1 flex-col justify-end">
                    <div
                      className="w-full min-h-[4px] cursor-default rounded-t-sm bg-blue-100 transition-colors group-hover:bg-blue-500"
                      style={{ height: `${pct}%` }}
                      title={tip}
                    />
                    <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 rounded-lg bg-gray-900 px-2.5 py-1.5 text-center text-xs font-semibold text-white shadow-lg group-hover:block whitespace-nowrap">
                      {tip}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="self-start rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <Activity className="text-blue-500" size={20} />
            <h3 className="text-lg font-bold text-gray-800">Живой лог</h3>
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            {logGroupsAvailable.map((group) => {
              const checked = selectedLogGroups.includes(group);
              return (
                <label
                  key={group}
                  className={`inline-flex cursor-pointer items-center gap-2 rounded-xl border px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                    checked
                      ? 'border-blue-300 bg-blue-50 text-blue-700'
                      : 'border-gray-200 bg-white text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    className="h-3.5 w-3.5 accent-blue-600"
                    checked={checked}
                    onChange={() => toggleLogGroup(group)}
                  />
                  {groupLabel(group)}
                </label>
              );
            })}
          </div>
          {logStatus === 'loading' ? (
            <LogSkeleton />
          ) : logStatus === 'error' ? (
            <div className="rounded-2xl border border-dashed border-red-100 bg-red-50/40 px-4 py-8 text-center text-sm font-semibold text-red-500">
              Не удалось загрузить живой лог
            </div>
          ) : (
            <ul className="max-h-[min(22rem,55vh)] space-y-4 overflow-y-auto pr-1">
              {filteredLogItems.length === 0 ? (
                <li className="text-sm text-gray-500">Нет событий по выбранным группам логов</li>
              ) : (
                filteredLogItems.map((item, idx) => (
                  <li key={`${item.at}-${idx}`} className="flex gap-3 text-sm">
                    <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${logDotClass(item.status, item.group)}`} />
                    <div className="min-w-0">
                      <p
                        className="font-medium text-gray-800"
                        title={item.description || item.logdescription || logLine(item)}
                      >
                        {logLine(item)}
                      </p>
                      <p className="text-xs text-gray-400">
                        <span className="mr-2 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-gray-500">
                          {groupLabel(item.group || 'post')}
                        </span>
                        {item.at
                          ? new Date(item.at).toLocaleTimeString('ru-RU', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </p>
                    </div>
                  </li>
                ))
              )}
            </ul>
          )}
          <button type="button" className="mt-4 w-full rounded-2xl bg-blue-50 py-3 text-sm font-bold text-blue-600 transition-colors hover:bg-blue-100" onClick={openHistoryModal}>
            Смотреть все события
          </button>
        </div>
      </div>

      {showLogModal ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-gray-900/60 p-6 backdrop-blur-md"
          onClick={closeHistoryModal}
          role="presentation"
        >
          <div
            className="flex h-[85vh] w-full max-w-5xl flex-col overflow-hidden rounded-[40px] bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="history-modal-title"
          >
            <div className="flex items-center justify-between border-b border-gray-100 bg-white p-8">
              <div className="flex items-center gap-4">
                <div className="rounded-2xl bg-blue-600 p-3 text-white shadow-lg shadow-blue-100">
                  <Activity size={24} />
                </div>
                <div>
                  <h3 id="history-modal-title" className="text-2xl font-black tracking-tight text-gray-800">Полная история событий</h3>
                  <p className="text-sm font-medium text-gray-500">Мониторинг процессов за последние {HISTORY_MODAL_HOURS} ч (UTC)</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-xl bg-gray-50 px-4 py-2 text-sm font-bold text-gray-600 transition-all hover:bg-gray-100"
                  onClick={() => downloadHistoryLog(historyDisplayItems)}
                >
                  <Download size={16} /> .LOG
                </button>
                <button
                  type="button"
                  className="rounded-2xl p-3 text-gray-400 transition-all hover:bg-red-50 hover:text-red-500"
                  onClick={closeHistoryModal}
                  aria-label="Закрыть"
                >
                  <X size={24} />
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 overflow-x-auto border-b border-gray-100 bg-gray-50 px-8 py-4">
              <div className="relative max-w-md min-w-[200px] flex-1">
                <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="search"
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                  placeholder="Поиск по тексту или ID..."
                  className="w-full rounded-2xl border border-gray-200 bg-white py-2.5 pl-11 pr-4 text-sm font-medium outline-none focus:border-blue-300 focus:ring-4 focus:ring-blue-100"
                />
              </div>
              <div className="mx-2 hidden h-6 w-px bg-gray-200 sm:block" />
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-xs font-bold text-gray-500">
                  <Filter size={14} /> Группы
                </span>
                {logGroupsAvailable.map((group) => {
                  const checked = historySelectedGroups.includes(group);
                  return (
                    <label
                      key={`hist-${group}`}
                      className={`inline-flex cursor-pointer items-center gap-1.5 rounded-xl border px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                        checked ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-gray-200 bg-white text-gray-500 hover:bg-white'
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="h-3.5 w-3.5 accent-blue-600"
                        checked={checked}
                        onChange={() => toggleHistoryModalGroup(group)}
                      />
                      {groupLabel(group)}
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="flex gap-3 overflow-x-auto border-b border-gray-100 bg-gray-50/80 px-8 py-3">
              {[
                { id: 'all', label: 'Все типы' },
                { id: 'success', label: 'Успех' },
                { id: 'system', label: 'Система / info' },
                { id: 'errors', label: 'Ошибки' },
              ].map((btn) => (
                <button
                  key={btn.id}
                  type="button"
                  onClick={() => setHistoryQuickFilter(btn.id)}
                  className={`whitespace-nowrap rounded-xl border px-4 py-2 text-sm font-bold transition-all ${
                    historyQuickFilter === btn.id
                      ? btn.id === 'success'
                        ? 'border-green-200 bg-green-50 text-green-700'
                        : btn.id === 'errors'
                          ? 'border-red-200 bg-red-50 text-red-700'
                          : btn.id === 'system'
                            ? 'border-blue-200 bg-blue-50 text-blue-700'
                            : 'border-gray-300 bg-white text-gray-800 shadow-sm'
                      : 'border-transparent bg-white/80 text-gray-600 hover:border-gray-200 hover:bg-white'
                  }`}
                >
                  {btn.label}
                </button>
              ))}
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto p-8 font-mono text-xs">
              {historyStatus === 'loading' && historyItems.length === 0 ? (
                <div className="flex items-center justify-center py-20 text-sm font-semibold text-gray-400">Загрузка истории…</div>
              ) : historyStatus === 'error' && historyItems.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-red-100 bg-red-50/40 px-4 py-12 text-center text-sm font-semibold text-red-500">
                  Не удалось загрузить историю событий
                </div>
              ) : historyDisplayItems.length === 0 ? (
                <div className="py-16 text-center text-sm font-medium text-gray-400">Нет событий по текущим фильтрам</div>
              ) : (
                historyDisplayItems.map((item, idx) => {
                  const badgeType = getHistoryBadgeType(item);
                  const tip = item.description || item.logdescription || logLine(item);
                  return (
                    <div
                      key={`${item.at}-${historyEventId(item)}-${idx}`}
                      className="group flex gap-4 rounded-2xl border border-transparent p-4 transition-all hover:border-gray-100 hover:bg-gray-50 sm:gap-6"
                      title={tip}
                    >
                      <div className="w-[4.5rem] shrink-0 font-bold text-gray-400">{formatHistoryTime(item.at)}</div>
                      <div
                        className={`w-24 shrink-0 rounded-lg px-2 py-0.5 text-center text-[10px] font-black uppercase tracking-tighter ${historyBadgeClass(badgeType)}`}
                      >
                        {historyEventId(item)}
                      </div>
                      <div className="min-w-0 flex-1 font-semibold text-gray-700 transition-colors group-hover:text-gray-900">
                        {logLine(item)}
                      </div>
                      <div className="hidden w-28 shrink-0 truncate text-right text-[10px] font-bold uppercase text-gray-400 sm:block">
                        {historyTargetLabel(item)}
                      </div>
                      <div className="hidden w-6 shrink-0 justify-end opacity-0 transition-opacity group-hover:opacity-100 sm:flex">
                        <ChevronRight size={14} className="text-gray-300" />
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 border-t border-gray-100 bg-white px-10 py-6 text-[10px] font-black uppercase tracking-widest text-gray-400">
              <div className="flex flex-wrap gap-6">
                <span>
                  Показано: {historyDisplayItems.length}
                  {historyItems.length !== historyDisplayItems.length ? ` / ${historyItems.length} загружено` : ''}
                </span>
                <span className="text-red-400">Ошибок в выборке: {historyErrorCount}</span>
              </div>
              <div className="text-right">
                Автообновление: каждые 5 сек
                {historyLastRefresh ? (
                  <span className="mt-1 block font-semibold normal-case text-gray-500">
                    Обновлено: {historyLastRefresh.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
