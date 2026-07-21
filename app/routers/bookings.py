from typing import Annotated
from sqlalchemy import func, select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, APIRouter, HTTPException

from app.db import get_session
from app.models import Room, Booking, Setting, BookingStatus
from app.schemas import BookingRequest, BookingResponse

router = APIRouter(prefix="/bookings", tags=["Bookings"])


async def expire_bookings(room_id: int, db: AsyncSession):
    await db.execute(
        update(Booking)
        .where(
            Booking.room_id == room_id,
            Booking.status == BookingStatus.pending,
            Booking.expires_at <= func.now(),
        )
        .values(status=BookingStatus.expired)
    )


# TODO: grab user id
async def get_current_user():
    return 1


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking(
    body: BookingRequest,
    user_id: Annotated[int, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    room = await db.get(Room, body.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    await expire_bookings(body.room_id, db)

    requested_range = func.tstzrange(body.start_time, body.end_time, "[)")

    stmt = select(
        select(Booking)
        .where(
            and_(
                Booking.room_id == body.room_id,
                func.tstzrange(Booking.start_time, Booking.end_time, "[)").op("&&")(
                    requested_range
                ),
                Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
            )
        )
        .exists()
    )

    result = await db.execute(stmt)

    if result.scalar_one():
        raise HTTPException(status_code=409, detail="Time slot is no longer available")

    ttl_row = await db.scalar(
        select(Setting.value).where(Setting.name == "hold_ttl_minutes")
    )

    booking = Booking(
        room_id=body.room_id,
        user_id=user_id,
        start_time=body.start_time,
        end_time=body.end_time,
        expires_at=func.now() + func.make_interval(0, 0, 0, 0, 0, int(ttl_row)),  # pyright: ignore[reportArgumentType]
    )

    db.add(booking)
    await db.flush()
    await db.refresh(booking)
    return booking
