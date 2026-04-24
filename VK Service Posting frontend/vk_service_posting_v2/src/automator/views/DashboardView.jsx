import React, { useCallback, useEffect, useState } from 'react';
import { message } from 'antd';
import { Activity, AlertCircle, Database, TrendingUp } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

export default function DashboardView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [summary, setSummary] = useState(null);
  const [clipsTotal, setClipsTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, clipsRes] = await Promise.all([
        api.get(`/users/${user.id}/vk_accounts/v2_summary`),
        api.get(`/users/${user.id}/clip_list/get_all`),
      ]);
      setSummary(sumRes.data);
      const lists = Array.isArray(clipsRes.data) ? clipsRes.data : [];
      setClipsTotal(lists.reduce((acc, row) => acc + (Number(row.count) || 0), 0));
    } catch {
      messageApi.error('Не удалось загрузить сводку');
    } finally {
      setLoading(false);
    }
  }, [messageApi, user.id]);

  useEffect(() => {
    load();
  }, [load]);

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

      <div className="rounded-3xl border border-gray-100 bg-white p-8 shadow-sm">
        <h3 className="mb-2 text-lg font-bold text-gray-800">Детализация</h3>
        <p className="mb-6 text-sm font-medium text-gray-500">
          По типам аккаунтов: {summary?.by_type ? JSON.stringify(summary.by_type) : '—'}
        </p>
        <p className="text-sm text-gray-500">
          Графики из макета оставлены визуально упрощёнными: при необходимости подключим реальные метрики постинга отдельной ручкой.
        </p>
        <div className="mt-6 flex h-40 items-end justify-between gap-1 px-2 opacity-80">
          {[40, 70, 45, 90, 65, 80, 95, 70, 50, 40, 60, 85, 30, 45, 70, 90, 100, 80, 60, 40, 50, 75, 90, 85].map((h, i) => (
            <div
              key={i}
              className="flex-1 cursor-pointer rounded-t-sm bg-blue-100 transition-all hover:bg-blue-500"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
