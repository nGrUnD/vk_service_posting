import React, { useEffect, useMemo, useState } from 'react';
import { Spin, message } from 'antd';
import { Link, useOutletContext } from 'react-router-dom';

import api from '../api/axios';

function getStatusTone(status) {
  if (status === 'success') return 'success';
  if (status === 'failure') return 'danger';
  if (status === 'pending' || status === 'in_progress') return 'warning';
  return 'neutral';
}

function formatStatus(status) {
  if (!status) return 'Неизвестно';
  return status.replaceAll('_', ' ');
}

function buildFallbackSummary(accounts, proxyCount) {
  const byType = {};
  const byStatus = {};

  for (const account of accounts) {
    byType[account.account_type] = (byType[account.account_type] || 0) + 1;
    byStatus[account.parse_status] = (byStatus[account.parse_status] || 0) + 1;
  }

  return {
    total_accounts: accounts.length,
    with_proxy: accounts.filter((account) => account.proxy_id).length,
    with_cookies: accounts.filter((account) => account.cookies).length,
    flooded: accounts.filter((account) => account.flood_control).length,
    proxy_count: proxyCount,
    workflow_count: 0,
    by_type: byType,
    by_status: byStatus,
    recent_accounts: [...accounts]
      .sort((left, right) => right.id - left.id)
      .slice(0, 6),
  };
}

function SummaryCard({ title, value, accent, hint }) {
  return (
    <article className="v2-card rounded-[28px] p-5">
      <div className="text-sm font-medium text-slate-400">{title}</div>
      <div className={`mt-3 text-3xl font-semibold ${accent}`}>{value}</div>
      <div className="v2-muted mt-2 text-sm">{hint}</div>
    </article>
  );
}

export default function OverviewPage() {
  const { user } = useOutletContext();
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadOverview() {
      setLoading(true);
      try {
        const { data } = await api.get(`/users/${user.id}/vk_accounts/v2_summary`);
        if (isMounted) {
          setSummary(data);
        }
      } catch {
        try {
          const [accountsResponse, proxyResponse] = await Promise.all([
            api.get(`/users/${user.id}/vk_accounts/all`),
            api.get(`/proxy/${user.id}/get`),
          ]);
          if (isMounted) {
            setSummary(
              buildFallbackSummary(
                Array.isArray(accountsResponse.data) ? accountsResponse.data : [],
                Array.isArray(proxyResponse.data) ? proxyResponse.data.length : 0,
              ),
            );
            messageApi.info('V2 использует локально собранную сводку, пока backend summary недоступен.');
          }
        } catch {
          if (isMounted) {
            messageApi.error('Не удалось загрузить overview');
          }
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadOverview();
    return () => {
      isMounted = false;
    };
  }, [messageApi, user.id]);

  const typeItems = useMemo(
    () =>
      Object.entries(summary?.by_type || {})
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, value]) => ({ key, value })),
    [summary],
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        {contextHolder}
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {contextHolder}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <SummaryCard
          title="Всего аккаунтов"
          value={summary?.total_accounts ?? 0}
          accent="text-white"
          hint="Полный объем аккаунтов, доступных в новой версии интерфейса."
        />
        <SummaryCard
          title="Рабочие аккаунты"
          value={summary?.by_status?.success ?? 0}
          accent="text-emerald-300"
          hint="Аккаунты со статусом `success`."
        />
        <SummaryCard
          title="Прокси"
          value={summary?.proxy_count ?? 0}
          accent="text-sky-300"
          hint="Количество прокси, привязанных к пользователю."
        />
        <SummaryCard
          title="С cookie"
          value={summary?.with_cookies ?? 0}
          accent="text-violet-300"
          hint="Можно быстро увидеть, насколько заполнены данные для переиспользования."
        />
        <SummaryCard
          title="С proxy_id"
          value={summary?.with_proxy ?? 0}
          accent="text-amber-300"
          hint="Аккаунты, которым уже назначен прокси."
        />
        <SummaryCard
          title="Flood control"
          value={summary?.flooded ?? 0}
          accent="text-rose-300"
          hint="Новая панель сразу показывает проблемные аккаунты."
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <article className="v2-card rounded-[28px] p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="m-0 text-xl font-semibold text-white">Структура аккаунтов</h3>
              <p className="v2-muted mt-2 text-sm">
                Разбивка по типам, чтобы макет `V2` мог строить отдельные сценарии под каждую категорию.
              </p>
            </div>
            <Link to="/accounts" className="text-sm font-semibold text-indigo-300">
              Открыть список
            </Link>
          </div>

          <div className="mt-6 space-y-3">
            {typeItems.length ? (
              typeItems.map((item) => (
                <div
                  key={item.key}
                  className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-3"
                >
                  <div className="text-sm font-medium text-white">{item.key}</div>
                  <div className="text-lg font-semibold text-slate-100">{item.value}</div>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-700 px-4 py-8 text-center text-sm text-slate-400">
                Пока нет данных по типам аккаунтов.
              </div>
            )}
          </div>
        </article>

        <article className="v2-card rounded-[28px] p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="m-0 text-xl font-semibold text-white">Последние аккаунты</h3>
              <p className="v2-muted mt-2 text-sm">
                Этот блок уже можно заменить вашим готовым новым макетом карточек без связи с `V1`.
              </p>
            </div>
            <Link to="/proxy" className="text-sm font-semibold text-indigo-300">
              Прокси
            </Link>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {(summary?.recent_accounts || []).map((account) => (
              <article key={account.id} className="rounded-[24px] border border-slate-800 bg-slate-950/40 p-4">
                <div className="flex items-start gap-3">
                  <img
                    src={account.avatar_url || 'https://placehold.co/64x64/0f172a/e2e8f0?text=VK'}
                    alt={account.name || 'VK'}
                    className="h-14 w-14 rounded-2xl object-cover"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-base font-semibold text-white">
                      {[account.name, account.second_name].filter(Boolean).join(' ') || 'Без имени'}
                    </div>
                    <div className="v2-muted mt-1 truncate text-sm">
                      {account.login || `VK ID: ${account.vk_account_id}`}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="v2-chip" data-tone={getStatusTone(account.parse_status)}>
                        {formatStatus(account.parse_status)}
                      </span>
                      <span className="v2-chip" data-tone="info">
                        {account.account_type || 'account'}
                      </span>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
