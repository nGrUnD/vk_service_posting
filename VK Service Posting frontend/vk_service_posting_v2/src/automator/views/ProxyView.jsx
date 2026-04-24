import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { AlertCircle, ShieldCheck, Trash2 } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

function parseProxyInput(value) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function ProxyView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [inputValue, setInputValue] = useState('');
  const [proxies, setProxies] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(false);
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

  const selectedProxyValues = useMemo(
    () => proxies.filter((p) => selectedIds.includes(p.id)).map((p) => p.http),
    [proxies, selectedIds],
  );

  const toggle = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

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
    } catch {
      messageApi.error('Ошибка добавления');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (!selectedProxyValues.length) {
      messageApi.info('Выберите прокси');
      return;
    }
    setLoading(true);
    try {
      await api.delete(`/proxy/${user.id}/delete_list`, { data: { proxys: selectedProxyValues } });
      setSelectedIds([]);
      messageApi.success('Удалено');
      await loadProxies();
    } catch {
      messageApi.error('Ошибка удаления');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl animate-in fade-in duration-300">
      {contextHolder}
      <div className="rounded-3xl border border-gray-100 bg-white p-10 shadow-sm">
        <div className="flex flex-col gap-12 lg:flex-row">
          <div className="flex-1">
            <div className="mb-6 inline-flex rounded-2xl bg-indigo-50 p-4 text-indigo-600 shadow-inner">
              <ShieldCheck size={32} />
            </div>
            <h3 className="mb-4 text-2xl font-black text-gray-800">Прокси (как в V1)</h3>
            <p className="mb-8 text-sm font-medium leading-relaxed text-gray-500">
              Те же endpoint&apos;ы: <code className="rounded bg-gray-100 px-1">/proxy/&#123;user_id&#125;/add</code> и{' '}
              <code className="rounded bg-gray-100 px-1">delete_list</code>.
            </p>
            <label className="mb-3 ml-1 block text-xs font-black uppercase tracking-widest text-gray-400">
              Список (один на строку)
            </label>
            <textarea
              className="h-64 w-full resize-none rounded-3xl border border-gray-100 bg-gray-50 p-6 font-mono text-sm leading-relaxed outline-none transition-all focus:ring-4 focus:ring-indigo-50"
              placeholder={'http://login:pass@ip:port'}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
            <button
              type="button"
              disabled={loading}
              onClick={handleAdd}
              className="mt-6 w-full rounded-2xl bg-indigo-600 py-4 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition-all hover:bg-indigo-700 disabled:opacity-60"
            >
              {loading ? '…' : 'Добавить прокси'}
            </button>
          </div>

          <div className="flex w-full flex-col gap-6 lg:w-96">
            <div className="flex flex-1 flex-col rounded-3xl border border-gray-100 bg-gray-50 p-8">
              <div className="mb-6 flex items-center justify-between">
                <h4 className="text-sm font-black uppercase tracking-wider text-gray-800">Загруженные</h4>
                <span className="rounded-lg bg-green-500 px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-white shadow-sm">
                  {refreshing ? '…' : `${proxies.length} шт.`}
                </span>
              </div>
              <div className="max-h-80 space-y-4 overflow-y-auto">
                {proxies.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between rounded-2xl border border-gray-100 bg-white p-4 shadow-sm transition-all group-hover:border-gray-200"
                  >
                    <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-3">
                      <input type="checkbox" checked={selectedIds.includes(p.id)} onChange={() => toggle(p.id)} />
                      <div className="min-w-0">
                        <p className="break-all font-mono text-xs font-bold text-gray-700">{p.http}</p>
                        <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-gray-400">id {p.id}</p>
                      </div>
                    </label>
                  </div>
                ))}
                {!refreshing && !proxies.length && (
                  <p className="text-center text-sm text-gray-400">Прокси нет</p>
                )}
              </div>
              <button
                type="button"
                disabled={loading}
                onClick={handleDeleteSelected}
                className="mt-4 w-full rounded-2xl border border-red-100 py-3 text-sm font-bold text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                Удалить выбранные
              </button>
              <button
                type="button"
                onClick={loadProxies}
                className="mt-2 w-full rounded-2xl py-2 text-xs font-bold text-gray-500 hover:bg-gray-100"
              >
                Обновить список
              </button>
            </div>

            <div className="rounded-3xl border border-blue-100 bg-blue-50/50 p-6">
              <div className="flex items-start gap-3">
                <AlertCircle size={20} className="mt-0.5 shrink-0 text-blue-500" />
                <p className="text-xs font-medium leading-relaxed text-blue-800">
                  Удаление через список строк совпадает с логикой V1: передаются значения поля <strong>http</strong>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
