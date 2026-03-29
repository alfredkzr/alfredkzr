from datetime import date, datetime

from pydantic import BaseModel, HttpUrl


class SlotPreferenceCreate(BaseModel):
    priority: int
    preferred_date: date
    preferred_time: str
    course_name: str | None = None


class SlotPreferenceResponse(SlotPreferenceCreate):
    id: int
    target_id: int

    model_config = {"from_attributes": True}


class TargetCreate(BaseModel):
    restaurant_code: str
    restaurant_name: str
    restaurant_url: str
    priority: int = 0
    party_size: int = 2
    preferred_date_start: date | None = None
    preferred_date_end: date | None = None
    booking_opens_at: datetime | None = None
    check_interval_seconds: int = 30
    is_active: bool = True
    slot_preferences: list[SlotPreferenceCreate] = []


class TargetUpdate(BaseModel):
    restaurant_code: str | None = None
    restaurant_name: str | None = None
    restaurant_url: str | None = None
    priority: int | None = None
    party_size: int | None = None
    preferred_date_start: date | None = None
    preferred_date_end: date | None = None
    booking_opens_at: datetime | None = None
    check_interval_seconds: int | None = None
    is_active: bool | None = None
    slot_preferences: list[SlotPreferenceCreate] | None = None


class TargetResponse(BaseModel):
    id: int
    restaurant_code: str
    restaurant_name: str
    restaurant_url: str
    priority: int
    party_size: int
    preferred_date_start: date | None
    preferred_date_end: date | None
    booking_opens_at: datetime | None
    check_interval_seconds: int
    is_active: bool
    status: str
    created_at: datetime
    updated_at: datetime
    slot_preferences: list[SlotPreferenceResponse]

    model_config = {"from_attributes": True}


class PriorityUpdate(BaseModel):
    priority: int


class BookingAttemptResponse(BaseModel):
    id: int
    target_id: int
    slot_date: date | None
    slot_time: str | None
    course_name: str | None
    party_size: int | None
    status: str
    failure_reason: str | None
    screenshot_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CredentialsUpdate(BaseModel):
    email: str
    password: str


class TelegramUpdate(BaseModel):
    bot_token: str
    chat_id: str


class SettingsResponse(BaseModel):
    omakase_email: str
    omakase_password_set: bool
    telegram_bot_token: str
    telegram_chat_id: str


class BotStatusResponse(BaseModel):
    is_running: bool
    targets: dict[int, str]  # target_id -> status
