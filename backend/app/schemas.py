from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["hardware", "software", "network", "consumables", "maintenance", "other"]
Priority = Literal["critical", "high", "medium", "low"]
Status = Literal["new", "processing", "manual_review", "open", "resolved", "duplicate", "failed"]


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=160)
    customer_email: str = Field(min_length=5, max_length=320)
    customer_phone: str | None = Field(default=None, max_length=64)
    device_type: str = Field(min_length=2, max_length=80)
    device_model: str | None = Field(default=None, max_length=120)
    description: str = Field(min_length=20, max_length=5000)


class TicketUpdate(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    assigned_to: str | None = None
    requires_manual_review: bool | None = None


class AIClassification(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(min_length=10, max_length=500)
    suggested_action: str = Field(min_length=10, max_length=800)
    confidence: float = Field(ge=0, le=1)
    requires_manual_review: bool


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    public_reference: str
    customer_name: str
    customer_email: str
    customer_phone: str | None
    device_type: str
    device_model: str | None
    description: str
    category: str
    priority: str
    status: str
    ai_summary: str | None
    suggested_action: str | None
    ai_confidence: float | None
    requires_manual_review: bool
    sla_due_at: datetime | None
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime


class TicketList(BaseModel):
    items: list[TicketRead]
    total: int
    page: int
    page_size: int


class TicketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ticket_id: UUID
    event_type: str
    source: str
    event_metadata: dict
    created_at: datetime


class AutomationRunCreate(BaseModel):
    workflow_name: str
    correlation_id: str
    ticket_id: UUID | None = None
    status: Literal["started", "completed", "failed", "retrying"]
    attempt: int = 1
    error_message: str | None = None


class AutomationRunRead(AutomationRunCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    started_at: datetime
    completed_at: datetime | None


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
