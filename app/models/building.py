from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    building_name: Mapped[str] = mapped_column()
