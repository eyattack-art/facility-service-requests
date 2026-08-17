from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.service_request import RequestCategory, RequestPriority, RequestStatus


class CreateRequestSchema(BaseModel):
    model_config = {"extra": "forbid"}
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    category: RequestCategory
    priority: RequestPriority

    @field_validator("title", "description", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()


class AssignRequestSchema(BaseModel):
    """Тело POST /requests/{id}/assign"""

    model_config = {"extra": "forbid"}
    technician_id: UUID


class RequestListItemSchema(BaseModel):
    """Краткая заявка в GET /requests (п.8)"""

    model_config = {"from_attributes": True}
    id: UUID
    facility_id: UUID
    author_id: UUID
    title: str
    category: RequestCategory
    priority: RequestPriority
    status: RequestStatus
    assignee_id: UUID | None
    created_at: datetime
    updated_at: datetime


class RequestCardSchema(RequestListItemSchema):
    description: str
    result: str | None
    cancellation_reason: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None
