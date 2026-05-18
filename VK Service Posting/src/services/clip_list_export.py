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


def _safe_archive_basename(name: str) -> str:
    base = re.sub(r"[^\w\-.]+", "_", (name or "clips").strip())
    return base[:80] or "clips"


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


def count_downloadable_clips(clips: list[ClipExportPayload]) -> int:
    return sum(1 for c in clips if _is_downloadable_url(c.files))


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
) -> bytes:
    """Мгновенный ZIP со ссылками — скачивание с ПК (CDN часто не отдаёт файлы серверу)."""
    url_lines: list[str] = []
    html_items: list[str] = []

    for idx, clip in enumerate(clips, start=1):
        url = (clip.files or "").strip()
        if not _is_downloadable_url(url):
            continue
        ext = _ext_from_url(url)
        fname = f"clip_{clip.vk_group_id}_{clip.vk_id}_{idx}{ext}"
        url_lines.append(url)
        safe_url = html.escape(url, quote=True)
        safe_fname = html.escape(fname)
        html_items.append(
            f'<li><a href="{safe_url}" download="{safe_fname}">{safe_fname}</a></li>',
        )

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
            "Ссылки VK CDN часто привязаны к IP и сроку действия.",
            "Сервер при ZIP-скачивании получает 400 — это нормально.",
            "Скачивайте с вашего ПК:",
            "  • откройте index.html в браузере и сохраняйте файлы;",
            "  • или urls.txt в IDM / Free Download Manager / aria2c.",
            "",
            "Чтобы обновить ссылки — заново «Пополните» базу в V1.",
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

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("readme.txt", "\n".join(readme).encode("utf-8"))
        zf.writestr("urls.txt", "\n".join(url_lines).encode("utf-8"))
        zf.writestr("index.html", html_page.encode("utf-8"))
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
) -> tuple[int, str, str, Path | None, str | None]:
    """idx, entry_name, url, temp_path|None, error|None"""
    url = (clip.files or "").strip()
    if not _is_downloadable_url(url):
        return idx, "", url, None, "no_url"

    ext = _ext_from_url(url)
    entry_name = f"clips/clip_{clip.vk_group_id}_{clip.vk_id}_{idx}{ext}"
    session = requests.Session()
    session.headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; VKPosting/1.0)")
    try:
        return idx, entry_name, url, _download_url_to_temp_file(session, url), None
    except Exception as e:
        return idx, entry_name, url, None, str(e).replace(";", ",")
    finally:
        session.close()


def build_clip_list_zip_archive(
    clip_list_name: str,
    clips: list[ClipExportPayload],
    *,
    progress_cb: Optional[ProgressCallback] = None,
    total_in_list: Optional[int] = None,
    random_sample: bool = False,
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
                pool.submit(_download_clip_to_temp, clip, idx)
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
        raise ValueError(
            "Не удалось скачать ни одного клипа. Ссылки VK могли устареть — пополните базу заново.",
        )

    if progress_cb:
        progress_cb(total, total, "done")

    return zip_path, ok_count, fail_count
