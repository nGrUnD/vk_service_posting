import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { useOutletContext } from 'react-router-dom';

import api from '../api/axios';
import {
  PARSE_STATUS_FILTER_OPTIONS,
  getAccountCurl,
  matchesParseStatusFilter,
} from '../utils/accountFilters';

function getStatusTone(status) {
  if (status === 'success') return 'success';
  if (status === 'failure') return 'danger';
  if (status === 'pending' || status === 'in_progress') return 'warning';
  return 'neutral';
}

function getStatusLabel(status) {
  return status ? status.replaceAll('_', ' ') : 'unknown';
}

export default function AccountsPage() {
  const { user } = useOutletContext();
  const [messageApi, contextHolder] = message.useMessage();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [collectingCurlId, setCollectingCurlId] = useState(null);

  const loadAccounts = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true);
    }
    try {
      const { data } = await api.get(`/users/${user.id}/vk_accounts/all`);
      setAccounts(Array.isArray(data) ? data : []);
    } catch {
      messageApi.error('Не удалось загрузить аккаунты');
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [messageApi, user.id]);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const filteredAccounts = useMemo(() => {
    const query = search.trim().toLowerCase();

    return accounts.filter((account) => {
      const haystack = [
        account.name,
        account.second_name,
        account.login,
        account.vk_account_id,
        account.account_type,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      const matchesSearch = !query || haystack.includes(query);
      const matchesType = typeFilter === 'all' || account.account_type === typeFilter;
      const matchesStatus = matchesParseStatusFilter(statusFilter, account.parse_status);
      return matchesSearch && matchesType && matchesStatus;
    });
  }, [accounts, search, typeFilter, statusFilter]);

  const copyCurl = (account) => {
    const curl = getAccountCurl(account);
    if (!curl) return;
    navigator.clipboard.writeText(curl).then(
      () => messageApi.success('cURL скопирован в буфер'),
      () => messageApi.error('Не удалось скопировать'),
    );
  };

  const collectCurl = async (accountId) => {
    setCollectingCurlId(accountId);
    try {
      const { data } = await api.post(`/users/${user.id}/vk_accounts/${accountId}/collect_curl`);
      if (data?.task_id) {
        messageApi.success('Сбор cURL запущен');
      } else {
        messageApi.info(data?.detail || 'cURL уже сохранен');
      }
      await loadAccounts(true);
    } catch (error) {
      messageApi.error(error?.response?.data?.detail || 'Не удалось запустить сбор cURL');
    } finally {
      setCollectingCurlId(null);
    }
  };

  const availableTypes = useMemo(
    () => ['all', ...new Set(accounts.map((account) => account.account_type).filter(Boolean))],
    [accounts],
  );

  return (
    <div className="space-y-6">
      {contextHolder}

      <section className="v2-card rounded-[28px] p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <h3 className="m-0 text-xl font-semibold text-white">Accounts</h3>
            <p className="v2-muted mt-2 text-sm">
              Новый экран списка аккаунтов использует существующий endpoint, но уже не зависит от вкладочного UI старого frontend.
            </p>
          </div>

          <div className="grid w-full gap-3 md:grid-cols-[minmax(0,1fr)_180px_180px_auto] xl:max-w-4xl">
            <input
              className="v2-input"
              value={search}
              placeholder="Поиск по имени, логину, ID"
              onChange={(event) => setSearch(event.target.value)}
            />

            <select
              className="v2-select"
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
            >
              {availableTypes.map((item) => (
                <option key={item} value={item}>
                  {item === 'all' ? 'Все типы' : item}
                </option>
              ))}
            </select>

            <select
              className="v2-select"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              {PARSE_STATUS_FILTER_OPTIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>

            <button type="button" className="v2-button v2-button-secondary" onClick={() => loadAccounts(true)}>
              Обновить
            </button>
          </div>
        </div>
      </section>

      <section className="v2-card rounded-[28px] p-0">
        <div className="v2-table-wrap">
          <table className="v2-table">
            <thead>
              <tr>
                <th>Аккаунт</th>
                <th>VK ID</th>
                <th>Логин</th>
                <th>Тип</th>
                <th>Статус</th>
                <th>Прокси</th>
                <th>Паблики</th>
                <th>Cookies</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {filteredAccounts.map((account) => (
                <tr key={account.id}>
                  <td>
                    <div className="flex min-w-[220px] items-center gap-3">
                      <img
                        src={account.avatar_url || 'https://placehold.co/48x48/0f172a/e2e8f0?text=VK'}
                        alt={account.name || 'VK'}
                        className="h-12 w-12 rounded-2xl object-cover"
                      />
                      <div>
                        <div className="font-semibold text-white">
                          {[account.name, account.second_name].filter(Boolean).join(' ') || 'Без имени'}
                        </div>
                        <a
                          href={account.vk_account_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sm text-indigo-300"
                        >
                          Открыть VK
                        </a>
                      </div>
                    </div>
                  </td>
                  <td>{account.vk_account_id}</td>
                  <td>{account.login || '—'}</td>
                  <td>
                    <span className="v2-chip" data-tone="info">
                      {account.account_type || 'unknown'}
                    </span>
                  </td>
                  <td>
                    <span className="v2-chip" data-tone={getStatusTone(account.parse_status)}>
                      {getStatusLabel(account.parse_status)}
                    </span>
                  </td>
                  <td>{account.proxy_id ?? '—'}</td>
                  <td>{account.groups_count ?? 0}</td>
                  <td>{account.cookies ? 'Есть' : '—'}</td>
                  <td>
                    {getAccountCurl(account) ? (
                      <button
                        type="button"
                        className="v2-button v2-button-secondary text-xs"
                        onClick={() => copyCurl(account)}
                      >
                        Скопировать курл
                      </button>
                    ) : account.parse_status === 'success' ? (
                      <button
                        type="button"
                        className="v2-button v2-button-secondary text-xs"
                        disabled={collectingCurlId === account.id}
                        onClick={() => collectCurl(account.id)}
                      >
                        {collectingCurlId === account.id ? 'Сбор...' : 'Собрать курл'}
                      </button>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}

              {!loading && !filteredAccounts.length && (
                <tr>
                  <td colSpan="9">
                    <div className="px-4 py-10 text-center text-sm text-slate-400">
                      По текущим фильтрам аккаунты не найдены.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {loading && (
          <div className="border-t border-slate-800 px-6 py-4 text-sm text-slate-400">
            Загрузка аккаунтов...
          </div>
        )}
      </section>
    </div>
  );
}
