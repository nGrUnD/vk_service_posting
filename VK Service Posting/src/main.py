import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

import sys
from pathlib import Path
from starlette.middleware.cors import CORSMiddleware


sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings
from src.database import *
from src.api.user_auth import router as router_user_auth
from src.api.vk_account_cred import router as router_vk_account_cred
from src.api.vk_account import router as router_vk_account
from src.api.category import router as router_category
from src.api.vk_group import router as router_group
from src.api.clip_list import router as router_clip_list
from src.api.workerpost import router as router_workerpost

from src.services.posting_service import PostingService
from src.utils.database_manager import DataBaseManager
from src.api.dependencies import get_database, get_database_manager
from src.repositories.vk_account import VKAccountRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    async def scheduler_loop():
        minutes = 0
        while True:
            await asyncio.sleep(60)  # каждые 60 секунд
            minutes += 1

            async with async_session_maker() as session:
                async with PostingService(session) as serivce:
                    try:
                        await serivce.check_and_schedule(minutes)
                    except Exception as e:
                        print(e)

            if minutes >= 60:
                minutes = 0
                #print(f"обнуление минут: {minutes}")

    scheduler_task = asyncio.create_task(scheduler_loop())
    yield
    scheduler_task.cancel()  # корректно отменяем при завершении приложения

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://79.141.67.73",
    ],  # фронтенд-URL
    allow_credentials=True,                   # важно для cookie
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router_user_auth)
app.include_router(router_vk_account_cred)
app.include_router(router_vk_account)
app.include_router(router_category)
app.include_router(router_group)
app.include_router(router_clip_list)
app.include_router(router_workerpost)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)