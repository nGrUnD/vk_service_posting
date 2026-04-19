import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from src.api.dependencies import DataBaseDep, UserIdDep
from src.schemas.workerpost import WorkerPostRequestAdd, WorkerPostUpdate
from src.services.workerpost_banner_service import (
    DEFAULT_BANNER_HEIGHT,
    DEFAULT_BANNER_WIDTH,
    DEFAULT_BANNER_X,
    DEFAULT_BANNER_Y,
)
from src.services.workerpost_service import WorkerPostService

router = APIRouter(prefix="/users/{user_id}/workerpost", tags=["VK Постинг"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKERPOST_BANNERS_DIR = PROJECT_ROOT / "storage" / "workerpost_banners"
ALLOWED_BANNER_SUFFIXES = {".mp4", ".mov", ".webm", ".m4v"}


def _delete_banner_file(file_path: str | None) -> None:
    if not file_path:
        return
    banner_path = Path(file_path)
    if banner_path.exists():
        banner_path.unlink()


async def _get_workerpost_or_404(database: DataBaseDep, workerpost_id: int, user_id: int):
    workerpost = await database.workerpost.get_one_or_none(id=workerpost_id, user_id=user_id)
    if not workerpost:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VK постинг не найден",
        )
    return workerpost


@router.get("/all", summary="Получить все VK постинги")
async def get_all_workerpost(
        user_id: UserIdDep,
        database: DataBaseDep,
):
    return await WorkerPostService(database).get_workpost_all(user_id)

@router.get("/{workerpost_id}", summary="Получить конкретный VK постинг")
async def get_workerpost(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    """Возвращает детальную информацию о конкретном VK аккаунте"""
    return await _get_workerpost_or_404(database, workerpost_id, user_id)


@router.get("/{workerpost_id}/banner", summary="Получить видео-баннер VK постинга")
async def get_workerpost_banner(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    workerpost = await _get_workerpost_or_404(database, workerpost_id, user_id)
    if not workerpost.banner_video_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Баннер не найден")

    banner_path = Path(workerpost.banner_video_path)
    if not banner_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл баннера не найден")

    media_type = mimetypes.guess_type(str(banner_path))[0] or "application/octet-stream"
    return FileResponse(path=banner_path, media_type=media_type, filename=banner_path.name)


@router.post("/{workerpost_id}/banner", summary="Загрузить видео-баннер VK постинга")
async def upload_workerpost_banner(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
        banner_file: UploadFile = File(...),
):
    workerpost = await _get_workerpost_or_404(database, workerpost_id, user_id)

    file_suffix = Path(banner_file.filename or "").suffix.lower()
    if file_suffix not in ALLOWED_BANNER_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только видеофайлы: mp4, mov, webm, m4v",
        )

    if banner_file.content_type and not banner_file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нужно загрузить видеофайл",
        )

    WORKERPOST_BANNERS_DIR.mkdir(parents=True, exist_ok=True)
    new_banner_path = WORKERPOST_BANNERS_DIR / f"workerpost_{workerpost_id}_{uuid4().hex}{file_suffix}"

    try:
        with new_banner_path.open("wb") as buffer:
            while True:
                chunk = await banner_file.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)
    finally:
        await banner_file.close()

    _delete_banner_file(workerpost.banner_video_path)

    await database.workerpost.edit(
        WorkerPostUpdate(
            banner_video_path=str(new_banner_path),
            banner_x=workerpost.banner_x if workerpost.banner_x is not None else DEFAULT_BANNER_X,
            banner_y=workerpost.banner_y if workerpost.banner_y is not None else DEFAULT_BANNER_Y,
            banner_width=workerpost.banner_width if workerpost.banner_width is not None else DEFAULT_BANNER_WIDTH,
            banner_height=workerpost.banner_height if workerpost.banner_height is not None else DEFAULT_BANNER_HEIGHT,
        ),
        exclude_unset=True,
        id=workerpost_id,
        user_id=user_id,
    )
    await database.commit()

    return {
        "status": "OK",
        "banner_url": f"/users/{user_id}/workerpost/{workerpost_id}/banner",
    }


@router.delete("/{workerpost_id}/banner", summary="Удалить видео-баннер VK постинга")
async def delete_workerpost_banner(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    workerpost = await _get_workerpost_or_404(database, workerpost_id, user_id)
    _delete_banner_file(workerpost.banner_video_path)

    await database.workerpost.edit(
        WorkerPostUpdate(banner_video_path=None),
        exclude_unset=True,
        id=workerpost_id,
        user_id=user_id,
    )
    await database.commit()
    return {"status": "OK"}

@router.get("/{workerpost_id}/posted_clips/count")
async def get_workerpost_postedclips_count(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    workerpost = await _get_workerpost_or_404(database, workerpost_id, user_id)
    count = await database.schedule_posting.count_filtered(workpost_id=workerpost.id, status="success")
    return {"count": count}

@router.get("/{workerpost_id}/posted_clips/last_date")
async def get_workerpost_posted_clips_last_date(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    workerpost = await _get_workerpost_or_404(database, workerpost_id, user_id)
    datetime = await database.schedule_posting.get_last_posted_date(workpost_id=workerpost.id, status="success")
    return {"last_date": datetime}

@router.get("/{workerpost_id}/vk_account/block_status")
async def get_workerpost_block_status(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    workerpost = await _get_workerpost_or_404(database, workerpost_id, user_id)
    vk_account = await database.vk_account.get_one_or_none(id=workerpost.vk_account_id)
    if vk_account.account_type == "blocked":
        return {"status": "blocked"}
    return {"status": "OK"}

@router.get("/{workerpost_id}/status", summary="Статус парсинга VK Постинг")
async def get_vk_group_status(
      user_id: UserIdDep,
      workerpost_id: int,
      database: DataBaseDep,
):
    workerpost = await _get_workerpost_or_404(database, workerpost_id, user_id)
    return {
        "status": workerpost.parse_status,   # pending | success | failure
        "task_id": workerpost.task_id,
    }


@router.put("/{workerpost_id}", summary="Обновить конкретный VK постинг")
async def update_workerpost(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
        workerpost_update: WorkerPostUpdate,
):
    await _get_workerpost_or_404(database, workerpost_id, user_id)

    await database.workerpost.edit(
        workerpost_update,
        exclude_unset=True,
        id=workerpost_id,
        user_id=user_id,
    )
    await database.commit()

    return {"status": "OK"}


@router.post("/create_workerpost", status_code=status.HTTP_201_CREATED, summary="Добавить сразу много групп Источников по url")
async def create_workerpost(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_request: WorkerPostRequestAdd,
):
    """Добавляет новый VK аккаунт для парсинга данных"""
    user = await database.user.get_one_or_none(id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    try:
        detail = await WorkerPostService(database).create_workerpost(user_id, workerpost_request)
        #detail = await VKGroupSourceService(database).create_groups(user_id, vk_groups_request)
        #detail = await VKAccountBackupService(database).create_accounts(user_id, groups_url)
        return {"status": "OK", "detail": detail}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{workerpost_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить VK Постинг")
async def delete_workpost(
        user_id: UserIdDep,
        database: DataBaseDep,
        workerpost_id: int,
):
    """Удаляет привязанный VK аккаунт и связанные данные"""
    workpost_db = await _get_workerpost_or_404(database, workerpost_id, user_id)
    service_workpost = WorkerPostService(database)
    vk_account = await database.vk_account.get_one_or_none(id=workpost_db.vk_account_id)
    vk_group = await database.vk_group.get_one_or_none(id=workpost_db.vk_group_id)

    await service_workpost.revert_account_backup(vk_account.id, vk_group.id) # меняет тип аккаунта на backup
    _delete_banner_file(workpost_db.banner_video_path)

    await database.workerpost.delete(id=workerpost_id, user_id=user_id)
    await database.commit()

    return {"status": "OK"}
