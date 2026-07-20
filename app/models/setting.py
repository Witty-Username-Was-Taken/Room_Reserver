from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    value: Mapped[str] = mapped_column()
    comment: Mapped[str | None] = mapped_column()
