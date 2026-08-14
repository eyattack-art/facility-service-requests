import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
from app.models.mixins import TimeMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models import Facility, ServiceRequest, StatusHistory


class UserRole(enum.StrEnum):
    EMPLOYEE = "employee"
    TECHNICIAN = "technician"
    MANAGER = "manager"


class User(UUIDMixin, TimeMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False)
    facility_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    facility: Mapped["Facility | None"] = relationship(back_populates="users")
    created_requests: Mapped[list["ServiceRequest"]] = relationship(
        back_populates="author", foreign_keys="ServiceRequest.author_id"
    )
    assigned_requests: Mapped[list["ServiceRequest"]] = relationship(
        back_populates="assignee", foreign_keys="ServiceRequest.assignee_id"
    )
    changed_status_history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="changed_by_user", foreign_keys="StatusHistory.changed_by"
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('employee', 'technician', 'manager')",
            name="role",
        ),
        CheckConstraint(
            "(role = 'employee' AND facility_id IS NOT NULL) "
            "OR (role != 'employee' AND facility_id IS NULL)",
            name="facility_id_by_role",
        ),
    )
