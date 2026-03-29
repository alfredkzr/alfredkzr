from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_code: Mapped[str] = mapped_column(String(50), nullable=False)
    restaurant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    restaurant_url: Mapped[str] = mapped_column(String(500), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    preferred_date_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    preferred_date_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    booking_opens_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="idle")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    slot_preferences: Mapped[list["SlotPreference"]] = relationship(
        back_populates="target", cascade="all, delete-orphan", order_by="SlotPreference.priority"
    )
    booking_attempts: Mapped[list["BookingAttempt"]] = relationship(
        back_populates="target", cascade="all, delete-orphan"
    )


class SlotPreference(Base):
    __tablename__ = "slot_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("targets.id", ondelete="CASCADE"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_time: Mapped[str] = mapped_column(String(10), nullable=False)
    course_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    target: Mapped["Target"] = relationship(back_populates="slot_preferences")


class BookingAttempt(Base):
    __tablename__ = "booking_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("targets.id"), nullable=False)
    slot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    slot_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    course_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    party_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    target: Mapped["Target"] = relationship(back_populates="booking_attempts")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
