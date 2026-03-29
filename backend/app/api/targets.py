from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import SlotPreference, Target
from app.schemas import PriorityUpdate, TargetCreate, TargetResponse, TargetUpdate

router = APIRouter()


@router.get("", response_model=list[TargetResponse])
async def list_targets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Target).options(selectinload(Target.slot_preferences)).order_by(Target.priority)
    )
    return result.scalars().all()


@router.post("", response_model=TargetResponse, status_code=201)
async def create_target(data: TargetCreate, db: AsyncSession = Depends(get_db)):
    target = Target(
        restaurant_code=data.restaurant_code,
        restaurant_name=data.restaurant_name,
        restaurant_url=data.restaurant_url,
        priority=data.priority,
        party_size=data.party_size,
        preferred_date_start=data.preferred_date_start,
        preferred_date_end=data.preferred_date_end,
        booking_opens_at=data.booking_opens_at,
        check_interval_seconds=data.check_interval_seconds,
        is_active=data.is_active,
    )
    db.add(target)
    await db.flush()

    for sp in data.slot_preferences:
        pref = SlotPreference(
            target_id=target.id,
            priority=sp.priority,
            preferred_date=sp.preferred_date,
            preferred_time=sp.preferred_time,
            course_name=sp.course_name,
        )
        db.add(pref)

    await db.commit()
    await db.refresh(target, attribute_names=["slot_preferences"])
    return target


@router.get("/{target_id}", response_model=TargetResponse)
async def get_target(target_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Target)
        .where(Target.id == target_id)
        .options(selectinload(Target.slot_preferences))
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.put("/{target_id}", response_model=TargetResponse)
async def update_target(target_id: int, data: TargetUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Target)
        .where(Target.id == target_id)
        .options(selectinload(Target.slot_preferences))
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    update_fields = data.model_dump(exclude_unset=True, exclude={"slot_preferences"})
    for field, value in update_fields.items():
        setattr(target, field, value)

    if data.slot_preferences is not None:
        for pref in target.slot_preferences:
            await db.delete(pref)
        for sp in data.slot_preferences:
            pref = SlotPreference(
                target_id=target.id,
                priority=sp.priority,
                preferred_date=sp.preferred_date,
                preferred_time=sp.preferred_time,
                course_name=sp.course_name,
            )
            db.add(pref)

    await db.commit()
    await db.refresh(target, attribute_names=["slot_preferences"])
    return target


@router.delete("/{target_id}", status_code=204)
async def delete_target(target_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    await db.delete(target)
    await db.commit()


@router.patch("/{target_id}/priority", response_model=TargetResponse)
async def update_priority(
    target_id: int, data: PriorityUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Target)
        .where(Target.id == target_id)
        .options(selectinload(Target.slot_preferences))
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    target.priority = data.priority
    await db.commit()
    await db.refresh(target)
    return target
