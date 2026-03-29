import logging
import os
from dataclasses import dataclass
from datetime import date, datetime

from playwright.async_api import Page

from app.bot.availability import AvailableSlot
from app.bot.stealth import human_click, human_delay

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = "data/screenshots"


@dataclass
class BookingResult:
    success: bool
    slot_date: date
    slot_time: str
    course_name: str | None = None
    party_size: int | None = None
    failure_reason: str | None = None
    screenshot_path: str | None = None


async def attempt_booking(
    page: Page,
    slot: AvailableSlot,
    party_size: int,
    restaurant_code: str,
) -> BookingResult:
    """
    Attempt to book a specific slot. The page should already be on the restaurant page
    with the correct date selected.

    Returns a BookingResult indicating success or failure.
    """
    screenshot_path = None

    try:
        logger.info(
            f"Attempting to book: {slot.slot_date} {slot.slot_time} "
            f"({party_size} pax) at {restaurant_code}"
        )

        # Step 1: Select the date on the calendar
        date_selector = f'[data-date="{slot.slot_date.isoformat()}"]'
        try:
            await human_click(page, date_selector)
            await human_delay()
        except Exception:
            logger.warning("Could not click date, it may already be selected")

        # Step 2: Select the time slot
        time_clicked = False
        time_selectors = [
            f'[data-time="{slot.slot_time}"]',
            f'button:has-text("{slot.slot_time}")',
            f'.time-slot:has-text("{slot.slot_time}")',
        ]
        for selector in time_selectors:
            try:
                await human_click(page, selector)
                time_clicked = True
                break
            except Exception:
                continue

        if not time_clicked:
            return BookingResult(
                success=False,
                slot_date=slot.slot_date,
                slot_time=slot.slot_time,
                party_size=party_size,
                failure_reason="Could not select time slot",
                screenshot_path=await _take_screenshot(page, restaurant_code, "time_fail"),
            )

        await human_delay()

        # Step 3: Set party size if there's a selector
        try:
            pax_selectors = [
                'select[name*="seats"], select[name*="party"], select[name*="pax"], select[name*="guest"]',
                '[class*="guest"] select, [class*="party"] select',
            ]
            for selector in pax_selectors:
                pax_el = await page.query_selector(selector)
                if pax_el:
                    await pax_el.select_option(value=str(party_size))
                    await human_delay(short=True)
                    break
        except Exception as e:
            logger.warning(f"Could not set party size: {e}")

        # Step 4: Select course if specified
        if slot.course_name:
            try:
                course_selectors = [
                    f'[class*="course"]:has-text("{slot.course_name}")',
                    f'button:has-text("{slot.course_name}")',
                    f'label:has-text("{slot.course_name}")',
                ]
                for selector in course_selectors:
                    try:
                        await human_click(page, selector)
                        await human_delay(short=True)
                        break
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Could not select course: {e}")

        # Step 5: Click the reserve/book button
        book_clicked = False
        book_selectors = [
            'button:has-text("Reserve"), button:has-text("Book")',
            'button:has-text("\u4e88\u7d04"), button:has-text("RESERVE")',
            '.reserve-btn, .book-btn, [class*="reserve"], [class*="booking"] button',
            'input[type="submit"][value*="Reserve"], input[type="submit"][value*="Book"]',
        ]
        for selector in book_selectors:
            try:
                await human_click(page, selector)
                book_clicked = True
                break
            except Exception:
                continue

        if not book_clicked:
            return BookingResult(
                success=False,
                slot_date=slot.slot_date,
                slot_time=slot.slot_time,
                course_name=slot.course_name,
                party_size=party_size,
                failure_reason="Could not find reserve/book button",
                screenshot_path=await _take_screenshot(page, restaurant_code, "book_btn_fail"),
            )

        # Step 6: Wait for confirmation page
        await page.wait_for_load_state("networkidle", timeout=15000)
        await human_delay()

        # Step 7: Handle confirmation step
        confirm_selectors = [
            'button:has-text("Confirm"), button:has-text("\u78ba\u5b9a")',
            'button:has-text("Complete"), button:has-text("Submit")',
        ]
        for selector in confirm_selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    await human_click(page, selector)
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    await human_delay()
                    break
            except Exception:
                continue

        # Step 8: Check for success indicators
        success_indicators = [
            '[class*="success"], [class*="confirmed"], [class*="complete"]',
            'text="Reservation confirmed"',
            'text="\u4e88\u7d04\u304c\u78ba\u5b9a"',
            'text="Booking confirmed"',
            '.reservation-confirmed',
        ]
        for selector in success_indicators:
            try:
                el = await page.query_selector(selector)
                if el:
                    screenshot_path = await _take_screenshot(page, restaurant_code, "confirmed")
                    logger.info(f"Booking confirmed! Screenshot: {screenshot_path}")
                    return BookingResult(
                        success=True,
                        slot_date=slot.slot_date,
                        slot_time=slot.slot_time,
                        course_name=slot.course_name,
                        party_size=party_size,
                        screenshot_path=screenshot_path,
                    )
            except Exception:
                continue

        # Check for error/failure indicators
        error_indicators = [
            '[class*="error"], [class*="sold-out"], [class*="unavailable"]',
            'text="already been taken"',
            'text="no longer available"',
        ]
        for selector in error_indicators:
            try:
                el = await page.query_selector(selector)
                if el:
                    error_text = await el.text_content()
                    screenshot_path = await _take_screenshot(page, restaurant_code, "error")
                    return BookingResult(
                        success=False,
                        slot_date=slot.slot_date,
                        slot_time=slot.slot_time,
                        course_name=slot.course_name,
                        party_size=party_size,
                        failure_reason=f"Slot unavailable: {error_text}",
                        screenshot_path=screenshot_path,
                    )
            except Exception:
                continue

        # Uncertain outcome
        screenshot_path = await _take_screenshot(page, restaurant_code, "uncertain")
        return BookingResult(
            success=False,
            slot_date=slot.slot_date,
            slot_time=slot.slot_time,
            course_name=slot.course_name,
            party_size=party_size,
            failure_reason="Uncertain booking outcome \u2014 check screenshot",
            screenshot_path=screenshot_path,
        )

    except Exception as e:
        logger.error(f"Booking attempt failed: {e}")
        screenshot_path = await _take_screenshot(page, restaurant_code, "exception")
        return BookingResult(
            success=False,
            slot_date=slot.slot_date,
            slot_time=slot.slot_time,
            course_name=slot.course_name,
            party_size=party_size,
            failure_reason=str(e),
            screenshot_path=screenshot_path,
        )


async def _take_screenshot(page: Page, restaurant_code: str, label: str) -> str | None:
    """Take a screenshot and return the file path."""
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{restaurant_code}_{label}_{timestamp}.png"
        path = os.path.join(SCREENSHOTS_DIR, filename)
        await page.screenshot(path=path, full_page=True)
        logger.info(f"Screenshot saved: {path}")
        return path
    except Exception as e:
        logger.warning(f"Failed to take screenshot: {e}")
        return None
