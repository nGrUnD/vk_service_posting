import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';
import { ExternalLink, Loader2, PlayCircle, Plus, Settings, Trash2 } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

function getV1Url() {
  return import.meta.env.VITE_V1_URL || `${window.location.protocol}//${window.location.hostname}/`;
}

function parseLinksText(text) {
  return text
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function pipelineLabel(parseStatus) {
  if (parseStatus === 'success') return 'Готово';
  if (parseStatus === 'failure') return 'Ошибка';
  if (parseStatus === 'pending') return 'Selenium / API…';
  return parseStatus || '—';
}

export default function WorkflowView() {
  const user = useAutomatorUser();
  const [messageApi, contextHolder] = message.useMessage();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [linksText, setLinksText] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [postCreatePoll, setPostCreatePoll] = useState(0);

  const load = useCallback(
    async (opts = { silent: false }) => {
      if (!opts.silent) setLoading(true);
      let tableData = [];
      try {
        const response = await api.get(`/users/${user.id}/workerpost/all`);
        tableData = (Array.isArray(response.data) ? response.data : []).map((item) => {
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
            parseStatus: workpost?.parse_status,
            taskId: workpost?.task_id,
          };
        });
        setRows(tableData);
      } catch {
        if (!opts.silent) messageApi.error('Не удалось загрузить workerpost');
      } finally {
        if (!opts.silent) setLoading(false);
      }
      return tableData;
    },
    [messageApi, user.id],
  );

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get(`/users/${user.id}/categories/get_all`);
        if (!cancelled) setCategories(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setCategories([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user.id]);

  const linkLines = useMemo(() => parseLinksText(linksText), [linksText]);

  const handlePreview = async () => {
    const cid = Number(categoryId);
    if (!cid) {
      messageApi.warning('Выберите категорию');
      return;
    }
    if (!linkLines.length) {
      messageApi.warning('Вставьте ссылки на паблики (по строке)');
      return;
    }
    setPreviewLoading(true);
    try {
      const { data } = await api.post(`/users/${user.id}/workerpost/preview_create`, {
        vk_groups_links: linkLines,
        category_id: cid,
      });
      setPreview(data);
    } catch (e) {
      messageApi.error(e.response?.data?.detail || 'Не удалось выполнить предпросмотр');
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCreate = async () => {
    const cid = Number(categoryId);
    if (!cid) {
      messageApi.warning('Выберите категорию');
      return;
    }
    if (!linkLines.length) {
      messageApi.warning('Вставьте ссылки на паблики');
      return;
    }
    setCreateLoading(true);
    try {
      const { data } = await api.post(`/users/${user.id}/workerpost/create_workerpost`, {
        vk_groups_links: linkLines,
        category_id: cid,
      });
      const failed = data?.detail?.['failed group'] || data?.detail?.failed_group || [];
      if (Array.isArray(failed) && failed.length) {
        messageApi.warning(`Часть пабликов не в очереди: ${failed.slice(0, 8).join(', ')}${failed.length > 8 ? '…' : ''}`);
      } else {
        messageApi.success('Задачи создания воркерпостов поставлены в очередь');
      }
      await load({ silent: true });
      setPostCreatePoll((k) => k + 1);
    } catch (e) {
      messageApi.error(e.response?.data?.detail || 'Ошибка create_workerpost');
    } finally {
      setCreateLoading(false);
    }
  };

  useEffect(() => {
    if (postCreatePoll === 0) return undefined;
    let ticks = 0;
    const maxTicks = 22;
    const id = setInterval(async () => {
      ticks += 1;
      const data = await load({ silent: true });
      const pending = data.filter((r) => r.parseStatus === 'pending');
      if (!pending.length || ticks >= maxTicks) {
        clearInterval(id);
        if (ticks >= maxTicks && pending.length) {
          messageApi.info('Долгие задачи Selenium ещё выполняются — обновите список позже.');
        }
      }
    }, 4000);
    return () => clearInterval(id);
  }, [postCreatePoll, load, messageApi]);

  const activeCount = rows.filter((r) => r.active).length;

  return (
    <div className="space-y-6">
      {contextHolder}

      <section className="rounded-3xl border border-amber-100 bg-amber-50/80 p-6 shadow-sm">
        <h3 className="mb-2 text-lg font-black text-amber-900">Редактирование баннеров и клипов</h3>
        <p className="text-sm font-medium text-amber-800">
          Полный конструктор (баннеры, категории, списки клипов) пока в V1. Ниже — создание воркерпостов по ссылкам и
          живой список из API.
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
        <h3 className="mb-2 flex items-center gap-3 text-xl font-black text-gray-800">
          <div className="rounded-xl bg-blue-50 p-2 text-blue-600">
            <PlayCircle size={20} />
          </div>
          Новые воркерпосты (только ссылки + категория)
        </h3>
        <p className="mb-6 text-sm text-gray-500">
          Для каждой ссылки нужен паблик в сервисе и backup-аккаунт, уже привязанный к этому паблику. Сначала нажмите
          «Предпросмотр».
        </p>
        <div className="flex flex-col gap-6 lg:flex-row">
          <div className="min-w-0 flex-1">
            <label className="mb-2 block text-xs font-black uppercase tracking-widest text-gray-400">
              Ссылки vk.com/club… или public… ({linkLines.length} шт.)
            </label>
            <textarea
              className="h-44 w-full resize-none rounded-2xl border border-gray-100 bg-gray-50 p-4 font-mono text-sm outline-none focus:ring-4 focus:ring-blue-100"
              placeholder={'https://vk.com/public123456\nhttps://vk.com/club123456'}
              value={linksText}
              onChange={(e) => setLinksText(e.target.value)}
            />
          </div>
          <div className="flex w-full shrink-0 flex-col justify-end gap-4 lg:w-72">
            <div>
              <label className="mb-2 block text-xs font-black uppercase tracking-widest text-gray-400">Категория</label>
              <select
                className="w-full rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-100"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
              >
                <option value="">— выберите —</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} (#{c.id})
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              disabled={previewLoading}
              onClick={handlePreview}
              className="rounded-2xl border-2 border-blue-200 bg-white py-3 text-sm font-bold text-blue-700 hover:bg-blue-50 disabled:opacity-60"
            >
              {previewLoading ? 'Предпросмотр…' : 'Предпросмотр'}
            </button>
            <button
              type="button"
              disabled={createLoading}
              onClick={handleCreate}
              className="flex items-center justify-center gap-2 rounded-2xl bg-blue-600 py-4 text-sm font-bold text-white shadow-lg shadow-blue-100 hover:bg-blue-700 disabled:opacity-60"
            >
              {createLoading ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
              Запустить создание
            </button>
          </div>
        </div>

        {preview && (
          <div className="mt-8 rounded-2xl border border-gray-100 bg-gray-50/80 p-6">
            <h4 className="mb-3 text-sm font-black text-gray-800">Результат предпросмотра</h4>
            <div className="mb-4 flex flex-wrap gap-3 text-xs font-bold">
              <span className="rounded-lg bg-green-100 px-2 py-1 text-green-800">В очередь: {preview.will_queue}</span>
              <span className="rounded-lg bg-red-100 px-2 py-1 text-red-800">Не встанут: {preview.will_fail}</span>
              {preview.invalid_url ? (
                <span className="rounded-lg bg-amber-100 px-2 py-1 text-amber-900">Неверный URL: {preview.invalid_url}</span>
              ) : null}
              {preview.missing_group_in_admin ? (
                <span className="rounded-lg bg-amber-100 px-2 py-1 text-amber-900">
                  Нет паблика в админке: {preview.missing_group_in_admin}
                </span>
              ) : null}
              {preview.no_backup_linked ? (
                <span className="rounded-lg bg-amber-100 px-2 py-1 text-amber-900">
                  Нет backup: {preview.no_backup_linked}
                </span>
              ) : null}
              {preview.no_main_account ? (
                <span className="rounded-lg bg-rose-100 px-2 py-1 text-rose-900">Нет главного аккаунта</span>
              ) : null}
              {preview.no_category ? (
                <span className="rounded-lg bg-rose-100 px-2 py-1 text-rose-900">Категория недоступна</span>
              ) : null}
            </div>
            <ul className="max-h-48 space-y-2 overflow-y-auto text-xs">
              {(preview.links || []).map((row, idx) => (
                <li
                  key={`${row.link}-${idx}`}
                  className={`rounded-lg border px-3 py-2 ${
                    row.status === 'will_queue' ? 'border-green-200 bg-green-50/50' : 'border-gray-200 bg-white'
                  }`}
                >
                  <span className="font-mono text-gray-700">{row.link}</span>
                  <span className="ml-2 font-bold text-gray-900">{row.status}</span>
                  {row.detail ? <span className="ml-2 text-gray-500">{row.detail}</span> : null}
                  {row.chosen_account_id != null ? (
                    <span className="ml-2 font-mono text-gray-400">acc #{row.chosen_account_id}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
        <h3 className="mb-2 text-lg font-black text-gray-800">Воркерпосты</h3>
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
            onClick={() => load()}
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
                <th className="px-6 py-5">Пайплайн</th>
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
                        {row.groupName}{' '}
                        <ExternalLink size={12} className="opacity-0 transition-opacity group-hover:opacity-100" />
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
                    <span className="text-xs font-bold text-slate-700">{pipelineLabel(row.parseStatus)}</span>
                    {row.taskId ? (
                      <div className="mt-0.5 font-mono text-[10px] text-gray-400">
                        task {String(row.taskId).slice(0, 14)}…
                      </div>
                    ) : null}
                  </td>
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
                  <td colSpan={7} className="px-8 py-12 text-center text-sm text-gray-500">
                    Нет воркерпостов. Создайте через форму выше или в V1.
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
