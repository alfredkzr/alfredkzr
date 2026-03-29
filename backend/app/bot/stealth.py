import random


# Realistic browser profiles for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
]


def get_random_profile() -> dict:
    return {
        "user_agent": random.choice(USER_AGENTS),
        "viewport": random.choice(VIEWPORTS),
        "locale": "en-US",
        "timezone_id": "Asia/Tokyo",
    }


async def human_delay(short: bool = False):
    """Random delay to simulate human behavior."""
    import asyncio
    if short:
        await asyncio.sleep(random.uniform(0.2, 0.8))
    else:
        await asyncio.sleep(random.uniform(0.5, 2.0))


async def human_type(page, selector: str, text: str):
    """Type text with human-like delays between keystrokes."""
    await page.click(selector)
    await human_delay(short=True)
    for char in text:
        await page.keyboard.press(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def human_click(page, selector: str):
    """Click with mouse movement to simulate human behavior."""
    element = await page.wait_for_selector(selector, timeout=10000)
    if element:
        box = await element.bounding_box()
        if box:
            # Move mouse to element with slight offset
            x = box["x"] + box["width"] / 2 + random.uniform(-3, 3)
            y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
            await page.mouse.move(x, y)
            await human_delay(short=True)
    await page.click(selector)


import asyncio
