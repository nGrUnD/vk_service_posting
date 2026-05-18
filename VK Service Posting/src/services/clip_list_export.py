import logging
import os
import random
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests

logger = logging.getLogger(__name__)

MAX_CLIPS_PER_EXPORT = 500
MAX_CLIP_FILE_BYTES = 150 * 1024 * 1024
DOWNLOAD_TIMEOUT_SEC = 120
DOWNLOAD_CHUNK = 1024 * 256

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

    session = requests.Session()
    session.headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; VKPosting/1.0)")

    if progress_cb:
        progress_cb(0, total, "preparing")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, clip in enumerate(clips, start=1):
            url = (clip.files or "").strip()
            if not _is_downloadable_url(url):
                fail_count += 1
                manifest_lines.append(f"{clip.id};{clip.vk_group_id};{clip.vk_id};;no_url\n")
                continue

            ext = _ext_from_url(url)
            entry_name = f"clips/clip_{clip.vk_group_id}_{clip.vk_id}_{idx}{ext}"
            temp_video: Path | None = None

            try:
                temp_video = _download_url_to_temp_file(session, url)
                zf.write(temp_video, arcname=entry_name)
                ok_count += 1
                manifest_lines.append(f"{clip.id};{clip.vk_group_id};{clip.vk_id};{url};ok\n")
            except Exception as e:
                fail_count += 1
                logger.warning("clip export failed id=%s: %s", clip.id, e)
                manifest_lines.append(
                    f"{clip.id};{clip.vk_group_id};{clip.vk_id};{url};{str(e).replace(';', ',')}\n",
                )
            finally:
                if temp_video:
                    try:
                        temp_video.unlink(missing_ok=True)
                    except OSError:
                        pass

            if progress_cb:
                progress_cb(idx, total, f"clip {idx}/{total}")

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
