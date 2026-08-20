from dataclasses import dataclass
from uuid import UUID

from app.models.service_request import (
    RequestCategory,
    RequestPriority,
    RequestStatus,
    ServiceRequest,
)


@dataclass(frozen=True)
class CreateRequestDTO:
    title: str
    description: str
    category: RequestCategory
    priority: RequestPriority


@dataclass(frozen=True)
class AssignRequestDTO:
    technician_id: UUID


@dataclass(frozen=True)
class CompleteRequestDTO:
    result: str


@dataclass(frozen=True)
class CancelRequestDTO:
    reason: str


@dataclass(frozen=True)
class ListRequestsFilterDTO:
    status: RequestStatus | None = None
    category: RequestCategory | None = None
    priority: RequestPriority | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class ListRequestsResultDTO:
    items: list[ServiceRequest]
    total: int
    limit: int
    offset: int
