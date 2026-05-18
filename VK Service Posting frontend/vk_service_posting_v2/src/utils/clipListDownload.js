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

/**
 * @param {import('axios').AxiosInstance} api
 * @param {string} basePath e.g. `/users/1/clip_list`
 * @param {{ id: number, name?: string, count?: number }} list
 * @param {{ onProgress?: (status: object) => void }} opts
 */
export async function downloadClipListZip(api, basePath, list, { onProgress } = {}) {
  const count = Number(list.count || 0);
  if (!count) {
    throw new Error('В списке нет клипов для скачивания');
  }

  const { data: started } = await api.post(`${basePath}/get/${list.id}/download/start`);
  let status = started;
  onProgress?.(status);

  const pollMs = 800;
  while (status.status === 'running' || status.status === 'pending') {
    await new Promise((r) => setTimeout(r, pollMs));
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

  const response = await api.get(`${basePath}/download/export/${status.job_id}/file`, {
    responseType: 'blob',
    timeout: 0,
  });

  const safeName = (list.name || `list_${list.id}`).replace(/[^\w\-.]+/g, '_').slice(0, 80);
  triggerBlobDownload(new Blob([response.data], { type: 'application/zip' }), `${safeName}_clips.zip`);

  return {
    status,
    ok: response.headers?.['x-export-ok'],
    failed: response.headers?.['x-export-failed'],
    randomSample: response.headers?.['x-export-random-sample'] === '1',
    totalInList: response.headers?.['x-export-total-in-list'],
  };
}

export { parseErrorDetail };
