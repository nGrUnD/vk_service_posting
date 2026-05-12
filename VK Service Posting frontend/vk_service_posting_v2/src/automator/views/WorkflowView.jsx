import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Button,
  Divider,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Tooltip,
  Typography,
  message,
} from 'antd';

import { Copy, ExternalLink, Loader2, PlayCircle, Plus, Settings, Trash2 } from 'lucide-react';

import api from '../../api/axios';
import { useAutomatorUser } from '../AutomatorUserContext.jsx';

const { Title, Text } = Typography;

const DEFAULT_BANNER_FORM = {
  banner_x: 0,
  banner_y: 0,
  banner_width: 100,
  banner_height: 15,
  banner_remove_green_background: true,
};

function getApiBaseUrl() {
  return (api.defaults.baseURL || '/api').replace(/\/$/, '');
}

function getV1Url() {
  return import.meta.env.VITE_V1_URL || `${window.location.protocol}//${window.location.hostname}/`;
}

function getV1WorkflowStatusUrl() {
  return `${getV1Url().replace(/\/$/, '')}/dashboard/workflow-status`;
}

function isVkAccountUrl(url) {
  if (!url || typeof url !== 'string') return false;
  const t = url.trim();
  if (!t || t === 'pending') return false;
  return /^https?:\/\//i.test(t);
}

/** Формат даты/времени как в V1 WorkflowStatusPage */
function formatLastPostRu(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const s = d
    .toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
    .replace(',', ' -');
  const diffHours = (Date.now() - d.getTime()) / 3600000;
  return { text: s, stale: diffHours > 4 };
}

function parseFilterKeywords(text) {
  return text
    .split(/[\n,]+/)
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

function parseLinksText(text) {
  return text
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function pipelineLabel(parseStatus) {
  if (parseStatus === 'success') return 'Готово';
  if (parseStatus === 'failure' || parseStatus === 'failed') return 'Ошибка';
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
  const [tableSearch, setTableSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [updatingWorkerpostId, setUpdatingWorkerpostId] = useState(null);
  const [deletingWorkerpostId, setDeletingWorkerpostId] = useState(null);

  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [clipLists, setClipLists] = useState([]);
  const [loadingClips, setLoadingClips] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [bannerFile, setBannerFile] = useState(null);
  const [bannerPreviewUrl, setBannerPreviewUrl] = useState(null);
  const [bannerMarkedForDeletion, setBannerMarkedForDeletion] = useState(false);
  const [modalForm, setModalForm] = useState({
    name: '',
    description: '',
    repost_enabled: false,
    daily_limit: 0,
    hourly_limit: 0,
    clip_list_id: null,
    ...DEFAULT_BANNER_FORM,
  });
  const bannerFileInputRef = useRef(null);

  const load = useCallback(
    async (opts = { silent: false }) => {
      if (!opts.silent) setLoading(true);
      let tableData = [];
      try {
        const apiBase = getApiBaseUrl();
        const response = await api.get(`/users/${user.id}/workerpost/all`);
        tableData = (Array.isArray(response.data) ? response.data : []).map((item) => {
          const { workpost, vk_group, vk_account, category, clip_list, account_data } = item;
          const accountUrl = vk_account?.vk_account_url;
          const ad = account_data;
          const accountLoginPass =
            ad?.login != null && String(ad.login).length
              ? ad?.password != null && String(ad.password).length
                ? `${ad.login}:${ad.password}`
                : `${ad.login}:••••`
              : '—';
          const bannerVideoUrl = workpost?.banner_video_path
            ? `${apiBase}/users/${user.id}/workerpost/${workpost.id}/banner`
            : null;
          return {
            id: workpost.id,
            groupName: vk_group?.name,
            groupUrl: vk_group?.vk_group_url,
            accountName: `${vk_account?.name ?? ''} ${vk_account?.second_name ?? ''}`.trim(),
            accountUrl: isVkAccountUrl(accountUrl) ? accountUrl : null,
            accountLoginPass,
            categoryId: category?.id,
            workerpost: {
              id: workpost.id,
              isActive: workpost?.is_active,
              bannerVideoUrl,
              hasBanner: Boolean(workpost?.banner_video_path),
              banner_x: workpost.banner_x ?? DEFAULT_BANNER_FORM.banner_x,
              banner_y: workpost.banner_y ?? DEFAULT_BANNER_FORM.banner_y,
              banner_width: workpost.banner_width ?? DEFAULT_BANNER_FORM.banner_width,
              banner_height: workpost.banner_height ?? DEFAULT_BANNER_FORM.banner_height,
              banner_remove_green_background:
                workpost.banner_remove_green_background ?? DEFAULT_BANNER_FORM.banner_remove_green_background,
            },
            category: category?.name,
            hourly: category?.hourly_limit,
            active: workpost?.is_active,
            clipList: clip_list?.name,
            parseStatus: vk_account?.parse_status,
            lastPostAt: workpost?.last_post_at ?? null,
            accountType: vk_account?.account_type ?? null,
            floodControl: Boolean(vk_account?.flood_control),
            floodControlTime: vk_account?.flood_control_time ?? null,
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

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingClips(true);
      try {
        const { data } = await api.get(`/users/${user.id}/clip_list/get_all`);
        if (!cancelled) setClipLists(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setClipLists([]);
      } finally {
        if (!cancelled) setLoadingClips(false);
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

  const handleToggleActive = useCallback(
    async (rowId, nextActive) => {
      setUpdatingWorkerpostId(rowId);
      try {
        await api.put(`/users/${user.id}/workerpost/${rowId}`, { is_active: nextActive });
        setRows((prev) =>
          prev.map((r) =>
            r.id === rowId
              ? {
                  ...r,
                  active: nextActive,
                  workerpost: r.workerpost ? { ...r.workerpost, isActive: nextActive } : r.workerpost,
                }
              : r,
          ),
        );
        messageApi.success(nextActive ? 'Воркерпост включён' : 'Воркерпост на паузе');
      } catch {
        messageApi.error('Не удалось обновить статус воркерпоста');
      } finally {
        setUpdatingWorkerpostId(null);
      }
    },
    [messageApi, user.id],
  );

  const handleDeleteWorkerpost = useCallback(
    async (rowId) => {
      if (!window.confirm('Удалить воркерпост? Аккаунт вернётся в backup по связке с пабликом.')) return;
      setDeletingWorkerpostId(rowId);
      try {
        await api.delete(`/users/${user.id}/workerpost/${rowId}`);
        messageApi.success('Воркерпост удалён');
        await load({ silent: true });
      } catch (e) {
        messageApi.error(e.response?.data?.detail || 'Ошибка удаления');
      } finally {
        setDeletingWorkerpostId(null);
      }
    },
    [load, messageApi, user.id],
  );

  const cleanupLocalBannerPreview = useCallback(() => {
    setBannerPreviewUrl((prev) => {
      if (prev?.startsWith('blob:')) {
        URL.revokeObjectURL(prev);
      }
      return null;
    });
  }, []);

  const closeSettingsModal = useCallback(() => {
    cleanupLocalBannerPreview();
    setSettingsModalOpen(false);
    setEditingRecord(null);
    setBannerFile(null);
    setBannerMarkedForDeletion(false);
  }, [cleanupLocalBannerPreview]);

  const openSettingsModal = useCallback(
    (row) => {
      if (row.categoryId == null) {
        messageApi.warning('Нет категории для этой строки — обновите список.');
        return;
      }
      const fullCategory = categories.find((c) => c.id === row.categoryId);
      setEditingRecord({
        id: row.id,
        category: { id: row.categoryId },
        workerpost: row.workerpost,
      });
      setBannerFile(null);
      setBannerMarkedForDeletion(false);
      cleanupLocalBannerPreview();
      setModalForm({
        name: fullCategory?.name ?? '',
        description: fullCategory?.description ?? '',
        repost_enabled: fullCategory?.repost_enabled ?? false,
        daily_limit: fullCategory?.daily_limit ?? 0,
        hourly_limit: fullCategory?.hourly_limit ?? 0,
        clip_list_id: fullCategory?.clip_list_id ?? null,
        banner_x: row.workerpost.banner_x,
        banner_y: row.workerpost.banner_y,
        banner_width: row.workerpost.banner_width,
        banner_height: row.workerpost.banner_height,
        banner_remove_green_background: row.workerpost.banner_remove_green_background,
      });
      setBannerPreviewUrl(row.workerpost.bannerVideoUrl);
      setSettingsModalOpen(true);
    },
    [categories, cleanupLocalBannerPreview, messageApi],
  );

  const updateModalForm = useCallback((patch) => {
    setModalForm((prev) => ({ ...prev, ...patch }));
  }, []);

  const handleBannerChange = (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (file.type && !file.type.startsWith('video/')) {
      messageApi.error('Нужно выбрать видеофайл');
      return;
    }
    cleanupLocalBannerPreview();
    setBannerFile(file);
    setBannerMarkedForDeletion(false);
    setBannerPreviewUrl(URL.createObjectURL(file));
  };

  const handleBannerDeleteClick = () => {
    cleanupLocalBannerPreview();
    setBannerFile(null);
    setBannerMarkedForDeletion(true);
  };

  const copyToClipboard = useCallback(
    async (text, successMsg = 'Скопировано') => {
      if (!text || text === '—') return;
      try {
        await navigator.clipboard.writeText(text);
        messageApi.success(successMsg);
      } catch {
        messageApi.error('Не удалось скопировать');
      }
    },
    [messageApi],
  );

  const handleSaveSettings = useCallback(async () => {
    if (!editingRecord?.category?.id || !editingRecord?.workerpost?.id) return;
    setSavingSettings(true);
    try {
      await api.put(`/users/${user.id}/categories/edit/${editingRecord.category.id}`, {
        name: modalForm.name,
        description: modalForm.description,
        repost_enabled: modalForm.repost_enabled ?? false,
        daily_limit: modalForm.daily_limit ?? 0,
        hourly_limit: modalForm.hourly_limit ?? 0,
        clip_list_id: modalForm.clip_list_id,
        is_active: true,
      });

      await api.put(`/users/${user.id}/workerpost/${editingRecord.workerpost.id}`, {
        banner_x: modalForm.banner_x,
        banner_y: modalForm.banner_y,
        banner_width: modalForm.banner_width,
        banner_height: modalForm.banner_height,
        banner_remove_green_background: modalForm.banner_remove_green_background,
      });

      if (bannerMarkedForDeletion && editingRecord.workerpost.hasBanner) {
        await api.delete(`/users/${user.id}/workerpost/${editingRecord.workerpost.id}/banner`);
      }

      if (bannerFile) {
        const payload = new FormData();
        payload.append('banner_file', bannerFile);
        await api.post(`/users/${user.id}/workerpost/${editingRecord.workerpost.id}/banner`, payload, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }

      messageApi.success('Настройки workerpost обновлены');
      closeSettingsModal();
      await load({ silent: true });
    } catch (e) {
      messageApi.error(e.response?.data?.detail || 'Ошибка при сохранении настроек');
    } finally {
      setSavingSettings(false);
    }
  }, [
    bannerFile,
    bannerMarkedForDeletion,
    closeSettingsModal,
    editingRecord,
    load,
    messageApi,
    modalForm,
    user.id,
  ]);

  const activeCount = useMemo(() => rows.filter((r) => r.active).length, [rows]);

  const filterKeywords = useMemo(() => parseFilterKeywords(tableSearch), [tableSearch]);

  const filteredRows = useMemo(() => {
    if (!filterKeywords.length) return rows;
    return rows.filter((r) => filterKeywords.some((kw) => String(r.groupName || '').toLowerCase().includes(kw)));
  }, [rows, filterKeywords]);

  const pageCount = useMemo(
    () => Math.max(1, Math.ceil(filteredRows.length / pageSize) || 1),
    [filteredRows.length, pageSize],
  );

  const paginatedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredRows.slice(start, start + pageSize);
  }, [filteredRows, page, pageSize]);

  useEffect(() => {
    setPage(1);
  }, [tableSearch]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  const currentBannerPreview = bannerMarkedForDeletion ? null : bannerPreviewUrl;

  return (
    <div className="space-y-6">
      {contextHolder}

      <section className="rounded-3xl border border-amber-100 bg-amber-50/80 p-6 shadow-sm">
        <h3 className="mb-2 text-lg font-black text-amber-900">Редактирование баннеров и клипов</h3>
        <p className="text-sm font-medium text-amber-800">
          Детальные настройки строки (категория, описание, репост, баннер) — в модалке «Настройки» в таблице ниже. Здесь
          же можно открыть полный экран V1.
        </p>
        <button
          type="button"
          onClick={() => window.open(getV1WorkflowStatusUrl(), '_blank')}
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
          Паблик должен уже быть в сервисе у главного тех. аккаунта. Отдельно нужен{' '}
          <strong className="font-semibold text-gray-700">backup-аккаунт, привязанный к этому паблику</strong> в базе
          (после импорта и успешного разбора групп или через парный импорт на странице «Аккаунты ВК»). Сначала
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
              {preview.already_workerpost ? (
                <span className="rounded-lg bg-rose-100 px-2 py-1 text-rose-900">
                  Уже воркерпост: {preview.already_workerpost}
                </span>
              ) : null}
            </div>
            {preview.no_backup_linked ? (
              <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50/90 p-4 text-sm text-amber-950">
                <p className="font-black text-amber-950">Нет backup для паблика — что сделать</p>
                <p className="mt-2 font-medium leading-relaxed text-amber-900/95">
                  Сервис не нашёл ни одного backup-аккаунта, <strong className="font-semibold">уже связанного с этим
                  пабликом</strong> (запись в базе после импорта и разбора). Пока связи нет — воркерпост не создать.
                </p>
                <ol className="mt-3 list-decimal space-y-2 pl-5 font-medium leading-relaxed text-amber-900/95">
                  <li>
                    Импортируйте backup (log:pass) в{' '}
                    <Link to="/accounts" className="font-bold text-blue-700 underline hover:text-blue-900">
                      Аккаунты ВК
                    </Link>
                    , дождитесь успешного подключения. У аккаунта в ВК должна быть подписка на этот паблик — тогда при
                    разборе групп появится привязка «паблик ↔ backup».
                  </li>
                  <li>
                    Либо в том же разделе, блок «Дополнительные способы» →{' '}
                    <strong className="font-semibold">парный импорт</strong> (log:pass и ссылка на паблик по строкам)
                    — если паблик ещё не привязан к backup.
                  </li>
                </ol>
              </div>
            ) : null}
            <ul className="max-h-48 space-y-2 overflow-y-auto text-xs">
              {(preview.links || []).map((row, idx) => (
                <li
                  key={`${row.link}-${idx}`}
                  className={`rounded-lg border px-3 py-2 ${
                    row.status === 'will_queue'
                      ? 'border-green-200 bg-green-50/50'
                      : row.status === 'already_workerpost'
                        ? 'border-rose-200 bg-rose-50/60'
                        : row.status === 'no_backup'
                          ? 'border-amber-200 bg-amber-50/40'
                          : 'border-gray-200 bg-white'
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
            {filterKeywords.length > 0 && filteredRows.length !== rows.length ? (
              <span className="ml-2 text-gray-400">
                (по фильтру: {filteredRows.length} строк)
              </span>
            ) : null}
          </p>
        )}
      </section>

      <section className="overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
        <div className="flex flex-col gap-4 border-b border-gray-100 p-6 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-xl font-black text-gray-800">Список воркеров</h3>
            <button
              type="button"
              onClick={() => load()}
              className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-50"
            >
              Обновить
            </button>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <label className="block min-w-0 flex-1 text-xs font-bold uppercase tracking-wide text-gray-600">
              Фильтр по названию паблика
              <textarea
                rows={3}
                className="mt-1 w-full resize-y rounded-xl border border-gray-100 bg-gray-50 px-4 py-2.5 text-sm font-medium text-gray-800 outline-none focus:ring-2 focus:ring-blue-100"
                placeholder="Несколько слов через запятую или с новой строки"
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
              />
            </label>
            <label className="flex shrink-0 items-center gap-2 text-xs font-bold text-gray-600">
              На странице
              <select
                className="rounded-lg border border-gray-200 bg-white px-2 py-2 text-sm font-bold"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </label>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-gray-100/90 text-xs font-bold uppercase tracking-wide text-gray-700">
              <tr>
                <th className="px-8 py-5">ID / Группа</th>
                <th className="px-6 py-5">Аккаунт</th>
                <th className="px-6 py-5">Категория</th>
                <th className="px-6 py-5">Лимит клипов/ч</th>
                <th className="px-6 py-5">Пайплайн</th>
                <th className="px-6 py-5">Состояние</th>
                <th className="px-6 py-5">Постинг</th>
                <th className="px-8 py-5 text-right">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm text-gray-800">
              {paginatedRows.map((row) => {
                const lastPost = formatLastPostRu(row.lastPostAt);
                return (
                  <tr key={row.id} className="group transition-colors hover:bg-gray-50/50">
                    <td className="px-8 py-5">
                      {row.groupUrl ? (
                        <a
                          href={row.groupUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-sm font-bold text-blue-700 hover:underline"
                        >
                          {row.groupName}{' '}
                          <ExternalLink size={14} className="opacity-0 transition-opacity group-hover:opacity-100" />
                        </a>
                      ) : (
                        <span className="text-sm font-bold text-gray-900">{row.groupName}</span>
                      )}
                      {row.groupUrl ? (
                        <div className="mt-1 flex max-w-[18rem] items-center gap-1">
                          <span className="min-w-0 flex-1 truncate font-mono text-xs text-gray-600" title={row.groupUrl}>
                            {row.groupUrl}
                          </span>
                          <button
                            type="button"
                            title="Копировать ссылку на паблик"
                            onClick={() => void copyToClipboard(row.groupUrl, 'Ссылка скопирована')}
                            className="shrink-0 rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-800"
                          >
                            <Copy size={14} />
                          </button>
                        </div>
                      ) : null}
                      <div className="mt-0.5 font-mono text-xs font-medium text-gray-600">#{row.id}</div>
                    </td>
                    <td className="px-6 py-5">
                      <Tooltip title={row.accountName?.trim() ? row.accountName : undefined}>
                        <div className="flex max-w-[18rem] items-center gap-1.5">
                          <span className="min-w-0 flex-1 truncate font-mono text-sm text-gray-900" title={row.accountLoginPass}>
                            {row.accountLoginPass}
                          </span>
                          <button
                            type="button"
                            title="Копировать логин:пароль"
                            disabled={row.accountLoginPass === '—'}
                            onClick={() => void copyToClipboard(row.accountLoginPass)}
                            className="shrink-0 rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-800 disabled:opacity-30"
                          >
                            <Copy size={14} />
                          </button>
                        </div>
                      </Tooltip>
                    </td>
                    <td className="px-6 py-5">
                      <span className="rounded-lg bg-gray-100 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-gray-700">
                        {row.category || '—'}
                      </span>
                    </td>
                    <td className="px-6 py-5 font-mono text-sm font-bold text-gray-900">{row.hourly ?? '—'}</td>
                    <td className="px-6 py-5">
                      <span className="text-sm font-bold text-slate-800">{pipelineLabel(row.parseStatus)}</span>
                    </td>
                    <td className="max-w-[14rem] px-6 py-5 text-sm leading-relaxed text-gray-800">
                      <div>
                        {lastPost ? (
                          <span className={lastPost.stale ? 'font-semibold text-red-600' : 'text-gray-800'}>
                            Постинг: {lastPost.text}
                          </span>
                        ) : (
                          <span className="font-semibold text-red-600">Постинг: нет данных</span>
                        )}
                      </div>
                      <div className="mt-1">
                        {row.accountType === 'blocked' ? (
                          <span className="font-bold text-red-600">Аккаунт: заблокирован</span>
                        ) : (
                          <span className="font-bold text-green-700">Аккаунт: активен</span>
                        )}
                      </div>
                      <div className="mt-1 text-gray-600">Флудконтроль: {row.floodControl ? 'Да' : 'Нет'}</div>
                    </td>
                    <td className="px-6 py-5">
                      <Switch
                        checked={row.active}
                        loading={updatingWorkerpostId === row.id}
                        disabled={updatingWorkerpostId === row.id}
                        onChange={(checked) => void handleToggleActive(row.id, checked)}
                        checkedChildren="Вкл"
                        unCheckedChildren="Выкл"
                      />
                    </td>
                    <td className="px-8 py-5 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          title="Настройки workerpost"
                          onClick={() => openSettingsModal(row)}
                          className="rounded-xl p-2.5 text-gray-500 transition-all hover:bg-blue-50 hover:text-blue-600"
                        >
                          <Settings size={18} />
                        </button>
                        <button
                          type="button"
                          disabled={deletingWorkerpostId === row.id}
                          title="Удалить воркерпост"
                          onClick={() => void handleDeleteWorkerpost(row.id)}
                          className="rounded-xl p-2.5 text-gray-500 transition-all hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                        >
                          {deletingWorkerpostId === row.id ? (
                            <Loader2 size={18} className="animate-spin" />
                          ) : (
                            <Trash2 size={18} />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!loading && !rows.length && (
                <tr>
                  <td colSpan={8} className="px-8 py-12 text-center text-sm text-gray-500">
                    Нет воркерпостов. Создайте через форму выше или в V1.
                  </td>
                </tr>
              )}
              {!loading && rows.length > 0 && filteredRows.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-8 py-12 text-center text-sm text-gray-500">
                    Нет строк по фильтру. Измените запрос.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {!loading && filteredRows.length > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-6 py-4 text-sm text-gray-700 sm:px-8">
            <span>
              Показано{' '}
              {filteredRows.length === 0
                ? '0'
                : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, filteredRows.length)}`}{' '}
              из {filteredRows.length}
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-lg border border-gray-200 px-3 py-1.5 font-bold hover:bg-gray-50 disabled:opacity-40"
              >
                Назад
              </button>
              <span className="font-mono">
                Стр. {page} / {pageCount}
              </span>
              <button
                type="button"
                disabled={page >= pageCount}
                onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                className="rounded-lg border border-gray-200 px-3 py-1.5 font-bold hover:bg-gray-50 disabled:opacity-40"
              >
                Вперёд
              </button>
            </div>
          </div>
        ) : null}
      </section>

      <Modal
        open={settingsModalOpen}
        onCancel={closeSettingsModal}
        title={editingRecord ? `Настройки workerpost #${editingRecord.id}` : 'Настройки workerpost'}
        width={900}
        destroyOnClose
        footer={[
          <Button key="cancel" onClick={closeSettingsModal}>
            Отмена
          </Button>,
          <Button key="save" type="primary" loading={savingSettings} onClick={() => void handleSaveSettings()}>
            Сохранить
          </Button>,
        ]}
      >
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="flex flex-col gap-4">
            <Title level={5} style={{ margin: 0 }}>
              Категория
            </Title>

            <Input
              placeholder="Название"
              value={modalForm.name}
              onChange={(e) => updateModalForm({ name: e.target.value })}
            />

            <Input.TextArea
              placeholder="Описание"
              value={modalForm.description}
              onChange={(e) => updateModalForm({ description: e.target.value })}
              rows={4}
            />

            <div className="flex items-center justify-between">
              <span>Репост:</span>
              <Switch
                checked={modalForm.repost_enabled}
                onChange={(value) => updateModalForm({ repost_enabled: value })}
              />
            </div>

            <Select
              className="min-w-0 w-full"
              placeholder="Список клипов"
              value={modalForm.clip_list_id}
              onChange={(value) => updateModalForm({ clip_list_id: value })}
              allowClear
              loading={loadingClips}
              options={clipLists.map((item) => ({
                label: item.name,
                value: item.id,
              }))}
            />

            <Divider style={{ margin: '8px 0' }} />

            <Title level={5} style={{ margin: 0 }}>
              Видео-баннер
            </Title>
            <Text type="secondary">Координаты и размер задаются в процентах от итогового видео.</Text>
            <div className="flex flex-wrap items-center gap-3">
              <input
                ref={bannerFileInputRef}
                type="file"
                accept="video/*,.mp4,.mov,.webm,.m4v"
                className="sr-only"
                tabIndex={-1}
                onChange={handleBannerChange}
              />
              <Button type="default" onClick={() => bannerFileInputRef.current?.click()} aria-label="Выбрать видеофайл баннера">
                Выберите файл
              </Button>
              <Text type="secondary" className="text-sm">
                {bannerFile?.name || 'Файл не выбран'}
              </Text>
            </div>

            <Space wrap>
              <Button
                onClick={() =>
                  updateModalForm({
                    banner_x: DEFAULT_BANNER_FORM.banner_x,
                    banner_y: DEFAULT_BANNER_FORM.banner_y,
                    banner_width: DEFAULT_BANNER_FORM.banner_width,
                    banner_height: DEFAULT_BANNER_FORM.banner_height,
                  })
                }
              >
                Сбросить положение
              </Button>
              <Button
                danger
                onClick={handleBannerDeleteClick}
                disabled={!currentBannerPreview && !editingRecord?.workerpost?.hasBanner}
              >
                Удалить баннер
              </Button>
            </Space>

            {currentBannerPreview ? (
              <div className="flex items-center justify-between">
                <span>Удалить фон (зелёный):</span>
                <Switch
                  checked={modalForm.banner_remove_green_background}
                  onChange={(value) => updateModalForm({ banner_remove_green_background: value })}
                />
              </div>
            ) : null}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Text>X (%)</Text>
                <InputNumber
                  min={0}
                  max={100}
                  step={0.5}
                  value={modalForm.banner_x}
                  onChange={(value) => updateModalForm({ banner_x: value ?? 0 })}
                  style={{ width: '100%' }}
                />
              </div>
              <div>
                <Text>Y (%)</Text>
                <InputNumber
                  min={0}
                  max={100}
                  step={0.5}
                  value={modalForm.banner_y}
                  onChange={(value) => updateModalForm({ banner_y: value ?? 0 })}
                  style={{ width: '100%' }}
                />
              </div>
              <div>
                <Text>Ширина (%)</Text>
                <InputNumber
                  min={1}
                  max={100}
                  step={0.5}
                  value={modalForm.banner_width}
                  onChange={(value) => updateModalForm({ banner_width: value ?? 1 })}
                  style={{ width: '100%' }}
                />
              </div>
              <div>
                <Text>Высота (%)</Text>
                <InputNumber
                  min={1}
                  max={100}
                  step={0.5}
                  value={modalForm.banner_height}
                  onChange={(value) => updateModalForm({ banner_height: value ?? 1 })}
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <Title level={5} style={{ margin: 0 }}>
              Превью
            </Title>
            <Text type="secondary">Макет показывает пример положения баннера на вертикальном клипе.</Text>

            <div
              style={{
                position: 'relative',
                width: 320,
                height: 568,
                margin: '0 auto',
                borderRadius: 20,
                overflow: 'hidden',
                background: 'linear-gradient(180deg, #1f2937 0%, #111827 100%)',
                border: '1px solid #d9d9d9',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'rgba(255,255,255,0.65)',
                  fontSize: 18,
                  letterSpacing: 1,
                  textTransform: 'uppercase',
                }}
              >
                Preview clip
              </div>

              {currentBannerPreview ? (
                <video
                  key={currentBannerPreview}
                  src={currentBannerPreview}
                  autoPlay
                  loop
                  muted
                  playsInline
                  style={{
                    position: 'absolute',
                    left: `${modalForm.banner_x}%`,
                    top: `${modalForm.banner_y}%`,
                    width: `${modalForm.banner_width}%`,
                    height: `${modalForm.banner_height}%`,
                    objectFit: 'fill',
                    borderRadius: 8,
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
                  }}
                />
              ) : (
                <div
                  style={{
                    position: 'absolute',
                    left: `${modalForm.banner_x}%`,
                    top: `${modalForm.banner_y}%`,
                    width: `${modalForm.banner_width}%`,
                    height: `${modalForm.banner_height}%`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px dashed rgba(255,255,255,0.5)',
                    color: 'rgba(255,255,255,0.8)',
                    fontSize: 12,
                    textAlign: 'center',
                    background: 'rgba(255,255,255,0.08)',
                  }}
                >
                  Баннер не загружен
                </div>
              )}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
