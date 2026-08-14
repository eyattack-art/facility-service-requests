from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.mixins import TimeMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models import ServiceRequest, User


class Facility(UUIDMixin, TimeMixin, Base):
    __tablename__ = "facilities"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    users: Mapped[list["User"]] = relationship(back_populates="facility")
    service_requests: Mapped[list["ServiceRequest"]] = relationship(back_populates="facility")
