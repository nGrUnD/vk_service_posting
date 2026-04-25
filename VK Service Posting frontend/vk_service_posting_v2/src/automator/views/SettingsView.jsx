import React, { useCallback, useEffect, useState } from 'react';
import { message } from 'antd';
import { Bell, FileVideo, Key, Lock, ShieldCheck, Settings } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

function getV1Url() {
  return import.meta.env.VITE_V1_URL || `${window.location.protocol}//${window.location.hostname}/`;
}

export default function SettingsView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [activeSubTab, setActiveSubTab] = useState('general');
  const [categories, setCategories] = useState([]);
  const [clipLists, setClipLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    name: '',
    description: '',
    repost_enabled: false,
    daily_limit: 0,
    hourly_limit: 0,
    clip_list_id: null,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [catRes, clipRes] = await Promise.all([
        api.get(`/users/${user.id}/categories/get_all`),
        api.get(`/users/${user.id}/clip_list/get_all`),
      ]);
      setCategories(Array.isArray(catRes.data) ? catRes.data : []);
      setClipLists(Array.isArray(clipRes.data) ? clipRes.data : []);
    } catch {
      messageApi.error('Не удалось загрузить настройки');
    } finally {
      setLoading(false);
    }
  }, [messageApi, user.id]);

  useEffect(() => {
    load();
  }, [load]);

  const openEdit = (cat) => {
    setEditing(cat);
    setForm({
      name: cat.name,
      description: cat.description ?? '',
      repost_enabled: Boolean(cat.repost_enabled),
      daily_limit: cat.daily_limit ?? 0,
      hourly_limit: cat.hourly_limit ?? 0,
      clip_list_id: cat.clip_list_id ?? null,
    });
  };

  const saveCategory = async () => {
    if (!editing) return;
    try {
      await api.put(`/users/${user.id}/categories/edit/${editing.id}`, {
        name: editing.name,
        ...form,
        is_active: true,
        repost_enabled: form.repost_enabled,
      });
      messageApi.success('Сохранено');
      setEditing(null);
      load();
    } catch {
      messageApi.error('Ошибка сохранения');
    }
  };

  const nav = [
    { id: 'general', label: 'Категории и лимиты', icon: Settings },
    { id: 'safety', label: 'Безопасность', icon: ShieldCheck },
    { id: 'video', label: 'Уникализация видео', icon: FileVideo },
    { id: 'notif', label: 'Уведомления', icon: Bell },
    { id: 'api', label: 'API & Ключи', icon: Key },
  ];

  return (
    <div className="flex animate-in fade-in flex-col gap-8 duration-300 lg:flex-row">
      {contextHolder}

      <div className="w-full shrink-0 space-y-2 lg:w-64">
        {nav.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setActiveSubTab(item.id)}
            className={`flex w-full items-center space-x-3 rounded-2xl px-5 py-4 text-sm font-bold transition-all ${
              activeSubTab === item.id
                ? 'border border-gray-100 bg-white text-blue-600 shadow-md shadow-gray-200/50'
                : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </button>
        ))}
      </div>

      <div className="min-h-[600px] flex-1 rounded-3xl border border-gray-100 bg-white p-10 shadow-sm">
        {activeSubTab === 'general' && (
          <div className="space-y-8">
            <div>
              <h3 className="mb-2 text-xl font-black text-gray-800">Категории (API V1)</h3>
              <p className="mb-6 text-sm font-medium text-gray-500">
                Редактирование лимитов и привязки списка клипов — те же ручки, что в первой версии.
              </p>
              <button
                type="button"
                onClick={() => window.open(`${getV1Url().replace(/\/$/, '')}/dashboard/category-settings`, '_blank')}
                className="mb-6 rounded-2xl border border-gray-200 px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-50"
              >
                Полный экран в V1
              </button>
            </div>

            {loading ? (
              <p className="text-gray-500">Загрузка…</p>
            ) : (
              <div className="space-y-3">
                {categories.map((c) => (
                  <div
                    key={c.id}
                    className="flex flex-col justify-between gap-3 rounded-2xl border border-gray-100 bg-gray-50 p-4 sm:flex-row sm:items-center"
                  >
                    <div>
                      <p className="font-bold text-gray-900">{c.name}</p>
                      <p className="text-xs text-gray-500">
                        час: {c.hourly_limit} • сутки: {c.daily_limit} • репост: {c.repost_enabled ? 'да' : 'нет'}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => openEdit(c)}
                      className="rounded-xl bg-white px-4 py-2 text-sm font-bold text-blue-600 shadow-sm ring-1 ring-gray-100 hover:bg-blue-50"
                    >
                      Изменить
                    </button>
                  </div>
                ))}
              </div>
            )}

            {editing && (
              <div className="fixed inset-0 z-40 flex items-center justify-center bg-gray-900/30 p-4">
                <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white p-8 shadow-2xl">
                  <h4 className="mb-4 text-lg font-black">Категория: {editing.name}</h4>
                  <div className="space-y-4">
                    <label className="block text-xs font-bold text-gray-500">
                      Описание
                      <textarea
                        className="mt-1 w-full rounded-2xl border border-gray-100 bg-gray-50 p-3 text-sm"
                        value={form.description}
                        onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                      />
                    </label>
                    <label className="block text-xs font-bold text-gray-500">
                      Клипов в час
                      <input
                        type="number"
                        className="mt-1 w-full rounded-2xl border border-gray-100 bg-gray-50 p-3 text-sm font-bold"
                        value={form.hourly_limit}
                        onChange={(e) => setForm((f) => ({ ...f, hourly_limit: Number(e.target.value) }))}
                      />
                    </label>
                    <label className="block text-xs font-bold text-gray-500">
                      Клипов в сутки
                      <input
                        type="number"
                        className="mt-1 w-full rounded-2xl border border-gray-100 bg-gray-50 p-3 text-sm font-bold"
                        value={form.daily_limit}
                        onChange={(e) => setForm((f) => ({ ...f, daily_limit: Number(e.target.value) }))}
                      />
                    </label>
                    <label className="flex items-center gap-2 text-sm font-bold text-gray-700">
                      <input
                        type="checkbox"
                        checked={form.repost_enabled}
                        onChange={(e) => setForm((f) => ({ ...f, repost_enabled: e.target.checked }))}
                      />
                      Репосты
                    </label>
                    <label className="block text-xs font-bold text-gray-500">
                      Список клипов
                      <select
                        className="mt-1 w-full rounded-2xl border border-gray-100 bg-gray-50 p-3 text-sm font-bold"
                        value={form.clip_list_id ?? ''}
                        onChange={(e) =>
                          setForm((f) => ({
                            ...f,
                            clip_list_id: e.target.value ? Number(e.target.value) : null,
                          }))
                        }
                      >
                        <option value="">—</option>
                        {clipLists.map((cl) => (
                          <option key={cl.id} value={cl.id}>
                            {cl.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <div className="mt-6 flex gap-3">
                    <button
                      type="button"
                      onClick={() => setEditing(null)}
                      className="flex-1 rounded-2xl border-2 border-gray-100 py-3 font-bold text-gray-700 hover:bg-gray-50"
                    >
                      Отмена
                    </button>
                    <button
                      type="button"
                      onClick={saveCategory}
                      className="flex-1 rounded-2xl bg-blue-600 py-3 font-bold text-white shadow-lg hover:bg-blue-700"
                    >
                      Сохранить
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {['notif', 'safety', 'video', 'api'].includes(activeSubTab) && (
          <div className="flex h-full flex-col items-center justify-center py-20 text-center">
            <div className="mb-6 rounded-full bg-gray-50 p-6">
              <Lock size={48} className="text-gray-300" />
            </div>
            <h4 className="mb-2 text-xl font-black text-gray-800">Раздел из макета</h4>
            <p className="max-w-md text-sm font-medium text-gray-500">
              Здесь можно подключить отдельные backend-ручки под V2. Сейчас это заглушка, как в вашем макете.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
