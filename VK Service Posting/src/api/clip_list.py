import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, func
from sqlalchemy.orm import aliased

from src.api.dependencies import DataBaseDep, UserIdDep
from src.models import VKClipOrm, ClipListOrm
from src.schemas.clip_list import ClipListAddRequest, ClipListAdd, ClipListUpdate
from src.services.clip_list_export import (
    _safe_archive_basename,
    attachment_content_disposition,
    build_links_manifest_zip,
    clips_to_payloads,
    count_downloadable_clips,
    load_export_download_context,
    pick_clips_for_export,
)
from src.services.clip_list_export_jobs import get_job, job_to_status_dict, remove_job, start_export_job
from src.services.live_log import livelogadd
from src.services.vk_group_service import VKGroupSourceService

router = APIRouter(prefix="/users/{user_id}/clip_list", tags=["Список клипов"])

@router.post("/add", summary="Добавить список клипов")
async def create(clip_list_request: ClipListAddRequest, database: DataBaseDep, user_id: UserIdDep):
    clip_list_add = ClipListAdd(
        user_id=user_id,
        name=clip_list_request.name,
        parse_status="",
        task_id=""
    )
    new_clip_list = await database.clip_list.add(clip_list_add)
    await database.commit()
    return {"status": "OK", "detail": new_clip_list}

@router.get("/get_all", summary="Получить все списки клипов пользователя")
async def read_all(database: DataBaseDep, user_id: UserIdDep):
    subq = (
        select(VKClipOrm.clip_list_id.label("clip_list_id"),
               func.count(VKClipOrm.id).label("cnt"))
        .group_by(VKClipOrm.clip_list_id)
        .subquery()
    )

    stmt = (
        select(
            ClipListOrm.id,
            ClipListOrm.user_id,
            ClipListOrm.name,
            ClipListOrm.parse_status,
            ClipListOrm.task_id,
            func.coalesce(subq.c.cnt, 0).label("count"),
        )
        .outerjoin(subq, subq.c.clip_list_id == ClipListOrm.id)
        .where(ClipListOrm.user_id == int(user_id))
        .order_by(ClipListOrm.id)
    )

    rows = await database.session.execute(stmt)
    result = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "name": r.name,
            "parse_status": r.parse_status,
            "task_id": r.task_id,
            "count": r.count,
        }
        for r in rows
    ]
    return result

@router.get("/get/{clip_list_id}", summary="Получить конкретный список клипов пользователя")
async def read(clip_list_id: int, database: DataBaseDep, user_id: UserIdDep):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")
    return clip_list

@router.post(
    "/get/{clip_list_id}/download/start",
    summary="Начать формирование ZIP (до 500 клипов, при большем списке — случайная выборка)",
)
async def start_clip_list_download(
    clip_list_id: int,
    database: DataBaseDep,
    user_id: UserIdDep,
):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id, user_id=user_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")

    clips = await database.vk_clip.get_all_filtered(clip_list_id=clip_list_id, user_id=user_id)
    if not clips:
        raise HTTPException(status_code=400, detail="В списке нет клипов для скачивания")

    filename = f"{_safe_archive_basename(clip_list.name)}_clips.zip"
    job = start_export_job(
        user_id=user_id,
        clip_list_id=clip_list_id,
        clip_list_name=clip_list.name,
        clips=clips,
        safe_filename=filename,
    )
    return job_to_status_dict(job)


@router.get(
    "/get/{clip_list_id}/download/links",
    summary="Скачать ZIP со ссылками на клипы (мгновенно, загрузка с ПК)",
)
async def download_clip_list_links(
    clip_list_id: int,
    database: DataBaseDep,
    user_id: UserIdDep,
):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id, user_id=user_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")

    clips = await database.vk_clip.get_all_filtered(clip_list_id=clip_list_id, user_id=user_id)
    if not clips:
        raise HTTPException(status_code=400, detail="В списке нет клипов для скачивания")

    export_clips, random_sample, total_in_list = pick_clips_for_export(clips)
    payloads = clips_to_payloads(export_clips)
    group_ids = {c.vk_group_id for c in payloads if c.vk_group_id}
    export_ctx = load_export_download_context(user_id, group_ids)
    group_map = export_ctx.vk_public_group_id_by_db_id if export_ctx else {}
    if count_downloadable_clips(payloads, group_map) == 0:
        raise HTTPException(status_code=400, detail="Нет ссылок на видео в выбранных клипах")
    zip_bytes = build_links_manifest_zip(
        clip_list.name,
        payloads,
        total_in_list=total_in_list,
        random_sample=random_sample,
        vk_public_group_id_by_db_id=group_map,
    )
    filename = f"{_safe_archive_basename(clip_list.name)}_links.zip"
    headers = {
        "Content-Disposition": attachment_content_disposition(filename),
        "X-Export-Total-In-List": str(total_in_list),
        "X-Export-Random-Sample": "1" if random_sample else "0",
        "X-Export-Count": str(len(payloads)),
    }
    return Response(content=zip_bytes, media_type="application/zip", headers=headers)


@router.get(
    "/download/export/{job_id}",
    summary="Статус формирования ZIP",
)
async def clip_list_download_status(
    job_id: str,
    user_id: UserIdDep,
):
    job = get_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job_to_status_dict(job)


@router.get(
    "/download/export/{job_id}/file",
    summary="Скачать готовый ZIP",
)
async def clip_list_download_file(
    job_id: str,
    user_id: UserIdDep,
    background_tasks: BackgroundTasks,
):
    job = get_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    if job.status == "failed":
        raise HTTPException(status_code=400, detail=job.error or "Ошибка формирования архива")
    if job.status != "done" or not job.zip_path:
        raise HTTPException(status_code=409, detail="Архив ещё формируется")

    zip_path = Path(job.zip_path)
    if not zip_path.is_file():
        raise HTTPException(status_code=404, detail="Файл архива не найден")

    def _cleanup() -> None:
        remove_job(job_id)

    background_tasks.add_task(_cleanup)

    headers = {
        "X-Export-Ok": str(job.ok_count),
        "X-Export-Failed": str(job.fail_count),
        "X-Export-Total-In-List": str(job.total_in_list),
        "X-Export-Random-Sample": "1" if job.random_sample else "0",
    }

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=job.filename,
        headers=headers,
    )


@router.get("/get/{clip_list_id}/tasks_status", summary="Получить списки тасок по списку клипов пользователя")
async def get_all_tasks_status(
    database: DataBaseDep,
    user_id: UserIdDep,
    clip_list_id : int,
):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")

    detail = await VKGroupSourceService(database).get_tasks_status(user_id, clip_list_id)
    return {"status": "OK", "detail": detail}


@router.put("/edit/{clip_list_id}", summary="Редактировать конкретный список клипов пользователя")
async def update(clip_list_id: int, update_data: ClipListUpdate, database: DataBaseDep, user_id: UserIdDep):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")
    clip_list_edited = await database.clip_list.edit(update_data, exclude_unset=True, id=clip_list_id)
    await database.commit()
    return {"status": "OK", "detail": clip_list_edited}

@router.delete("/delete/{clip_list_id}", summary="Удалить конкретный список клипов пользователя")
async def delete(clip_list_id: int, database: DataBaseDep, user_id: UserIdDep):
    clip_list = await database.clip_list.get_one_or_none(id=clip_list_id)
    if not clip_list:
        raise HTTPException(status_code=404, detail="Список клипов не найден")
    celery_tasks = await database.celery_task.get_all_filtered(clip_list_id=clip_list_id)
    task_count = len(celery_tasks)
    for task in celery_tasks:
        await database.celery_task.delete(id=task.id)
    await database.commit()

    clips = await database.vk_clip.get_all_filtered(clip_list_id=clip_list_id)
    clip_count = len(clips)
    for clip in clips:
        await database.vk_clip.delete(id=clip.id)
    await database.commit()

    await database.clip_list.delete(id=clip_list_id)
    await database.commit()
    await livelogadd(
        database,
        user_id,
        "source",
        "Список клипов удалён",
        f"clip_list_id={clip_list_id}; clips={clip_count}; tasks={task_count}",
    )
    return {"status": "OK"}
