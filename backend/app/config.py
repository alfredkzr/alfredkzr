from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///data/omakase.db"
    encryption_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    omakase_email: str = ""
    omakase_password: str = ""
    headless: bool = True
    playwright_browsers_path: str = "/app/browsers"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
