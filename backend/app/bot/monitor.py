import asyncio
import logging
import random
from datetime import datetime

from playwright.async_api import BrowserContext

from app.bot.auth import is_logged_in, login
from app.bot.availability import AvailableSlot, check_availability
from app.bot.booker import BookingResult, attempt_booking
from app.models import SlotPreference, Target
from app.services.event_bus import event_bus

logger = logging.getLogger(__name__)


class TargetMonitor:
    """Monitors a single restaurant target and attempts booking when slots match."""

    def __init__(
        self,
        target: Target,
        context: BrowserContext,
        credentials: tuple[str, str],
        telegram_notify=None,
    ):
        self.target = target
        self.context = context
        self.email, self.password = credentials
        self.telegram_notify = telegram_notify
        self.is_running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"Monitor started for target {self.target.id}: {self.target.restaurant_name}")

    async def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info(f"Monitor stopped for target {self.target.id}")

    async def _run(self):
        try:
            if self.target.booking_opens_at:
                now = datetime.utcnow()
                opens_at = self.target.booking_opens_at
                if opens_at > now:
                    wait_seconds = (opens_at - now).total_seconds()
                    logger.info(
                        f"Target {self.target.id}: waiting {wait_seconds:.0f}s "
                        f"until booking opens at {opens_at}"
                    )
                    await self._update_status("waiting")
                    await asyncio.sleep(wait_seconds)

            while self.is_running:
                try:
                    await self._check_and_book()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Monitor error for target {self.target.id}: {e}")
                    await self._update_status("error")
                    await self._emit("error", {"target_id": self.target.id, "error": str(e)})
                    if self.telegram_notify:
                        await self.telegram_notify(
                            f"Error monitoring {self.target.restaurant_name}: {e}"
                        )

                if not self.is_running:
                    break

                interval = self.target.check_interval_seconds + random.uniform(-2, 2)
                await asyncio.sleep(max(5, interval))

        except asyncio.CancelledError:
            logger.info(f"Monitor cancelled for target {self.target.id}")

    async def _check_and_book(self):
        await self._update_status("monitoring")

        page = await self.context.new_page()
        try:
            await page.goto("https://omakase.in/en", wait_until="networkidle", timeout=30000)
            if not await is_logged_in(page):
                logger.info(f"Session expired, re-authenticating")
                success = await login(self.context, self.email, self.password)
                if not success:
                    raise Exception("Re-authentication failed")
                await page.close()
                page = await self.context.new_page()

            slots = await check_availability(
                page=page,
                restaurant_code=self.target.restaurant_code,
                preferred_date_start=self.target.preferred_date_start,
                preferred_date_end=self.target.preferred_date_end,
                party_size=self.target.party_size,
            )

            if not slots:
                logger.info(f"Target {self.target.id}: no matching slots found")
                return

            await self._update_status("found")
            await self._emit("slot_found", {
                "target_id": self.target.id,
                "slots": [{"date": str(s.slot_date), "time": s.slot_time} for s in slots],
            })

            if self.telegram_notify:
                slot_list = "\n".join(
                    f"  - {s.slot_date} {s.slot_time}" for s in slots[:5]
                )
                await self.telegram_notify(
                    f"Slots found for {self.target.restaurant_name}!\n{slot_list}"
                )

            ordered_slots = self._sort_by_preference(slots)

            for slot in ordered_slots:
                if not self.is_running:
                    break

                await self._update_status("booking")
                result = await attempt_booking(
                    page=page,
                    slot=slot,
                    party_size=self.target.party_size,
                    restaurant_code=self.target.restaurant_code,
                )

                await self._emit("booking_result", {
                    "target_id": self.target.id,
                    "success": result.success,
                    "date": str(result.slot_date),
                    "time": result.slot_time,
                    "failure_reason": result.failure_reason,
                })

                if result.success:
                    await self._update_status("booked")
                    if self.telegram_notify:
                        await self.telegram_notify(
                            f"BOOKED! {self.target.restaurant_name}\n"
                            f"Date: {result.slot_date}\n"
                            f"Time: {result.slot_time}\n"
                            f"Party: {result.party_size} pax"
                        )
                    self.is_running = False  # STOP to prevent double booking
                    return

                logger.info(
                    f"Booking failed for {slot.slot_date} {slot.slot_time}: "
                    f"{result.failure_reason}"
                )

            if self.telegram_notify:
                await self.telegram_notify(
                    f"All preferred slots taken for {self.target.restaurant_name}. "
                    f"Continuing to monitor..."
                )

        finally:
            try:
                await page.close()
            except Exception:
                pass

    def _sort_by_preference(self, slots: list[AvailableSlot]) -> list[AvailableSlot]:
        """Sort available slots by user's slot preference priority (strict waterfall)."""
        preferences = sorted(self.target.slot_preferences, key=lambda p: p.priority)

        ordered: list[AvailableSlot] = []
        remaining = list(slots)

        for pref in preferences:
            for slot in remaining:
                if (
                    slot.slot_date == pref.preferred_date
                    and slot.slot_time == pref.preferred_time
                ):
                    ordered.append(slot)
                    remaining.remove(slot)
                    break

        ordered.extend(remaining)
        return ordered

    async def _update_status(self, status: str):
        self.target.status = status
        await self._emit("status_change", {"target_id": self.target.id, "status": status})

    async def _emit(self, event: str, data: dict):
        await event_bus.publish({"event": event, **data})
