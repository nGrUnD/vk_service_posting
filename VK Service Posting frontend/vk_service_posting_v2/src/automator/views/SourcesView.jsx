import React, { useCallback, useEffect, useState } from 'react';
import { message } from 'antd';
import { Database, Download, Loader2, Plus, Settings } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

const PALETTE = [
  { color: 'bg-orange-50 text-orange-600', border: 'border-orange-100', dot: 'bg-orange-400' },
  { color: 'bg-pink-50 text-pink-600', border: 'border-pink-100', dot: 'bg-pink-400' },
  { color: 'bg-blue-50 text-blue-600', border: 'border-blue-100', dot: 'bg-blue-400' },
  { color: 'bg-emerald-50 text-emerald-600', border: 'border-emerald-100', dot: 'bg-emerald-400' },
  { color: 'bg-purple-50 text-purple-600', border: 'border-purple-100', dot: 'bg-purple-400' },
];

function getV1Url() {
  return import.meta.env.VITE_V1_URL || `${window.location.protocol}//${window.location.hostname}/`;
}

export default function SourcesView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [lists, setLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [downloadingId, setDownloadingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/users/${user.id}/clip_list/get_all`);
      setLists(Array.isArray(data) ? data : []);
    } catch {
      messageApi.error('Не удалось загрузить списки клипов');
    } finally {
      setLoading(false);
    }
  }, [messageApi, user.id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDownloadList = async (cat) => {
    const count = Number(cat.count || 0);
    if (!count) {
      messageApi.warning('В списке нет клипов для скачивания');
      return;
    }
    setDownloadingId(cat.id);
    try {
      const response = await api.get(`/users/${user.id}/clip_list/get/${cat.id}/download`, {
        responseType: 'blob',
        timeout: 0,
      });
      const failed = response.headers?.['x-export-failed'];
      const ok = response.headers?.['x-export-ok'];
      const safeName = (cat.name || `list_${cat.id}`).replace(/[^\w\-.]+/g, '_').slice(0, 80);
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${safeName}_clips.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      if (failed && Number(failed) > 0) {
        messageApi.warning(
          `Архив скачан. Успешно: ${ok ?? '?'}. Не скачалось: ${failed} (см. manifest.csv в архиве).`,
        );
      } else {
        messageApi.success('Архив скачан на ваш компьютер');
      }
    } catch (e) {
      const detail = e.response?.data;
      let text = 'Не удалось скачать клипы';
      if (detail instanceof Blob) {
        try {
          text = JSON.parse(await detail.text())?.detail || text;
        } catch {
          /* ignore */
        }
      } else if (detail?.detail) {
        text = typeof detail.detail === 'string' ? detail.detail : text;
      }
      messageApi.error(text);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) {
      messageApi.warning('Введите название списка');
      return;
    }
    try {
      await api.post(`/users/${user.id}/clip_list/add`, { name: newName.trim() });
      setNewName('');
      messageApi.success('Список создан');
      load();
    } catch {
      messageApi.error('Не удалось создать список');
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {contextHolder}

      <div className="flex flex-col justify-between gap-4 rounded-3xl border border-gray-100 bg-white p-6 shadow-sm sm:flex-row sm:items-center">
        <h3 className="ml-2 text-lg font-black text-gray-800">Управление базами клипов</h3>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Название нового списка"
            className="min-w-[200px] rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm font-bold outline-none focus:ring-4 focus:ring-blue-100"
          />
          <button
            type="button"
            onClick={handleCreate}
            className="flex items-center gap-2 rounded-2xl bg-gray-900 px-6 py-3 text-sm font-bold text-white shadow-lg transition-all hover:bg-black"
          >
            <Plus size={18} /> Создать список
          </button>
          <button
            type="button"
            onClick={() => window.open(`${getV1Url().replace(/\/$/, '')}/dashboard/connect-source-group`, '_blank')}
            className="rounded-2xl border border-gray-200 px-4 py-3 text-sm font-bold text-gray-700 hover:bg-gray-50"
          >
            Подключить паблики (V1)
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-center text-gray-500">Загрузка…</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {lists.map((cat, i) => {
            const pal = PALETTE[i % PALETTE.length];
            return (
              <div
                key={cat.id}
                className={`relative flex flex-col overflow-hidden rounded-3xl border ${pal.border} bg-white p-8 shadow-sm transition-all hover:shadow-xl`}
              >
                <div className="pointer-events-none absolute right-0 top-0 p-6 opacity-10 transition-opacity group-hover:opacity-100">
                  <Database size={64} className={pal.color.split(' ')[1]} />
                </div>
                <div className={`mb-6 inline-flex self-start rounded-xl px-3 py-1.5 text-[10px] font-black uppercase tracking-widest ${pal.color}`}>
                  Список #{cat.id}
                </div>
                <h4 className="mb-2 text-2xl font-black text-gray-800">{cat.name}</h4>
                <div className="mb-10 flex items-center gap-2 text-sm">
                  <div className={`h-2 w-2 animate-pulse rounded-full ${pal.dot}`} />
                  <span className="font-bold text-gray-500">
                    {Number(cat.count || 0).toLocaleString('ru-RU')}{' '}
                    <span className="font-medium text-gray-400">клипов</span>
                  </span>
                </div>
                <div className="relative z-10 mt-auto flex gap-3">
                  <button
                    type="button"
                    disabled
                    className="flex-1 cursor-not-allowed rounded-2xl bg-gray-100 py-3.5 text-xs font-bold text-gray-400"
                    title="Парсинг источников — через V1"
                  >
                    Пополнить
                  </button>
                  <button
                    type="button"
                    disabled={!cat.count || downloadingId === cat.id}
                    onClick={() => void handleDownloadList(cat)}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-2xl border border-blue-200 bg-blue-50 py-3.5 text-xs font-bold text-blue-800 transition-all hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50"
                    title="Скачать все клипы списка ZIP-архивом на компьютер"
                  >
                    {downloadingId === cat.id ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Download size={16} />
                    )}
                    Скачать
                  </button>
                  <button
                    type="button"
                    onClick={() => window.open(`${getV1Url().replace(/\/$/, '')}/dashboard/connect-source-group`, '_blank')}
                    className="rounded-2xl border border-gray-100 bg-gray-50 p-3.5 text-gray-500 transition-all hover:bg-gray-100"
                    title="Настройка в V1"
                  >
                    <Settings size={18} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
