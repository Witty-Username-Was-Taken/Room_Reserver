import enum
from datetime import datetime
from sqlalchemy import DateTime, func, ForeignKey, CheckConstraint, text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from .base import Base


class BookingStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    expired = "expired"
    no_show = "no_show"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="RESTRICT"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"), server_default=text("'pending'")
    )

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_time_order"),
        CheckConstraint(
            "EXTRACT(MINUTE FROM start_time)::integer % 15 = 0 AND EXTRACT(SECOND FROM start_time) = 0",
            name="start_time_15_min_interval_check",
        ),
        CheckConstraint(
            "EXTRACT(MINUTE FROM end_time)::integer % 15 = 0 AND EXTRACT(SECOND FROM end_time) = 0",
            name="end_time_15_min_interval_check",
        ),
        ExcludeConstraint(
            ("room_id", "="),
            (func.tstzrange(start_time, end_time, "[)"), "&&"),
            name="no_overlapping_room_bookings",
            where=text("status IN ('pending', 'confirmed')"),
        ),
    )
