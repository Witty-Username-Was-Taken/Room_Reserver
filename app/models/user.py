import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class UserRole(enum.Enum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str | None] = mapped_column()
    last_name: Mapped[str | None] = mapped_column()
    email: Mapped[str] = mapped_column()
    password_hash: Mapped[str] = mapped_column()
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        server_default=text("'user'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (Index("uq_users_email_lower", func.lower(email), unique=True),)
