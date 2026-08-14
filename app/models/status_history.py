from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.mixins import TimeMixin, UUIDMixin
from app.models.service_request import RequestStatus

if TYPE_CHECKING:
    from app.models import ServiceRequest, User


class StatusHistory(UUIDMixin, TimeMixin, Base):
    __tablename__ = "status_history"

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("service_requests.id", ondelete="RESTRICT"), nullable=False
    )
    old_status: Mapped[RequestStatus | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[RequestStatus] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    request: Mapped["ServiceRequest"] = relationship(back_populates="history")
    changed_by_user: Mapped["User"] = relationship(foreign_keys=[changed_by])

    __table_args__ = (
        CheckConstraint(
            "old_status IS NULL OR old_status IN "
            "('new', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name="old_status",
        ),
        CheckConstraint(
            "new_status IN ('new', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name="new_status",
        ),
        CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 1000",
            name="comment_length",
        ),
    )
