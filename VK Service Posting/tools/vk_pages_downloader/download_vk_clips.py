#!/usr/bin/env python3
"""
Скачивание клипов VK с ПК по vk_pages.txt / urls.txt (архив «Ссылки»).
"""

from __future__ import annotations

import argparse
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

try:
    import yt_dlp
except ImportError:
    yt_dlp = None  # type: ignore

VK_PAGE_RE = re.compile(
    r"https?://(?:[\w.-]+\.)?vk\.com/video(-?\d+)_(\d+)",
    re.IGNORECASE,
)

ProgressCallback = Callable[["DownloadProgress"], None]


@dataclass
class DownloadConfig:
    input_path: Path
    output_dir: Path | None = None
    workers: int = 3
    proxy: str | None = None
    cookies_file: str | None = None
    source: str = "auto"


@dataclass
class DownloadProgress:
    done: int = 0
    total: int = 0
    ok: int = 0
    fail: int = 0
    message: str = ""
    finished: bool = False
    success: bool = False
    errors_path: Path | None = None
    output_dir: Path | None = None


def read_url_list(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def vk_ids_from_url(url: str) -> tuple[str, str] | None:
    m = VK_PAGE_RE.search(url)
    if not m:
        return None
    return m.group(1), m.group(2)


def load_urls(input_path: Path, prefer: str = "auto") -> tuple[list[str], str]:
    if input_path.is_dir():
        vk_file = input_path / "vk_pages.txt"
        urls_file = input_path / "urls.txt"
        parent_vk = input_path.parent / "vk_pages.txt"
        if prefer == "urls" and urls_file.is_file():
            return read_url_list(urls_file), "urls"
        if vk_file.is_file():
            return read_url_list(vk_file), "vk_pages"
        if parent_vk.is_file() and input_path.name.lower() == "windows_downloader":
            return read_url_list(parent_vk), "vk_pages"
        if urls_file.is_file():
            return read_url_list(urls_file), "urls"
        raise FileNotFoundError(f"В папке нет vk_pages.txt: {input_path}")

    if not input_path.is_file():
        raise FileNotFoundError(str(input_path))

    name = input_path.name.lower()
    if prefer == "vk_pages" or (prefer == "auto" and "vk_page" in name):
        return read_url_list(input_path), "vk_pages"
    if prefer == "urls" or (prefer == "auto" and name == "urls.txt"):
        return read_url_list(input_path), "urls"
    urls = read_url_list(input_path)
    if urls and VK_PAGE_RE.search(urls[0]):
        return urls, "vk_pages"
    return urls, "urls"


def resolve_output_dir(config: DownloadConfig) -> Path:
    if config.output_dir:
        return config.output_dir
    inp = config.input_path
    base = inp.parent if inp.is_file() else inp
    return base / "clips"


def download_vk_page(
    url: str,
    index: int,
    out_dir: Path,
    proxy: str | None,
    cookies_file: str | None,
) -> tuple[bool, str, str]:
    if yt_dlp is None:
        return False, url, "yt-dlp не установлен"

    ids = vk_ids_from_url(url)
    if not ids:
        return False, url, "не ссылка vk.com/video"

    owner_id, video_id = ids
    prefix = f"clip_{owner_id}_{video_id}"
    existing = list(out_dir.glob(f"{prefix}.*"))
    if existing:
        return True, url, f"уже есть: {existing[0].name}"

    outtmpl = str(out_dir / f"{prefix}.%(ext)s")
    ydl_opts: dict = {
        "outtmpl": outtmpl,
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "socket_timeout": 30,
    }
    if proxy:
        ydl_opts["proxy"] = proxy
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        saved = list(out_dir.glob(f"{prefix}.*"))
        if saved:
            return True, url, saved[0].name
        return False, url, "файл не появился после yt-dlp"
    except Exception as e:
        return False, url, str(e).replace("\n", " ")


def download_cdn_url(
    url: str,
    index: int,
    out_dir: Path,
    proxy: str | None,
) -> tuple[bool, str, str]:
    import requests

    low = url.lower().split("?", 1)[0]
    ext = ".webm" if ".webm" in low else ".mp4"
    path = out_dir / f"cdn_{index:04d}{ext}"
    if path.is_file() and path.stat().st_size > 1024:
        return True, url, f"уже есть: {path.name}"

    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        with requests.get(url, stream=True, timeout=(15, 120), proxies=proxies) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(1024 * 256):
                    if chunk:
                        f.write(chunk)
        if path.stat().st_size < 1024:
            path.unlink(missing_ok=True)
            return False, url, "пустой ответ"
        return True, url, path.name
    except Exception as e:
        if path.exists():
            path.unlink(missing_ok=True)
        return False, url, str(e).replace("\n", " ")


def run_download(
    config: DownloadConfig,
    on_progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> DownloadProgress:
    if yt_dlp is None:
        raise RuntimeError("Установите yt-dlp: pip install yt-dlp")

    urls, mode = load_urls(config.input_path, config.source)
    if not urls:
        raise ValueError("Список ссылок пуст")

    out_dir = resolve_output_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    workers = max(1, min(config.workers, 8))
    cookies = config.cookies_file

    state = DownloadProgress(
        total=len(urls),
        output_dir=out_dir,
        errors_path=out_dir / "errors.txt",
    )
    state.errors_path.write_text("", encoding="utf-8")

    lock = threading.Lock()

    def emit(msg: str = "") -> None:
        if on_progress:
            on_progress(state)

    def worker(item: tuple[int, str]) -> tuple[bool, str, str]:
        if cancel_event and cancel_event.is_set():
            return False, item[1], "отменено"
        idx, url = item
        if mode == "vk_pages" or VK_PAGE_RE.search(url):
            return download_vk_page(url, idx, out_dir, config.proxy, cookies)
        return download_cdn_url(url, idx, out_dir, config.proxy)

    emit(f"Старт: {len(urls)} ссылок, потоков {workers}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, (i, u)): u for i, u in enumerate(urls, 1)}
        for future in as_completed(futures):
            if cancel_event and cancel_event.is_set():
                for f in futures:
                    f.cancel()
                break
            success, url, msg = future.result()
            with lock:
                state.done += 1
                if success:
                    state.ok += 1
                else:
                    state.fail += 1
                    if state.errors_path and msg != "отменено":
                        with open(state.errors_path, "a", encoding="utf-8") as ef:
                            ef.write(f"{url}\t{msg}\n")
                mark = "OK" if success else "FAIL"
                short = url if len(url) <= 60 else url[:57] + "..."
                state.message = f"[{state.done}/{state.total}] {mark} {msg} — {short}"
            emit()

    state.finished = True
    state.success = state.ok > 0 and not (cancel_event and cancel_event.is_set())
    if cancel_event and cancel_event.is_set():
        state.message = "Загрузка отменена"
    else:
        state.message = f"Готово: успешно {state.ok}, ошибок {state.fail}"
    emit()
    return state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Скачать клипы VK по vk_pages.txt",
    )
    parser.add_argument("-i", "--input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-w", "--workers", type=int, default=3)
    parser.add_argument("--proxy")
    parser.add_argument("--cookies", type=Path)
    parser.add_argument("--source", choices=("auto", "vk_pages", "urls"), default="auto")
    args = parser.parse_args()

    config = DownloadConfig(
        input_path=args.input or Path.cwd(),
        output_dir=args.output,
        workers=args.workers,
        proxy=args.proxy or None,
        cookies_file=str(args.cookies) if args.cookies else None,
        source=args.source,
    )

    try:
        result = run_download(
            config,
            on_progress=lambda p: print(p.message),
        )
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Ошибка: {e}")
        return 1

    if result.fail:
        print(f"Ошибки: {result.errors_path}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
