import enum
from datetime import datetime
from sqlalchemy import DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Weekday(enum.Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"
    saturday = "Saturday"
    sunday = "Sunday"


class BuildingHours(Base):
    __tablename__ = "building_hours"

    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT"), primary_key=True
    )
    weekday: Mapped[Weekday] = mapped_column(primary_key=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
