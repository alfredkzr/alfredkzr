import logging

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


async def send_notification(token: str, chat_id: str, message: str) -> bool:
    """Send a Telegram notification message."""
    url = TELEGRAM_API_URL.format(token=token)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": f"\ud83c\udf63 Omakase Bot\n\n{message}",
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("Telegram notification sent")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} {response.text}")
                return False
    except Exception as e:
        logger.error(f"Telegram notification failed: {e}")
        return False
