from fastapi import APIRouter

from app.bot.manager import bot_manager
from app.schemas import BotStatusResponse

router = APIRouter()


@router.post("/start")
async def start_bot():
    await bot_manager.start_all()
    return {"status": "started"}


@router.post("/stop")
async def stop_bot():
    await bot_manager.stop_all()
    return {"status": "stopped"}


@router.post("/start/{target_id}")
async def start_target(target_id: int):
    success = await bot_manager.start_target(target_id)
    if not success:
        return {"status": "error", "detail": "Could not start target"}
    return {"status": "started", "target_id": target_id}


@router.post("/stop/{target_id}")
async def stop_target(target_id: int):
    success = await bot_manager.stop_target(target_id)
    if not success:
        return {"status": "error", "detail": "Target not running"}
    return {"status": "stopped", "target_id": target_id}


@router.get("/status", response_model=BotStatusResponse)
async def get_status():
    return BotStatusResponse(
        is_running=bot_manager.is_running,
        targets=bot_manager.get_status(),
    )
