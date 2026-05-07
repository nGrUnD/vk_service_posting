import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { Activity, AlertCircle, Database, TrendingUp } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

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
  if (group === 'proxy') return 'bg-violet-500';
  if (group === 'worker') return 'bg-cyan-500';
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
  };
  return map[group] || group;
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
  const [messageApi, contextHolder] = message.useMessage();
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
      setLogGroupsAvailable(apiGroups);
      setSelectedLogGroups((prev) => {
        if (!Array.isArray(prev) || prev.length === 0) return apiGroups;
        const keep = prev.filter((g) => apiGroups.includes(g));
        return keep.length > 0 ? keep : apiGroups;
      });
      setLogStatus('success');
    } catch {
      if (!isCurrent()) return;
      setLogItems([]);
      setLogGroupsAvailable(['post', 'worker', 'account', 'group', 'clip', 'proxy', 'task']);
      setLogStatus('error');
    }
  }, [user.id]);

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
      value: (Number(summary?.by_status?.failure) || 0) + (Number(summary?.flooded) || 0),
      change: 'failure + flood',
      icon: AlertCircle,
      color: 'text-red-600',
      bg: 'bg-red-50',
      status: summaryStatus,
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-3xl border border-gray-100 bg-white p-8 shadow-sm lg:col-span-2">
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

        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
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
                      <p className="font-medium text-gray-800">{logLine(item)}</p>
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
          <button
            type="button"
            className="mt-4 w-full rounded-2xl bg-blue-50 py-3 text-sm font-bold text-blue-600 transition-colors hover:bg-blue-100"
            onClick={() => messageApi.info('Полный журнал событий появится в следующей версии')}
          >
            Смотреть все события
          </button>
        </div>
      </div>
    </div>
  );
}
