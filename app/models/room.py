from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT")
    )
    title: Mapped[str | None] = mapped_column()
    room_num: Mapped[str] = mapped_column()
    room_type: Mapped[str] = mapped_column()
    capacity: Mapped[int] = mapped_column()
