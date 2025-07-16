import asyncio

from fastapi import FastAPI
import uvicorn

import sys
from pathlib import Path
from starlette.middleware.cors import CORSMiddleware

sys.path.append(str(Path(__file__).parent.parent))

from src.database import *
from src.api.user_auth import router as router_user_auth
from src.api.vk_account import router as router_vk_account
from src.api.category import router as router_category
from src.api.vk_group import router as router_group
from src.api.clip_list import router as router_clip_list
from src.api.workerpost import router as router_workerpost
from src.api.proxy import router as router_proxy
from src.api.tools import router as router_tools

import src.models  # 👈 это активирует импорты из models/__init__.py

from src.services.posting_service import PostingService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scheduler_loop():
    logger.info("✅ Scheduler loop started")
    minutes = 0
    while True:
        logger.info("✅ sleep 60 sec")
        await asyncio.sleep(60)  # каждые 60 секунд
        minutes += 1
        
        logger.info("✅ try connect database")
        async with async_session_maker() as session:
            async with PostingService(session) as serivce:
                try:
                    logger.info("✅ check_and_schedule")
                    await serivce.check_and_schedule(minutes)
                except Exception as e:
                    print(e)

        if minutes >= 60:
            minutes = 0
            logger.info("✅ Обновление минут")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://0.0.0.0:5173",
        "http://79.141.67.73",
        "http://87.228.102.22",
    ],  # фронтенд-URL
    allow_credentials=True,                   # важно для cookie
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router_user_auth)
app.include_router(router_vk_account)
app.include_router(router_category)
app.include_router(router_group)
app.include_router(router_clip_list)
app.include_router(router_workerpost)
app.include_router(router_proxy)
app.include_router(router_tools)

@app.on_event("startup")
async def start_scheduler():
    asyncio.create_task(scheduler_loop())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
