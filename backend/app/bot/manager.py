import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.browser import browser_manager
from app.bot.monitor import TargetMonitor
from app.database import async_session
from app.models import Setting, Target
from app.services.crypto import decrypt
from app.services.event_bus import event_bus

logger = logging.getLogger(__name__)


class BotManager:
    """Orchestrates all target monitors with priority ordering."""

    def __init__(self):
        self._monitors: dict[int, TargetMonitor] = {}
        self._is_running = False
        self._telegram_notify = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def get_status(self) -> dict[int, str]:
        return {tid: m.target.status for tid, m in self._monitors.items()}

    async def start_all(self) -> None:
        if self._is_running:
            return

        await browser_manager.start()
        self._is_running = True

        self._telegram_notify = await self._get_telegram_notifier()

        credentials = await self._get_credentials()
        if not credentials:
            logger.error("No Omakase.in credentials configured")
            await event_bus.publish({
                "event": "error",
                "error": "No Omakase.in credentials configured. Go to Settings to add them.",
            })
            self._is_running = False
            return

        async with async_session() as db:
            result = await db.execute(
                select(Target)
                .where(Target.is_active.is_(True))
                .options(selectinload(Target.slot_preferences))
                .order_by(Target.priority)
            )
            targets = result.scalars().all()

        if not targets:
            logger.info("No active targets to monitor")
            self._is_running = False
            return

        logger.info(f"Starting monitoring for {len(targets)} targets")

        for i, target in enumerate(targets):
            context = await browser_manager.new_context()
            monitor = TargetMonitor(
                target=target,
                context=context,
                credentials=credentials,
                telegram_notify=self._telegram_notify,
            )
            self._monitors[target.id] = monitor
            await monitor.start()

            if i < len(targets) - 1:
                stagger = target.check_interval_seconds / max(len(targets), 1)
                await asyncio.sleep(min(stagger, 5))

    async def stop_all(self) -> None:
        logger.info("Stopping all monitors")
        for monitor in self._monitors.values():
            await monitor.stop()
        self._monitors.clear()
        await browser_manager.stop()
        self._is_running = False

    async def start_target(self, target_id: int) -> bool:
        if target_id in self._monitors:
            return True

        if not browser_manager.is_running:
            await browser_manager.start()
            self._is_running = True

        credentials = await self._get_credentials()
        if not credentials:
            return False

        async with async_session() as db:
            result = await db.execute(
                select(Target)
                .where(Target.id == target_id)
                .options(selectinload(Target.slot_preferences))
            )
            target = result.scalar_one_or_none()

        if not target:
            return False

        if not self._telegram_notify:
            self._telegram_notify = await self._get_telegram_notifier()

        context = await browser_manager.new_context()
        monitor = TargetMonitor(
            target=target,
            context=context,
            credentials=credentials,
            telegram_notify=self._telegram_notify,
        )
        self._monitors[target_id] = monitor
        await monitor.start()
        return True

    async def stop_target(self, target_id: int) -> bool:
        monitor = self._monitors.pop(target_id, None)
        if monitor:
            await monitor.stop()
            return True
        return False

    async def _get_credentials(self) -> tuple[str, str] | None:
        async with async_session() as db:
            email_result = await db.execute(
                select(Setting).where(Setting.key == "omakase_email")
            )
            password_result = await db.execute(
                select(Setting).where(Setting.key == "omakase_password")
            )
            email_setting = email_result.scalar_one_or_none()
            password_setting = password_result.scalar_one_or_none()

        if not email_setting or not password_setting:
            return None

        return email_setting.value, decrypt(password_setting.value)

    async def _get_telegram_notifier(self):
        async with async_session() as db:
            token_result = await db.execute(
                select(Setting).where(Setting.key == "telegram_bot_token")
            )
            chat_result = await db.execute(
                select(Setting).where(Setting.key == "telegram_chat_id")
            )
            token_setting = token_result.scalar_one_or_none()
            chat_setting = chat_result.scalar_one_or_none()

        if not token_setting or not chat_setting:
            logger.warning("Telegram not configured, notifications disabled")
            return None

        from app.services.telegram import send_notification

        token = token_setting.value
        chat_id = chat_setting.value

        async def notify(message: str):
            await send_notification(token, chat_id, message)

        return notify


bot_manager = BotManager()
