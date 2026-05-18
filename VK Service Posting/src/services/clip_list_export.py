import logging
import re
import tempfile
import zipfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

MAX_CLIPS_PER_EXPORT = 500
DOWNLOAD_TIMEOUT_SEC = 120
DOWNLOAD_CHUNK = 1024 * 256


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


def build_clip_list_zip_archive(clip_list_name: str, clips: list) -> tuple[Path, int, int]:
    """
    Скачивает клипы по URL из поля files и упаковывает во временный ZIP.
    Возвращает (путь к zip, успешно, с ошибкой).
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    zip_path = Path(tmp.name)
    tmp.close()

    ok_count = 0
    fail_count = 0
    manifest_lines = ["clip_db_id;vk_group_id;vk_id;url;status\n"]

    session = requests.Session()
    session.headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; VKPosting/1.0)")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, clip in enumerate(clips, start=1):
            url = (clip.files or "").strip()
            if not _is_downloadable_url(url):
                fail_count += 1
                manifest_lines.append(f"{clip.id};{clip.vk_group_id};{clip.vk_id};;no_url\n")
                continue

            ext = _ext_from_url(url)
            entry_name = f"clips/clip_{clip.vk_group_id}_{clip.vk_id}_{idx}{ext}"

            try:
                with session.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT_SEC) as resp:
                    resp.raise_for_status()
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in resp.iter_content(chunk_size=DOWNLOAD_CHUNK):
                        if not chunk:
                            continue
                        chunks.append(chunk)
                        size += len(chunk)
                        if size > 500 * 1024 * 1024:
                            raise RuntimeError("Файл больше 500 МБ")
                    if size < 1024:
                        raise RuntimeError("Пустой или слишком маленький файл")
                    zf.writestr(entry_name, b"".join(chunks))
                ok_count += 1
                manifest_lines.append(f"{clip.id};{clip.vk_group_id};{clip.vk_id};{url};ok\n")
            except Exception as e:
                fail_count += 1
                logger.warning("clip export failed id=%s: %s", clip.id, e)
                manifest_lines.append(
                    f"{clip.id};{clip.vk_group_id};{clip.vk_id};{url};{str(e).replace(';', ',')}\n",
                )

        zf.writestr("manifest.csv", "".join(manifest_lines).encode("utf-8-sig"))
        readme = (
            f"Список: {clip_list_name}\n"
            f"Успешно: {ok_count}\n"
            f"Ошибки: {fail_count}\n"
            "Подробности — manifest.csv\n"
        )
        zf.writestr("readme.txt", readme.encode("utf-8"))

    if ok_count == 0:
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ValueError(
            "Не удалось скачать ни одного клипа. Ссылки VK могли устареть — пополните базу заново.",
        )

    return zip_path, ok_count, fail_count
