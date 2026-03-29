import logging
from dataclasses import dataclass
from datetime import date

from playwright.async_api import Page

from app.bot.stealth import human_click, human_delay

logger = logging.getLogger(__name__)

RESTAURANT_URL_TEMPLATE = "https://omakase.in/en/r/{code}"


@dataclass
class AvailableSlot:
    slot_date: date
    slot_time: str
    course_name: str | None = None
    seats_available: int | None = None


async def check_availability(
    page: Page,
    restaurant_code: str,
    preferred_date_start: date | None = None,
    preferred_date_end: date | None = None,
    party_size: int = 2,
) -> list[AvailableSlot]:
    """
    Navigate to a restaurant page and extract available slots.
    Returns a list of AvailableSlot objects matching the criteria.
    """
    url = RESTAURANT_URL_TEMPLATE.format(code=restaurant_code)
    slots: list[AvailableSlot] = []

    try:
        logger.info(f"Checking availability at {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await human_delay()

        await page.wait_for_selector(
            '.calendar, .availability, [class*="calendar"], [class*="schedule"], [class*="reservation"]',
            timeout=15000,
        )
        await human_delay(short=True)

        date_selectors = [
            '.calendar-day:not(.disabled):not(.sold-out):not(.unavailable)',
            'td.available, td:not(.disabled):not(.past)',
            '[class*="date"]:not([class*="disabled"]):not([class*="sold"])',
            'button[class*="day"]:not(:disabled)',
        ]

        available_dates = []
        for selector in date_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                available_dates = elements
                logger.info(f"Found {len(elements)} available date elements with selector: {selector}")
                break

        if not available_dates:
            logger.info("No available dates found on calendar")
            return slots

        for date_el in available_dates:
            try:
                date_text = await date_el.get_attribute("data-date") or await date_el.text_content()
                if not date_text:
                    continue

                slot_date = _parse_date(date_text.strip())
                if not slot_date:
                    continue

                if preferred_date_start and slot_date < preferred_date_start:
                    continue
                if preferred_date_end and slot_date > preferred_date_end:
                    continue

                await human_click(page, f'[data-date="{slot_date.isoformat()}"]')
                await human_delay(short=True)

                time_slots = await _extract_time_slots(page, slot_date)
                slots.extend(time_slots)

            except Exception as e:
                logger.warning(f"Error processing date element: {e}")
                continue

        logger.info(f"Found {len(slots)} available slots")
        return slots

    except Exception as e:
        logger.error(f"Availability check failed: {e}")
        return slots


async def _extract_time_slots(page: Page, slot_date: date) -> list[AvailableSlot]:
    """Extract time slots from the currently selected date on the page."""
    time_slots: list[AvailableSlot] = []

    time_selectors = [
        '.time-slot:not(.disabled):not(.sold-out)',
        '[class*="time"]:not([class*="disabled"]):not([class*="sold"])',
        'button[class*="slot"]:not(:disabled)',
        '.schedule-item.available',
    ]

    time_elements = []
    for selector in time_selectors:
        elements = await page.query_selector_all(selector)
        if elements:
            time_elements = elements
            break

    for time_el in time_elements:
        try:
            time_text = await time_el.get_attribute("data-time") or await time_el.text_content()
            if not time_text:
                continue

            time_str = _parse_time(time_text.strip())
            if not time_str:
                continue

            course_name = None
            course_el = await time_el.query_selector('[class*="course"], [class*="menu"]')
            if course_el:
                course_name = await course_el.text_content()

            seats = None
            seats_el = await time_el.query_selector('[class*="seat"], [class*="remaining"]')
            if seats_el:
                seats_text = await seats_el.text_content()
                seats = _parse_seats(seats_text)

            time_slots.append(AvailableSlot(
                slot_date=slot_date,
                slot_time=time_str,
                course_name=course_name.strip() if course_name else None,
                seats_available=seats,
            ))
        except Exception as e:
            logger.warning(f"Error extracting time slot: {e}")
            continue

    return time_slots


def _parse_date(text: str) -> date | None:
    """Try to parse a date from various formats."""
    import re
    from datetime import datetime

    try:
        return date.fromisoformat(text)
    except ValueError:
        pass

    match = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    return None


def _parse_time(text: str) -> str | None:
    """Extract a time string like '18:00' from text."""
    import re
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"
    return None


def _parse_seats(text: str | None) -> int | None:
    """Extract seat count from text like '3 seats' or 'Remaining: 2'."""
    if not text:
        return None
    import re
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None
