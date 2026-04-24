import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { useOutletContext } from 'react-router-dom';

import api from '../api/axios';

function parseProxyInput(value) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function ProxyPage() {
  const { user } = useOutletContext();
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
    () => proxies.filter((proxy) => selectedIds.includes(proxy.id)).map((proxy) => proxy.http),
    [proxies, selectedIds],
  );

  const toggleProxy = (proxyId) => {
    setSelectedIds((prev) =>
      prev.includes(proxyId)
        ? prev.filter((currentId) => currentId !== proxyId)
        : [...prev, proxyId],
    );
  };

  const handleAdd = async () => {
    const newProxies = parseProxyInput(inputValue);
    if (!newProxies.length) {
      messageApi.warning('Введите хотя бы один прокси');
      return;
    }

    setLoading(true);
    try {
      await api.post(`/proxy/${user.id}/add`, { proxys: newProxies });
      setInputValue('');
      messageApi.success('Прокси добавлены');
      await loadProxies();
    } catch {
      messageApi.error('Не удалось добавить прокси');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (!selectedProxyValues.length) {
      messageApi.info('Выберите прокси для удаления');
      return;
    }

    setLoading(true);
    try {
      await api.delete(`/proxy/${user.id}/delete_list`, {
        data: { proxys: selectedProxyValues },
      });
      setSelectedIds([]);
      messageApi.success('Выбранные прокси удалены');
      await loadProxies();
    } catch {
      messageApi.error('Не удалось удалить прокси');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {contextHolder}

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <article className="v2-card rounded-[28px] p-6">
          <h3 className="m-0 text-xl font-semibold text-white">Добавить прокси</h3>
          <p className="v2-muted mt-2 text-sm">
            `V2` уже подключен к текущим proxy-endpoint'ам, поэтому эту страницу можно дорабатывать отдельно от старого интерфейса.
          </p>

          <textarea
            className="v2-textarea mt-5 min-h-[320px]"
            value={inputValue}
            placeholder={'127.0.0.1:8080\nlogin:pass@host:port'}
            onChange={(event) => setInputValue(event.target.value)}
          />

          <div className="mt-4 flex justify-end">
            <button type="button" className="v2-button v2-button-primary" onClick={handleAdd} disabled={loading}>
              {loading ? 'Сохраняем...' : 'Добавить прокси'}
            </button>
          </div>
        </article>

        <article className="v2-card rounded-[28px] p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="m-0 text-xl font-semibold text-white">Загруженные прокси</h3>
              <p className="v2-muted mt-2 text-sm">
                Всего: {proxies.length}. Здесь уже можно встроить ваш новый список/таблицу из готового макета.
              </p>
            </div>

            <div className="flex gap-3">
              <button type="button" className="v2-button v2-button-secondary" onClick={loadProxies} disabled={refreshing}>
                {refreshing ? 'Обновляем...' : 'Обновить'}
              </button>
              <button type="button" className="v2-button v2-button-danger" onClick={handleDeleteSelected} disabled={loading}>
                Удалить выбранные
              </button>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {proxies.map((proxy) => (
              <label
                key={proxy.id}
                className="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-3"
              >
                <input
                  type="checkbox"
                  checked={selectedIds.includes(proxy.id)}
                  onChange={() => toggleProxy(proxy.id)}
                />
                <div className="min-w-0 flex-1">
                  <div className="break-all font-medium text-white">{proxy.http}</div>
                  <div className="mt-1 text-xs text-slate-500">ID: {proxy.id}</div>
                </div>
              </label>
            ))}

            {!refreshing && !proxies.length && (
              <div className="rounded-2xl border border-dashed border-slate-700 px-4 py-10 text-center text-sm text-slate-400">
                Пока нет загруженных прокси.
              </div>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
