import logging

from playwright.async_api import BrowserContext, Page

from app.bot.browser import browser_manager
from app.bot.stealth import human_click, human_delay, human_type

logger = logging.getLogger(__name__)

OMAKASE_BASE_URL = "https://omakase.in/en"
LOGIN_URL = "https://omakase.in/en/users/sign_in"


async def is_logged_in(page: Page) -> bool:
    """Check if the current page shows a logged-in state."""
    try:
        logged_in = await page.query_selector(
            '[data-testid="user-menu"], .user-avatar, a[href*="mypage"], a[href*="sign_out"]'
        )
        return logged_in is not None
    except Exception:
        return False


async def login(context: BrowserContext, email: str, password: str) -> bool:
    """
    Log into Omakase.in using the provided credentials.
    Returns True if login successful, False otherwise.
    """
    page = await context.new_page()

    try:
        logger.info("Navigating to Omakase.in login page")
        await page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
        await human_delay()

        if await is_logged_in(page):
            logger.info("Already logged in")
            await browser_manager.save_session(context)
            await page.close()
            return True

        logger.info("Filling login form")
        email_selector = 'input[type="email"], input[name="user[email]"], #user_email'
        password_selector = 'input[type="password"], input[name="user[password]"], #user_password'

        await page.wait_for_selector(email_selector, timeout=10000)
        await human_type(page, email_selector, email)
        await human_delay(short=True)
        await human_type(page, password_selector, password)
        await human_delay()

        submit_selector = 'button[type="submit"], input[type="submit"], .login-btn'
        await human_click(page, submit_selector)

        await page.wait_for_load_state("networkidle", timeout=15000)
        await human_delay()

        if await is_logged_in(page):
            logger.info("Login successful")
            await browser_manager.save_session(context)
            await page.close()
            return True

        error_el = await page.query_selector(".alert-danger, .error, .flash-error")
        if error_el:
            error_text = await error_el.text_content()
            logger.error(f"Login failed: {error_text}")
        else:
            logger.error("Login failed: unknown reason")

        await page.close()
        return False

    except Exception as e:
        logger.error(f"Login error: {e}")
        try:
            await page.close()
        except Exception:
            pass
        return False
