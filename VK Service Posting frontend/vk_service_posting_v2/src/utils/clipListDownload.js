function parseErrorDetail(error) {
  const detail = error.response?.data;
  if (detail instanceof Blob) {
    return detail.text().then((text) => {
      try {
        const parsed = JSON.parse(text);
        return parsed?.detail || 'Не удалось скачать клипы';
      } catch {
        return 'Не удалось скачать клипы';
      }
    });
  }
  if (detail?.detail) {
    return Promise.resolve(typeof detail.detail === 'string' ? detail.detail : 'Не удалось скачать клипы');
  }
  return Promise.resolve(error.message || 'Не удалось скачать клипы');
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Скачивание через браузер (cookie), без загрузки всего ZIP в RAM. */
function triggerBrowserFileDownload(api, relativePath, filename) {
  const base = (api.defaults.baseURL || '/api').replace(/\/$/, '');
  const path = relativePath.startsWith('/') ? relativePath : `/${relativePath}`;
  const a = document.createElement('a');
  a.href = `${base}${path}`;
  a.download = filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

const POLL_MS = 800;
const MAX_POLL_MS = 3 * 60 * 60 * 1000;

/**
 * Мгновенный ZIP: urls.txt + index.html — видео качает браузер/IDM с ПК, не сервер.
 */
export async function downloadClipListLinks(api, basePath, list) {
  const count = Number(list.count || 0);
  if (!count) {
    throw new Error('В списке нет клипов для скачивания');
  }

  const response = await api.get(`${basePath}/get/${list.id}/download/links`, {
    responseType: 'blob',
    timeout: 120000,
  });

  const safeName = (list.name || `list_${list.id}`).replace(/[^\w\-.]+/g, '_').slice(0, 80);
  triggerBlobDownload(new Blob([response.data], { type: 'application/zip' }), `${safeName}_links.zip`);

  return {
    randomSample: response.headers?.['x-export-random-sample'] === '1',
    totalInList: response.headers?.['x-export-total-in-list'],
    exportCount: response.headers?.['x-export-count'],
  };
}

export async function downloadClipListZip(api, basePath, list, { onProgress } = {}) {
  const count = Number(list.count || 0);
  if (!count) {
    throw new Error('В списке нет клипов для скачивания');
  }

  const { data: started } = await api.post(`${basePath}/get/${list.id}/download/start`);
  let status = started;
  onProgress?.(status);

  const startedAt = Date.now();
  while (status.status === 'running' || status.status === 'pending') {
    if (Date.now() - startedAt > MAX_POLL_MS) {
      throw new Error('Превышено время ожидания формирования архива (3 ч)');
    }
    await new Promise((r) => setTimeout(r, POLL_MS));
    const { data } = await api.get(`${basePath}/download/export/${status.job_id}`);
    status = data;
    onProgress?.(status);
  }

  if (status.status === 'failed') {
    throw new Error(status.error || 'Ошибка формирования архива');
  }
  if (status.status !== 'done') {
    throw new Error('Не удалось завершить формирование архива');
  }
  if (!status.ok_count) {
    throw new Error(
      status.error
        || 'Не удалось скачать ни одного клипа на сервере. Попробуйте «Ссылки» или пополните базу.',
    );
  }

  const safeName = (list.name || `list_${list.id}`).replace(/[^\w\-.]+/g, '_').slice(0, 80);
  const zipFilename = status.filename || `${safeName}_clips.zip`;

  onProgress?.({ ...status, phase: 'downloading_file' });
  triggerBrowserFileDownload(
    api,
    `${basePath}/download/export/${status.job_id}/file`,
    zipFilename,
  );

  return {
    status,
    ok: String(status.ok_count ?? ''),
    failed: String(status.fail_count ?? ''),
    randomSample: status.random_sample,
    totalInList: status.total_in_list,
  };
}

export { parseErrorDetail };
