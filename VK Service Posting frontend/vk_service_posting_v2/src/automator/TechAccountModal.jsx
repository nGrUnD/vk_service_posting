import React, { useCallback, useEffect, useRef, useState } from 'react';
import { message } from 'antd';
import { ExternalLink, RefreshCcw, X } from 'lucide-react';

import api from '../api/axios';

function useParseStatusPoll(userId, accountId, taskVersion) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    if (!userId || !accountId) {
      setStatus(null);
      return undefined;
    }

    let intervalId;
    const fetchStatus = async () => {
      try {
        const { data } = await api.get(`/users/${userId}/vk_accounts/${accountId}/status`);
        setStatus(data.status);
        if (data.status === 'success' || data.status === 'failure') {
          clearInterval(intervalId);
        }
      } catch {
        clearInterval(intervalId);
      }
    };

    setStatus(null);
    fetchStatus();
    intervalId = setInterval(fetchStatus, 2000);
    return () => clearInterval(intervalId);
  }, [userId, accountId, taskVersion]);

  return status;
}

export default function TechAccountModal({ open, onClose, userId }) {
  const [messageApi, contextHolder] = message.useMessage();
  const [mainAccount, setMainAccount] = useState(null);
  const [loadingAccount, setLoadingAccount] = useState(false);
  const [curlInput, setCurlInput] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [taskVersion, setTaskVersion] = useState(0);
  const prevStatusRef = useRef(null);

  useEffect(() => {
    prevStatusRef.current = null;
  }, [mainAccount?.id]);

  const loadMain = useCallback(async () => {
    setLoadingAccount(true);
    try {
      const { data } = await api.get(`/users/${userId}/vk_accounts/all`);
      const accounts = Array.isArray(data) ? data : [];
      const main = accounts.find((a) => a.account_type === 'main') || null;
      setMainAccount(main);
    } catch {
      messageApi.error('Не удалось загрузить главный аккаунт');
      setMainAccount(null);
    } finally {
      setLoadingAccount(false);
    }
  }, [messageApi, userId]);

  useEffect(() => {
    if (!open) {
      return;
    }
    loadMain();
  }, [open, loadMain]);

  const liveStatus = useParseStatusPoll(userId, mainAccount?.id, taskVersion);

  useEffect(() => {
    if (!mainAccount || liveStatus == null) {
      return;
    }
    if (liveStatus !== mainAccount.parse_status) {
      setMainAccount((prev) => (prev ? { ...prev, parse_status: liveStatus } : prev));
    }
    if (liveStatus === 'success' && prevStatusRef.current !== 'success') {
      api
        .get(`/users/${userId}/vk_accounts/${mainAccount.id}`)
        .then((res) => {
          setMainAccount(res.data);
          messageApi.success('VK аккаунт успешно обработан');
        })
        .catch(() => messageApi.error('Не удалось обновить данные аккаунта'));
    } else if (liveStatus === 'failure' && prevStatusRef.current !== 'failure') {
      messageApi.error('Не удалось обработать VK аккаунт');
    }
    prevStatusRef.current = liveStatus;
  }, [liveStatus, mainAccount, messageApi, userId]);

  const handleConnect = async () => {
    if (!curlInput.trim()) {
      messageApi.warning('Вставьте команду curl');
      return;
    }
    setConnecting(true);
    try {
      const { data } = await api.post(`/users/${userId}/vk_accounts/curl_main`, { curl: curlInput.trim() });
      setMainAccount(data);
      setCurlInput('');
      messageApi.info('Запущена обработка главного аккаунта…');
      setTaskVersion((v) => v + 1);
    } catch (e) {
      messageApi.error(e.response?.data?.detail || 'Ошибка при отправке curl');
    } finally {
      setConnecting(false);
    }
  };

  const handleRetry = async () => {
    if (!mainAccount) {
      messageApi.warning('Сначала подключите главный аккаунт');
      return;
    }
    setRetrying(true);
    try {
      await api.post(`/users/${userId}/vk_accounts/retry`);
      messageApi.info('Повторная обработка запущена');
      setMainAccount((prev) => (prev ? { ...prev, parse_status: 'pending' } : prev));
      setTaskVersion((v) => v + 1);
    } catch {
      messageApi.error('Не удалось запустить повторную обработку');
    } finally {
      setRetrying(false);
    }
  };

  if (!open) {
    return null;
  }

  const displayName = mainAccount
    ? `${mainAccount.name ?? ''} ${mainAccount.second_name ?? ''}`.trim() || 'Главный аккаунт'
    : 'Не подключён';
  const initials = displayName
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase() || 'VK';

  const statusLabel = mainAccount?.parse_status?.replaceAll('_', ' ') || '—';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 p-4 backdrop-blur-sm">
      {contextHolder}
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white shadow-2xl">
        <div className="flex items-start justify-between bg-blue-600 p-8 text-white">
          <div className="flex gap-5">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20 text-2xl font-black backdrop-blur-md">
              {initials}
            </div>
            <div>
              <h3 className="text-2xl font-black">{displayName}</h3>
              <p className="mt-1 font-medium text-blue-100">Главный технический аккаунт (как в V1)</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-lg border border-white/20 bg-white/10 px-2.5 py-1 text-[10px] font-bold tracking-wider">
                  {loadingAccount ? '…' : statusLabel}
                </span>
                {mainAccount?.vk_account_url && (
                  <a
                    href={mainAccount.vk_account_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded-lg border border-white/20 bg-white/10 px-2.5 py-1 text-[10px] font-bold tracking-wider text-white no-underline hover:bg-white/20"
                  >
                    VK <ExternalLink size={12} />
                  </a>
                )}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20"
            aria-label="Закрыть"
          >
            <X size={16} />
          </button>
        </div>

        <div className="space-y-6 p-8">
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5">
              <p className="mb-2 text-xs font-bold uppercase tracking-wider text-gray-400">Пабликов</p>
              <p className="text-2xl font-black text-gray-800">
                {mainAccount?.groups_count ?? '—'}{' '}
                <span className="text-sm font-medium text-gray-400">сообществ</span>
              </p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-5">
              <p className="mb-2 text-xs font-bold uppercase tracking-wider text-gray-400">ID в системе</p>
              <p className="text-2xl font-black text-gray-800">{mainAccount?.id ?? '—'}</p>
            </div>
          </div>

          <div>
            <label className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider text-gray-500">
              Новая команда cURL (сессия)
            </label>
            <p className="mb-2 text-xs text-gray-500">
              Сохранённый curl на сервере не отдаётся в открытом виде — вставьте свежую команду, как в первой версии интерфейса.
            </p>
            <textarea
              className="h-32 w-full resize-none rounded-2xl border border-gray-200 bg-gray-900 p-4 font-mono text-xs leading-relaxed text-green-400 outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="curl 'https://vk.com/...' -H 'cookie: ...'"
              value={curlInput}
              onChange={(e) => setCurlInput(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-3 pt-2 sm:flex-row">
            <button
              type="button"
              disabled={connecting}
              onClick={handleConnect}
              className="flex-1 rounded-2xl bg-blue-600 py-4 font-bold text-white shadow-lg shadow-blue-100 transition-all hover:bg-blue-700 disabled:opacity-60"
            >
              {connecting ? 'Отправка…' : 'Подключить / обновить сессию'}
            </button>
            <button
              type="button"
              disabled={retrying || !mainAccount}
              onClick={handleRetry}
              className="flex flex-1 items-center justify-center gap-2 rounded-2xl border-2 border-gray-100 py-4 font-bold text-gray-700 transition-all hover:border-gray-200 hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCcw size={18} />
              Повторить обработку
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
