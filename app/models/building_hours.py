import enum
from datetime import time
from sqlalchemy import ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Weekday(enum.Enum):
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"
    Saturday = "Saturday"
    Sunday = "Sunday"


class BuildingHours(Base):
    __tablename__ = "building_hours"

    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT"), primary_key=True
    )
    weekday: Mapped[Weekday] = mapped_column(
        Enum(Weekday, name="weekday"), primary_key=True
    )
    start_time: Mapped[time] = mapped_column()
    end_time: Mapped[time] = mapped_column()
