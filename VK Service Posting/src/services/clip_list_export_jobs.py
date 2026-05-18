import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from src.services.clip_list_export import (
    ClipExportPayload,
    build_clip_list_zip_archive,
    load_export_download_context,
    pick_clips_for_export,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]

JOB_ROOT = Path(os.environ.get("CLIP_EXPORT_JOB_DIR", "")).expanduser()
if not str(JOB_ROOT):
    import tempfile

    JOB_ROOT = Path(tempfile.gettempdir()) / "vk_clip_export_jobs"


@dataclass
class ClipExportJob:
    job_id: str
    user_id: int
    clip_list_id: int
    status: str = "pending"
    current: int = 0
    total: int = 0
    phase: str = "queued"
    zip_path: Optional[str] = None
    filename: str = "clips.zip"
    error: Optional[str] = None
    total_in_list: int = 0
    export_count: int = 0
    random_sample: bool = False
    ok_count: int = 0
    fail_count: int = 0


_jobs: dict[str, ClipExportJob] = {}
_lock = threading.Lock()


def _job_meta_path(job_id: str) -> Path:
    return JOB_ROOT / f"{job_id}.json"


def _persist_job(job: ClipExportJob) -> None:
    JOB_ROOT.mkdir(parents=True, exist_ok=True)
    data = asdict(job)
    _job_meta_path(job.job_id).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _load_job_from_disk(job_id: str) -> Optional[ClipExportJob]:
    path = _job_meta_path(job_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ClipExportJob(**data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("clip export job meta corrupt %s: %s", job_id, e)
        return None


def _set_job(job_id: str, **kwargs: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            job = _load_job_from_disk(job_id)
        if not job:
            return
        for key, value in kwargs.items():
            setattr(job, key, value)
        _jobs[job_id] = job
        _persist_job(job)


def get_job(job_id: str, user_id: int) -> Optional[ClipExportJob]:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            job = _load_job_from_disk(job_id)
            if job:
                _jobs[job_id] = job
        if not job or job.user_id != user_id:
            return None
        return job


def _cleanup_job_files(job: ClipExportJob) -> None:
    if job.zip_path:
        try:
            os.unlink(job.zip_path)
        except OSError:
            pass
    try:
        _job_meta_path(job.job_id).unlink(missing_ok=True)
    except OSError:
        pass


def remove_job(job_id: str) -> None:
    with _lock:
        job = _jobs.pop(job_id, None)
        if not job:
            job = _load_job_from_disk(job_id)
    if job:
        _cleanup_job_files(job)


def start_export_job(
    *,
    user_id: int,
    clip_list_id: int,
    clip_list_name: str,
    clips: list,
    safe_filename: str,
) -> ClipExportJob:
    export_clips, random_sample, total_in_list = pick_clips_for_export(clips)
    payloads = [
        ClipExportPayload(
            id=c.id,
            vk_group_id=c.vk_group_id,
            vk_id=c.vk_id,
            files=c.files,
        )
        for c in export_clips
    ]

    job_id = uuid.uuid4().hex
    job = ClipExportJob(
        job_id=job_id,
        user_id=user_id,
        clip_list_id=clip_list_id,
        status="running",
        current=0,
        total=len(payloads),
        phase="starting",
        filename=safe_filename,
        total_in_list=total_in_list,
        export_count=len(payloads),
        random_sample=random_sample,
    )

    with _lock:
        _jobs[job_id] = job
        _persist_job(job)

    def progress_cb(current: int, total: int, phase: str) -> None:
        _set_job(job_id, current=current, total=total, phase=phase, status="running")

    def worker() -> None:
        try:
            group_ids = {c.vk_group_id for c in payloads if c.vk_group_id}
            download_context = load_export_download_context(user_id, group_ids)
            zip_path, ok_count, fail_count = build_clip_list_zip_archive(
                clip_list_name,
                payloads,
                progress_cb=progress_cb,
                total_in_list=total_in_list,
                random_sample=random_sample,
                download_context=download_context,
            )
            _set_job(
                job_id,
                status="done",
                zip_path=str(zip_path),
                ok_count=ok_count,
                fail_count=fail_count,
                current=len(payloads),
                phase="ready",
            )
            logger.info(
                "clip export job %s done ok=%s failed=%s zip=%s",
                job_id,
                ok_count,
                fail_count,
                zip_path,
            )
        except ValueError as e:
            _set_job(job_id, status="failed", error=str(e), phase="failed")
            logger.warning("clip export job %s failed: %s", job_id, e)
        except Exception as e:
            logger.exception("clip export job %s failed", job_id)
            _set_job(job_id, status="failed", error=str(e), phase="failed")

    threading.Thread(target=worker, daemon=True).start()
    return job


def job_to_status_dict(job: ClipExportJob) -> dict:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "current": job.current,
        "total": job.total,
        "phase": job.phase,
        "error": job.error,
        "total_in_list": job.total_in_list,
        "export_count": job.export_count,
        "random_sample": job.random_sample,
        "ok_count": job.ok_count,
        "fail_count": job.fail_count,
        "filename": job.filename,
    }
