import logging
import os

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from app.bot.stealth import get_random_profile
from app.config import settings

logger = logging.getLogger(__name__)

STORAGE_STATE_PATH = "data/storage_state.json"


class BrowserManager:
    """Manages a single Playwright browser instance shared across monitors."""

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        if self._browser:
            return
        self._playwright = await async_playwright().start()

        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
            self._browser = await stealth.use_async(
                self._playwright.chromium
            ).launch(headless=settings.headless)
            logger.info("Browser launched with stealth mode")
        except ImportError:
            self._browser = await self._playwright.chromium.launch(
                headless=settings.headless
            )
            logger.warning("playwright-stealth not available, launching without stealth")

    async def new_context(self) -> BrowserContext:
        if not self._browser:
            await self.start()

        profile = get_random_profile()

        # Try to load existing session
        storage_state = None
        if os.path.exists(STORAGE_STATE_PATH):
            storage_state = STORAGE_STATE_PATH
            logger.info("Loading saved browser session")

        context = await self._browser.new_context(
            user_agent=profile["user_agent"],
            viewport=profile["viewport"],
            locale=profile["locale"],
            timezone_id=profile["timezone_id"],
            storage_state=storage_state,
        )
        return context

    async def save_session(self, context: BrowserContext) -> None:
        os.makedirs(os.path.dirname(STORAGE_STATE_PATH), exist_ok=True)
        await context.storage_state(path=STORAGE_STATE_PATH)
        logger.info("Browser session saved")

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser stopped")

    @property
    def is_running(self) -> bool:
        return self._browser is not None


browser_manager = BrowserManager()
