import html
import io
import logging
import os
import random
import re
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests
from sqlalchemy import select

from src.celery_app.celery_db import SyncSessionLocal
from src.models import VKAccountOrm
from src.models.proxy import ProxyOrm
from src.models.vk_group import VKGroupOrm
from src.vk_api_methods.vk_auth import get_new_token_request
from src.vk_api_methods.vk_posting import (
    download_clip_by_direct_url,
    download_clip_by_url,
    get_clip_info,
)

logger = logging.getLogger(__name__)

MAX_CLIPS_PER_EXPORT = 500
MAX_CLIP_FILE_BYTES = 150 * 1024 * 1024
DOWNLOAD_TIMEOUT_SEC = (10, 45)
DOWNLOAD_CHUNK = 1024 * 256
PARALLEL_DOWNLOAD_WORKERS = 8

ProgressCallback = Callable[[int, int, str], None]


@dataclass(frozen=True)
class ClipExportPayload:
    id: int
    vk_group_id: int
    vk_id: int
    files: str


@dataclass(frozen=True)
class ClipExportDownloadContext:
    token: str
    cookies: str
    proxy: str | None
    vk_public_group_id_by_db_id: dict[int, int]


def _best_quality_key(files: dict) -> str | None:
    best_k = None
    best_res = -1
    for k in files:
        m = re.match(r"^mp4_(\d+)$", k)
        if not m:
            continue
        res = int(m.group(1))
        if res > best_res:
            best_res = res
            best_k = k
    if best_k:
        return best_k
    if "hls" in files:
        return "hls"
    return next(iter(files), None)


def _files_field_to_url(files) -> str | None:
    if isinstance(files, str):
        t = files.strip()
        if t.lower().startswith(("http://", "https://")):
            return t
        return None
    if isinstance(files, dict) and files:
        key = _best_quality_key(files)
        if key:
            url = files.get(key)
            if isinstance(url, str) and url.strip():
                return url.strip()
    return None


def load_export_download_context(
    user_id: int,
    vk_group_db_ids: set[int],
) -> ClipExportDownloadContext | None:
    with SyncSessionLocal() as session:
        main = session.execute(
            select(VKAccountOrm).where(
                VKAccountOrm.account_type == "main",
                VKAccountOrm.user_id == user_id,
            ),
        ).scalar_one_or_none()
        if not main or not (main.token or "").strip():
            return None

        proxy_http = None
        if main.proxy_id:
            proxy_row = session.get(ProxyOrm, main.proxy_id)
            if proxy_row:
                proxy_http = proxy_row.http

        group_map: dict[int, int] = {}
        if vk_group_db_ids:
            rows = session.execute(
                select(VKGroupOrm.id, VKGroupOrm.vk_group_id).where(
                    VKGroupOrm.id.in_(vk_group_db_ids),
                ),
            ).all()
            group_map = {int(r[0]): int(r[1]) for r in rows}

        return ClipExportDownloadContext(
            token=main.token.strip(),
            cookies=main.cookies or "",
            proxy=proxy_http,
            vk_public_group_id_by_db_id=group_map,
        )


def _vk_owner_id(context: ClipExportDownloadContext, clip: ClipExportPayload) -> int | None:
    pub = context.vk_public_group_id_by_db_id.get(clip.vk_group_id)
    if not pub:
        return None
    return -int(pub)


def _refresh_clip_download_url(
    context: ClipExportDownloadContext,
    clip: ClipExportPayload,
) -> str | None:
    owner_id = _vk_owner_id(context, clip)
    if owner_id is None:
        return None
    token = get_new_token_request(context.token, context.cookies, context.proxy) or context.token
    info = get_clip_info(owner_id, clip.vk_id, token, context.proxy)
    return _files_field_to_url(info.get("files"))


def _safe_archive_basename(name: str) -> str:
    """ASCII-only: Starlette кодирует заголовки как latin-1."""
    base = re.sub(r"[^a-zA-Z0-9_.-]+", "_", (name or "clips").strip())
    base = re.sub(r"_+", "_", base).strip("._")
    return base[:80] or "clips"


def attachment_content_disposition(filename: str) -> str:
    return f'attachment; filename="{filename}"'


def _ext_from_url(url: str) -> str:
    low = url.lower().split("?", 1)[0]
    if low.endswith(".webm"):
        return ".webm"
    if low.endswith(".mov"):
        return ".mov"
    return ".mp4"


def _is_downloadable_url(files: str | None) -> bool:
    if not files or not isinstance(files, str):
        return False
    t = files.strip()
    return t.lower().startswith(("http://", "https://"))


def pick_clips_for_export(clips: list, max_count: int = MAX_CLIPS_PER_EXPORT) -> tuple[list, bool, int]:
    total_in_list = len(clips)
    if total_in_list <= max_count:
        return clips, False, total_in_list
    return random.sample(clips, max_count), True, total_in_list


def count_downloadable_clips(
    clips: list[ClipExportPayload],
    vk_public_group_id_by_db_id: dict[int, int] | None = None,
) -> int:
    group_map = vk_public_group_id_by_db_id or {}
    return sum(
        1
        for c in clips
        if _is_downloadable_url(c.files) or c.vk_group_id in group_map
    )


def clips_to_payloads(clips: list) -> list[ClipExportPayload]:
    return [
        ClipExportPayload(
            id=c.id,
            vk_group_id=c.vk_group_id,
            vk_id=c.vk_id,
            files=c.files,
        )
        for c in clips
    ]


def build_links_manifest_zip(
    clip_list_name: str,
    clips: list[ClipExportPayload],
    *,
    total_in_list: int,
    random_sample: bool,
    vk_public_group_id_by_db_id: dict[int, int] | None = None,
) -> bytes:
    """Мгновенный ZIP со ссылками — скачивание с ПК (CDN часто не отдаёт файлы серверу)."""
    group_map = vk_public_group_id_by_db_id or {}
    url_lines: list[str] = []
    vk_page_lines: list[str] = []
    html_items: list[str] = []

    for idx, clip in enumerate(clips, start=1):
        url = (clip.files or "").strip()
        pub_id = group_map.get(clip.vk_group_id)
        vk_page = f"https://vk.com/video{-pub_id}_{clip.vk_id}" if pub_id else None
        if vk_page:
            vk_page_lines.append(vk_page)

        if not _is_downloadable_url(url):
            if vk_page:
                safe_page = html.escape(vk_page, quote=True)
                fname = f"clip_{clip.vk_id}_{idx}.mp4"
                html_items.append(
                    f'<li><a href="{safe_page}">{html.escape(fname)} (страница VK)</a></li>',
                )
            continue
        ext = _ext_from_url(url)
        fname = f"clip_{clip.vk_group_id}_{clip.vk_id}_{idx}{ext}"
        url_lines.append(url)
        safe_url = html.escape(url, quote=True)
        safe_fname = html.escape(fname)
        item = f'<li><a href="{safe_url}" download="{safe_fname}">{safe_fname}</a>'
        if vk_page:
            item += f' · <a href="{html.escape(vk_page, quote=True)}">VK</a>'
        html_items.append(f"{item}</li>")

    readme = [
        f"Список: {clip_list_name}",
        f"Ссылок в файле: {len(url_lines)}",
        f"Всего в базе: {total_in_list}",
    ]
    if random_sample:
        readme.append(
            f"Выборка: случайные {len(clips)} из {total_in_list} (лимит {MAX_CLIPS_PER_EXPORT}).",
        )
    readme.extend(
        [
            "",
            "urls.txt — прямые CDN (могут протухнуть).",
            "vk_pages.txt — страницы VK для загрузки с ПК.",
            "",
            "Windows: папка windows_downloader\\ — запустите Скачать_клипы.bat",
            "(перетащите vk_pages.txt на bat) — видео в папке clips\\",
            "",
            "Чтобы обновить CDN-ссылки — пополните базу в V1.",
        ],
    )

    html_page = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>{html.escape(clip_list_name)} — ссылки на клипы</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 1.5rem; }}
a {{ word-break: break-all; }}
li {{ margin: 0.4rem 0; }}
</style></head><body>
<h1>{html.escape(clip_list_name)}</h1>
<p>Откройте ссылки с <strong>этого компьютера</strong>. Для массовой загрузки используйте <code>urls.txt</code>.</p>
<ol>
{''.join(html_items)}
</ol>
</body></html>"""

    tool_dir = Path(__file__).resolve().parents[2] / "tools" / "vk_pages_downloader"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("readme.txt", "\n".join(readme).encode("utf-8"))
        zf.writestr("urls.txt", "\n".join(url_lines).encode("utf-8"))
        if vk_page_lines:
            zf.writestr("vk_pages.txt", "\n".join(vk_page_lines).encode("utf-8"))
        zf.writestr("index.html", html_page.encode("utf-8"))
        if tool_dir.is_dir():
            for name in ("download_vk_clips.py", "Скачать_клипы.bat", "requirements.txt"):
                tool_file = tool_dir / name
                if tool_file.is_file():
                    zf.write(tool_file, arcname=f"windows_downloader/{name}")
    return buf.getvalue()


def _download_url_to_temp_file(session: requests.Session, url: str) -> Path:
    suffix = _ext_from_url(url)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = Path(tmp.name)
    size = 0
    try:
        with session.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT_SEC) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=DOWNLOAD_CHUNK):
                if not chunk:
                    continue
                tmp.write(chunk)
                size += len(chunk)
                if size > MAX_CLIP_FILE_BYTES:
                    raise RuntimeError("Файл больше 150 МБ")
        tmp.close()
        if size < 1024:
            raise RuntimeError("Пустой или слишком маленький файл")
        return tmp_path
    except Exception:
        tmp.close()
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _download_clip_to_temp(
    clip: ClipExportPayload,
    idx: int,
    context: ClipExportDownloadContext | None = None,
    *,
    allow_ytdlp_fallback: bool = False,
) -> tuple[int, str, str, Path | None, str | None]:
    """Как workerpost: CDN → свежий URL через video.get → yt-dlp по странице VK."""
    stored = (clip.files or "").strip()
    ext = _ext_from_url(stored) if _is_downloadable_url(stored) else ".mp4"
    entry_name = f"clips/clip_{clip.vk_group_id}_{clip.vk_id}_{idx}{ext}"
    owner_id = _vk_owner_id(context, clip) if context else None

    urls_to_try: list[str] = []
    if _is_downloadable_url(stored):
        urls_to_try.append(stored)
    if context:
        try:
            fresh = _refresh_clip_download_url(context, clip)
            if fresh and fresh not in urls_to_try:
                urls_to_try.append(fresh)
        except Exception as e:
            logger.debug("clip %s refresh url failed: %s", clip.id, e)

    last_err = "no_url"
    for url in urls_to_try:
        try:
            if owner_id is not None:
                path_str = download_clip_by_direct_url(
                    url, context.proxy, owner_id, clip.vk_id,
                )
            else:
                session = requests.Session()
                session.headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; VKPosting/1.0)")
                try:
                    path_str = str(_download_url_to_temp_file(session, url))
                finally:
                    session.close()
            return idx, entry_name, url, Path(path_str), None
        except Exception as e:
            last_err = str(e).replace(";", ",")
            logger.debug("clip %s direct download failed: %s", clip.id, e)

    if allow_ytdlp_fallback and context and owner_id is not None:
        page_url = f"https://vk.com/video{owner_id}_{clip.vk_id}"
        try:
            path_str = download_clip_by_url(page_url, owner_id, clip.vk_id)
            return idx, entry_name, page_url, Path(path_str), None
        except Exception as e:
            last_err = str(e).replace(";", ",")
            logger.warning("clip export yt-dlp failed id=%s: %s", clip.id, e)

    return idx, entry_name, stored or "", None, last_err


def build_clip_list_zip_archive(
    clip_list_name: str,
    clips: list[ClipExportPayload],
    *,
    progress_cb: Optional[ProgressCallback] = None,
    total_in_list: Optional[int] = None,
    random_sample: bool = False,
    download_context: ClipExportDownloadContext | None = None,
) -> tuple[Path, int, int]:
    """
    Скачивает клипы на диск по одному и пишет в ZIP (без хранения всех файлов в RAM).
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    zip_path = Path(tmp.name)
    tmp.close()

    ok_count = 0
    fail_count = 0
    total = len(clips)
    manifest_lines = ["clip_db_id;vk_group_id;vk_id;url;status\n"]

    if progress_cb:
        progress_cb(0, total, "preparing")

    clip_by_idx = {i: c for i, c in enumerate(clips, start=1)}

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        completed = 0
        with ThreadPoolExecutor(max_workers=PARALLEL_DOWNLOAD_WORKERS) as pool:
            futures = [
                pool.submit(
                    _download_clip_to_temp,
                    clip,
                    idx,
                    download_context,
                    allow_ytdlp_fallback=False,
                )
                for idx, clip in clip_by_idx.items()
            ]
            for future in as_completed(futures):
                idx, entry_name, url, temp_path, err = future.result()
                clip = clip_by_idx[idx]
                completed += 1
                if progress_cb:
                    progress_cb(completed, total, f"clip {completed}/{total}")

                if err:
                    fail_count += 1
                    if err != "no_url":
                        logger.warning("clip export failed id=%s: %s", clip.id, err)
                    manifest_lines.append(
                        f"{clip.id};{clip.vk_group_id};{clip.vk_id};{url};{err}\n",
                    )
                    continue

                try:
                    zf.write(temp_path, arcname=entry_name)
                    ok_count += 1
                    manifest_lines.append(f"{clip.id};{clip.vk_group_id};{clip.vk_id};{url};ok\n")
                except Exception as e:
                    fail_count += 1
                    logger.warning("clip export zip write failed id=%s: %s", clip.id, e)
                    manifest_lines.append(
                        f"{clip.id};{clip.vk_group_id};{clip.vk_id};{url};{str(e).replace(';', ',')}\n",
                    )
                finally:
                    if temp_path:
                        try:
                            temp_path.unlink(missing_ok=True)
                        except OSError:
                            pass

        if progress_cb:
            progress_cb(total, total, "packing")

        zf.writestr("manifest.csv", "".join(manifest_lines).encode("utf-8-sig"))
        readme_lines = [
            f"Список: {clip_list_name}",
            f"Успешно: {ok_count}",
            f"Ошибки: {fail_count}",
        ]
        if total_in_list is not None:
            readme_lines.append(f"Всего в базе: {total_in_list}")
        if random_sample:
            readme_lines.append(
                f"В архив попали случайные {total} клипов (лимит {MAX_CLIPS_PER_EXPORT} за раз).",
            )
        readme_lines.append("CDN-ссылки могут не работать с IP сервера — используйте «Ссылки» для скачивания с ПК.")
        readme_lines.append("Подробности — manifest.csv")
        zf.writestr("readme.txt", "\n".join(readme_lines).encode("utf-8"))

    if ok_count == 0:
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
        hint = (
            "Не удалось скачать ни одного клипа. Проверьте main-аккаунт, прокси и пополните базу."
            if download_context
            else "Не удалось скачать ни одного клипа. Добавьте main-аккаунт или используйте «Ссылки»."
        )
        raise ValueError(hint)

    if progress_cb:
        progress_cb(total, total, "done")

    return zip_path, ok_count, fail_count
