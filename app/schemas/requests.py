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
    model_config = {"extra": "forbid"}
    technician_id: UUID


class CompleteRequestSchema(BaseModel):
    model_config = {"extra": "forbid"}
    result: str = Field(min_length=5, max_length=4000)

    @field_validator("result", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()


class CancelRequestSchema(BaseModel):
    model_config = {"extra": "forbid"}
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()


class RequestFiltersSchema(BaseModel):
    status: RequestStatus | None = None
    category: RequestCategory | None = None
    priority: RequestPriority | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class RequestSummarySchema(BaseModel):
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


class RequestDetailSchema(RequestSummarySchema):
    description: str
    result: str | None
    cancellation_reason: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None


class StatusHistoryItemSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    old_status: RequestStatus | None
    new_status: RequestStatus
    changed_by: UUID
    comment: str | None
    created_at: datetime


class RequestDetailWithHistorySchema(RequestDetailSchema):
    history: list[StatusHistoryItemSchema]


class RequestListResponseSchema(BaseModel):
    items: list[RequestSummarySchema]
    limit: int
    offset: int
    total: int
