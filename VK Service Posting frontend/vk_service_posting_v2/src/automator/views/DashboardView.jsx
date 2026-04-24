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
  const g = item.group_name || '—';
  if (item.status === 'success') return `Опубликован клип в «${g}»`;
  if (item.status === 'starting') return `В очереди на публикацию в «${g}»`;
  return `Событие в «${g}» (${item.status})`;
}

function logDotClass(status) {
  if (status === 'success') return 'bg-green-500';
  if (status === 'starting') return 'bg-blue-500';
  return 'bg-red-500';
}

export default function DashboardView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [summary, setSummary] = useState(null);
  const [clipsTotal, setClipsTotal] = useState(0);
  const [buckets, setBuckets] = useState([]);
  const [logItems, setLogItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, clipsRes, actRes, logRes] = await Promise.allSettled([
        api.get(`/users/${user.id}/vk_accounts/v2_summary`),
        api.get(`/users/${user.id}/clip_list/get_all`),
        api.get(`/users/${user.id}/dashboard/v2/posting_activity`, { params: { hours: 24 } }),
        api.get(`/users/${user.id}/dashboard/v2/activity_log`, { params: { limit: 25 } }),
      ]);

      if (sumRes.status === 'fulfilled') {
        setSummary(sumRes.value.data);
      } else {
        setSummary(null);
      }

      if (clipsRes.status === 'fulfilled') {
        const lists = Array.isArray(clipsRes.value.data) ? clipsRes.value.data : [];
        setClipsTotal(lists.reduce((acc, row) => acc + (Number(row.count) || 0), 0));
      } else {
        setClipsTotal(0);
      }

      if (actRes.status === 'fulfilled') {
        setBuckets(Array.isArray(actRes.value.data?.buckets) ? actRes.value.data.buckets : []);
      } else {
        setBuckets([]);
      }

      if (logRes.status === 'fulfilled') {
        setLogItems(Array.isArray(logRes.value.data?.items) ? logRes.value.data.items : []);
      } else {
        setLogItems([]);
      }

      const failedCount = [sumRes, clipsRes, actRes, logRes].filter((res) => res.status === 'rejected').length;
      if (failedCount > 0) {
        messageApi.warning(`Часть данных не загрузилась (${failedCount}/4)`);
      }
    } catch {
      messageApi.error('Не удалось загрузить сводку');
    } finally {
      setLoading(false);
    }
  }, [messageApi, user.id]);

  useEffect(() => {
    load();
  }, [load]);

  const maxPosted = useMemo(() => {
    const m = Math.max(0, ...buckets.map((b) => Number(b.posted) || 0));
    return m > 0 ? m : 1;
  }, [buckets]);

  const stats = [
    {
      label: 'Аккаунтов ВК',
      value: summary?.total_accounts ?? '—',
      change: `${summary?.by_status?.success ?? 0} success`,
      icon: TrendingUp,
      color: 'text-green-600',
      bg: 'bg-green-50',
    },
    {
      label: 'Активных воркеров',
      value: summary?.workflow_count ?? '—',
      change: 'workerpost',
      icon: Activity,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Клипов в базах',
      value: clipsTotal.toLocaleString('ru-RU'),
      change: 'сумма по спискам',
      icon: Database,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
    },
    {
      label: 'Проблемы',
      value: (Number(summary?.by_status?.failure) || 0) + (Number(summary?.flooded) || 0),
      change: 'failure + flood',
      icon: AlertCircle,
      color: 'text-red-600',
      bg: 'bg-red-50',
    },
  ];

  if (loading) {
    return <p className="text-center font-medium text-gray-500">Загрузка…</p>;
  }

  return (
    <div className="space-y-8">
      {contextHolder}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="mb-4 flex items-start justify-between">
              <div className={`rounded-2xl p-3.5 ${stat.bg} ${stat.color}`}>
                <stat.icon size={24} />
              </div>
              <span className={`rounded-xl px-2.5 py-1.5 text-[11px] font-black uppercase tracking-wider ${stat.bg} ${stat.color}`}>
                {stat.change}
              </span>
            </div>
            <h4 className="mb-1 text-sm font-bold text-gray-500">{stat.label}</h4>
            <p className="text-3xl font-black text-gray-800">{stat.value}</p>
          </div>
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
        </div>

        <div className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <Activity className="text-blue-500" size={20} />
            <h3 className="text-lg font-bold text-gray-800">Живой лог</h3>
          </div>
          <ul className="max-h-[min(22rem,55vh)] space-y-4 overflow-y-auto pr-1">
            {logItems.length === 0 ? (
              <li className="text-sm text-gray-500">Пока нет записей расписания</li>
            ) : (
              logItems.map((item, idx) => (
                <li key={`${item.at}-${idx}`} className="flex gap-3 text-sm">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${logDotClass(item.status)}`} />
                  <div className="min-w-0">
                    <p className="font-medium text-gray-800">{logLine(item)}</p>
                    <p className="text-xs text-gray-400">
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
