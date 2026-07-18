from typing import Annotated
from fastapi import FastAPI, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from app.db import get_session
from datetime import date, time, datetime, timezone, timedelta
from ..models.booking import Booking, BookingStatus
from ..models.room import Room
from ..schemas.rooms import BusyInterval, RoomResponse

app = FastAPI()

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=list[RoomResponse])
async def get_rooms(db: Annotated[AsyncSession, Depends(get_session)]):

    stmt = select(Room)

    rows = await db.execute(stmt)

    items = rows.scalars().all()

    return items


@router.get("/{room_id}/availability", response_model=list[BusyInterval])
async def get_room_availability(
    room_id: int, date: date, session: Annotated[AsyncSession, Depends(get_session)]
):

    day_start = datetime.combine(date, time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    stmt = select(Booking.start_time, Booking.end_time).where(
        Booking.room_id == room_id,
        Booking.start_time < day_end,
        Booking.end_time > day_start,
        or_(
            Booking.status == BookingStatus.confirmed,
            and_(
                Booking.status == BookingStatus.pending,
                Booking.expires_at > func.now(),
            ),
        ),
    )

    rows = (await session.execute(stmt)).all()

    return [BusyInterval(start_time=s, end_time=e) for s, e in rows]
