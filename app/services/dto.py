from dataclasses import dataclass
from uuid import UUID

from app.models.service_request import RequestCategory, RequestPriority


@dataclass(frozen=True)
class CreateRequestDTO:
    title: str
    description: str
    category: RequestCategory
    priority: RequestPriority


@dataclass(frozen=True)
class AssignRequestDTO:
    technician_id: UUID
