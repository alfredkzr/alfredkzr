from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Setting
from app.schemas import CredentialsUpdate, SettingsResponse, TelegramUpdate
from app.services.crypto import encrypt
from app.services.telegram import send_notification

router = APIRouter()


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    settings_map = {s.key: s.value for s in result.scalars().all()}

    return SettingsResponse(
        omakase_email=settings_map.get("omakase_email", ""),
        omakase_password_set=bool(settings_map.get("omakase_password")),
        telegram_bot_token=settings_map.get("telegram_bot_token", ""),
        telegram_chat_id=settings_map.get("telegram_chat_id", ""),
    )


@router.put("/credentials")
async def update_credentials(data: CredentialsUpdate, db: AsyncSession = Depends(get_db)):
    await _upsert_setting(db, "omakase_email", data.email)
    await _upsert_setting(db, "omakase_password", encrypt(data.password))
    await db.commit()
    return {"status": "ok"}


@router.put("/telegram")
async def update_telegram(data: TelegramUpdate, db: AsyncSession = Depends(get_db)):
    await _upsert_setting(db, "telegram_bot_token", data.bot_token)
    await _upsert_setting(db, "telegram_chat_id", data.chat_id)
    await db.commit()
    return {"status": "ok"}


@router.post("/telegram/test")
async def test_telegram(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    settings_map = {s.key: s.value for s in result.scalars().all()}

    token = settings_map.get("telegram_bot_token")
    chat_id = settings_map.get("telegram_chat_id")
    if not token or not chat_id:
        return {"status": "error", "detail": "Telegram not configured"}

    success = await send_notification(token, chat_id, "Test notification from Omakase Booking Bot!")
    return {"status": "ok" if success else "error"}


@router.post("/credentials/test")
async def test_credentials(db: AsyncSession = Depends(get_db)):
    from app.bot.auth import login
    from app.bot.browser import browser_manager
    from app.services.crypto import decrypt

    result = await db.execute(select(Setting))
    settings_map = {s.key: s.value for s in result.scalars().all()}

    email = settings_map.get("omakase_email")
    encrypted_password = settings_map.get("omakase_password")
    if not email or not encrypted_password:
        return {"status": "error", "detail": "Credentials not configured"}

    password = decrypt(encrypted_password)

    await browser_manager.start()
    context = await browser_manager.new_context()
    try:
        success = await login(context, email, password)
        return {"status": "ok" if success else "error", "detail": "Login successful" if success else "Login failed"}
    finally:
        await context.close()


async def _upsert_setting(db: AsyncSession, key: str, value: str):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        db.add(Setting(key=key, value=value))
