from datetime import datetime
from uuid import UUID

import uuid_utils.compat as uuid
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class UUIDMixin(Base):
    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid7,
    )


class TimeMixin(Base):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
