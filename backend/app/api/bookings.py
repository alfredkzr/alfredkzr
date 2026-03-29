from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BookingAttempt
from app.schemas import BookingAttemptResponse

router = APIRouter()


@router.get("", response_model=list[BookingAttemptResponse])
async def list_bookings(
    target_id: int | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(BookingAttempt).order_by(BookingAttempt.created_at.desc())
    if target_id:
        query = query.where(BookingAttempt.target_id == target_id)
    if status:
        query = query.where(BookingAttempt.status == status)
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{booking_id}", response_model=BookingAttemptResponse)
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BookingAttempt).where(BookingAttempt.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking attempt not found")
    return booking


@router.get("/{booking_id}/screenshot")
async def get_screenshot(booking_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BookingAttempt).where(BookingAttempt.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking attempt not found")
    if not booking.screenshot_path:
        raise HTTPException(status_code=404, detail="No screenshot available")
    return FileResponse(booking.screenshot_path, media_type="image/png")
