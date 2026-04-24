import React, { useCallback, useEffect, useState } from 'react';
import { message } from 'antd';
import { ExternalLink, Plus, Settings, Trash2 } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

function getV1Url() {
  return import.meta.env.VITE_V1_URL || `${window.location.protocol}//${window.location.hostname}:5173/`;
}

export default function WorkflowView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(`/users/${user.id}/workerpost/all`);
      const tableData = (Array.isArray(response.data) ? response.data : []).map((item) => {
        const { workpost, vk_group, vk_account, category, clip_list } = item;
        return {
          id: workpost.id,
          groupName: vk_group?.name,
          groupUrl: vk_group?.vk_group_url,
          accountName: `${vk_account?.name ?? ''} ${vk_account?.second_name ?? ''}`.trim(),
          category: category?.name,
          hourly: category?.hourly_limit,
          active: workpost?.is_active,
          clipList: clip_list?.name,
        };
      });
      setRows(tableData);
    } catch {
      messageApi.error('Не удалось загрузить workerpost');
    } finally {
      setLoading(false);
    }
  }, [messageApi, user.id]);

  useEffect(() => {
    load();
  }, [load]);

  const activeCount = rows.filter((r) => r.active).length;

  return (
    <div className="space-y-6">
      {contextHolder}

      <section className="rounded-3xl border border-amber-100 bg-amber-50/80 p-6 shadow-sm">
        <h3 className="mb-2 text-lg font-black text-amber-900">Создание и редактирование воркеров</h3>
        <p className="text-sm font-medium text-amber-800">
          Полный конструктор (баннеры, категории, списки клипов) пока в первой версии интерфейса. Здесь отображается живой список
          воркерпостов из API.
        </p>
        <button
          type="button"
          onClick={() =>
            window.open(`${getV1Url().replace(/\/$/, '')}/dashboard/workflow-status`, '_blank')
          }
          className="mt-4 rounded-2xl bg-amber-600 px-5 py-3 text-sm font-bold text-white shadow-md hover:bg-amber-700"
        >
          Открыть V1: статус рабочего процесса
        </button>
      </section>

      <section className="rounded-3xl border border-gray-100 bg-white p-8 shadow-sm">
        <h3 className="mb-6 flex items-center gap-3 text-xl font-black text-gray-800">
          <div className="rounded-xl bg-blue-50 p-2 text-blue-600">
            <Plus size={20} />
          </div>
          Воркерпосты (данные с backend)
        </h3>
        {loading ? (
          <p className="text-gray-500">Загрузка…</p>
        ) : (
          <p className="text-sm text-gray-500">
            Активных: <span className="font-bold text-gray-800">{activeCount}</span> из {rows.length}
          </p>
        )}
      </section>

      <section className="overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 p-8">
          <h3 className="text-lg font-bold text-gray-800">Список воркеров</h3>
          <button
            type="button"
            onClick={load}
            className="rounded-xl border border-gray-200 px-4 py-2 text-xs font-bold text-gray-600 hover:bg-gray-50"
          >
            Обновить
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-gray-50 text-[10px] font-black uppercase tracking-widest text-gray-400">
              <tr>
                <th className="px-8 py-5">ID / Группа</th>
                <th className="px-6 py-5">Аккаунт</th>
                <th className="px-6 py-5">Категория</th>
                <th className="px-6 py-5">Посты (ч)</th>
                <th className="px-6 py-5">Статус</th>
                <th className="px-8 py-5 text-right">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              {rows.map((row) => (
                <tr key={row.id} className="group transition-colors hover:bg-gray-50/50">
                  <td className="px-8 py-5">
                    {row.groupUrl ? (
                      <a
                        href={row.groupUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 font-bold text-blue-600 hover:underline"
                      >
                        {row.groupName} <ExternalLink size={12} className="opacity-0 transition-opacity group-hover:opacity-100" />
                      </a>
                    ) : (
                      <span className="font-bold text-gray-800">{row.groupName}</span>
                    )}
                    <div className="mt-0.5 font-mono text-[10px] text-gray-400">#{row.id}</div>
                  </td>
                  <td className="px-6 py-5 font-semibold text-gray-800">{row.accountName || '—'}</td>
                  <td className="px-6 py-5">
                    <span className="rounded-lg bg-gray-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-gray-500">
                      {row.category || '—'}
                    </span>
                  </td>
                  <td className="px-6 py-5 font-mono font-bold text-gray-600">{row.hourly ?? '—'}</td>
                  <td className="px-6 py-5">
                    {row.active ? (
                      <span className="flex items-center gap-2 text-xs font-bold text-green-600">
                        <span className="h-2 w-2 animate-pulse rounded-full bg-green-600" /> В работе
                      </span>
                    ) : (
                      <span className="flex items-center gap-2 text-xs font-bold text-amber-600">
                        <span className="h-2 w-2 rounded-full bg-amber-600" /> Выкл.
                      </span>
                    )}
                  </td>
                  <td className="px-8 py-5 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        title="В V1"
                        onClick={() => window.open(getV1Url(), '_blank')}
                        className="rounded-xl p-2.5 text-gray-400 transition-all hover:bg-blue-50 hover:text-blue-600"
                      >
                        <Settings size={18} />
                      </button>
                      <button type="button" disabled className="rounded-xl p-2.5 text-gray-300" title="Удаление через V1">
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && !rows.length && (
                <tr>
                  <td colSpan={6} className="px-8 py-12 text-center text-sm text-gray-500">
                    Нет воркерпостов. Создайте их в интерфейсе V1.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
