import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimeMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models import Facility, StatusHistory, User


class RequestCategory(enum.StrEnum):
    EQUIPMENT = "equipment"
    ELECTRICITY = "electricity"
    PLUMBING = "plumbing"
    PREMISES = "premises"
    OTHER = "other"


class RequestPriority(enum.StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class RequestStatus(enum.StrEnum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ServiceRequest(UUIDMixin, TimeMixin, Base):
    __tablename__ = "service_requests"

    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[RequestCategory] = mapped_column(String(20), nullable=False)
    priority: Mapped[RequestPriority] = mapped_column(String(20), nullable=False)
    status: Mapped[RequestStatus] = mapped_column(String(20), nullable=False)
    assignee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    facility: Mapped["Facility"] = relationship(back_populates="service_requests")
    author: Mapped["User"] = relationship(
        back_populates="created_requests", foreign_keys=[author_id]
    )
    assignee: Mapped["User | None"] = relationship(
        back_populates="assigned_requests", foreign_keys=[assignee_id]
    )
    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="request",
        order_by="[StatusHistory.created_at, StatusHistory.id]",
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ('equipment', 'electricity', 'plumbing', 'premises', 'other')",
            name="category",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="priority",
        ),
        CheckConstraint(
            "status IN ('new', 'assigned', 'in_progress', 'completed', 'cancelled')",
            name="status",
        ),
        CheckConstraint(
            "char_length(trim(title)) BETWEEN 5 AND 200",
            name="title_length",
        ),
        CheckConstraint(
            "char_length(trim(description)) BETWEEN 10 AND 4000",
            name="description_length",
        ),
        CheckConstraint(
            "result IS NULL OR char_length(trim(result)) <= 4000",
            name="result_length",
        ),
        CheckConstraint(
            "cancellation_reason IS NULL OR char_length(trim(cancellation_reason)) <= 1000",
            name="cancellation_reason_length",
        ),
        Index("ix_service_requests_facility_created", "facility_id", "created_at"),
        Index("ix_service_requests_assignee_created", "assignee_id", "created_at"),
        Index("ix_service_requests_status_created", "status", "created_at"),
    )
