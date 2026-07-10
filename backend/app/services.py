import hashlib
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AutomationRun, Ticket, TicketEvent
from app.schemas import AIClassification, AutomationRunCreate, TicketCreate, TicketUpdate

SLA_HOURS = {"critical": 2, "high": 8, "medium": 24, "low": 72}


def normalize_description(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


def fingerprint(description: str) -> str:
    return hashlib.sha256(normalize_description(description).encode()).hexdigest()


def calculate_sla(priority: str, now: datetime | None = None) -> datetime:
    base = now or datetime.now(UTC)
    return base + timedelta(hours=SLA_HOURS[priority])


async def next_public_reference(session: AsyncSession) -> str:
    year = datetime.now(UTC).year
    count = await session.scalar(select(func.count(Ticket.id)))
    return f"SRV-{year}-{(count or 0) + 1:06d}"


async def detect_duplicate(session: AsyncSession, data: TicketCreate) -> Ticket | None:
    since = datetime.now(UTC) - timedelta(hours=settings.duplicate_window_hours)
    stmt = (
        select(Ticket)
        .where(Ticket.customer_email == data.customer_email)
        .where(Ticket.device_type == data.device_type)
        .where(Ticket.description_fingerprint == fingerprint(data.description))
        .where(Ticket.created_at >= since)
        .where(Ticket.status != "duplicate")
        .order_by(Ticket.created_at.desc())
    )
    return (await session.scalars(stmt)).first()


async def add_event(
    session: AsyncSession, ticket_id: UUID, event_type: str, source: str, metadata: dict | None = None
) -> None:
    session.add(
        TicketEvent(
            ticket_id=ticket_id,
            event_type=event_type,
            source=source,
            event_metadata=metadata or {},
        )
    )


async def create_ticket(
    session: AsyncSession, data: TicketCreate, ai: AIClassification | None, source: str = "api"
) -> Ticket:
    duplicate = await detect_duplicate(session, data)
    if duplicate:
        await add_event(session, duplicate.id, "duplicate_detected", source, {"reason": "fingerprint"})
        return duplicate

    priority = ai.priority if ai else "medium"
    manual = True if not ai else ai.requires_manual_review or ai.confidence < settings.ai_confidence_threshold
    ticket = Ticket(
        public_reference=await next_public_reference(session),
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        customer_phone=data.customer_phone,
        device_type=data.device_type,
        device_model=data.device_model,
        description=data.description,
        description_fingerprint=fingerprint(data.description),
        category=ai.category if ai else "other",
        priority=priority,
        status="manual_review" if manual else "open",
        ai_summary=ai.summary if ai else None,
        suggested_action=ai.suggested_action if ai else None,
        ai_confidence=ai.confidence if ai else None,
        requires_manual_review=manual,
        sla_due_at=calculate_sla(priority),
    )
    session.add(ticket)
    await session.flush()
    await add_event(session, ticket.id, "ticket_created", source, {"manual_review": manual})
    if manual:
        await add_event(session, ticket.id, "manual_review_required", "ai", {"threshold": settings.ai_confidence_threshold})
    return ticket


async def update_ticket(session: AsyncSession, ticket: Ticket, data: TicketUpdate) -> Ticket:
    before = {"status": ticket.status, "priority": ticket.priority}
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    if data.priority:
        ticket.sla_due_at = calculate_sla(data.priority)
    if data.status and data.status != before["status"]:
        await add_event(session, ticket.id, "status_changed", "admin", {"from": before["status"], "to": data.status})
    return ticket


async def list_tickets(session: AsyncSession, filters: dict, page: int, page_size: int, sort: str) -> tuple[list[Ticket], int]:
    stmt: Select = select(Ticket)
    for key in ["status", "priority", "category", "customer_email", "public_reference"]:
        if filters.get(key):
            stmt = stmt.where(getattr(Ticket, key) == filters[key])
    if filters.get("manual_review") is not None:
        stmt = stmt.where(Ticket.requires_manual_review == filters["manual_review"])
    if filters.get("created_from"):
        stmt = stmt.where(Ticket.created_at >= filters["created_from"])
    if filters.get("created_to"):
        stmt = stmt.where(Ticket.created_at <= filters["created_to"])
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    order_col = Ticket.created_at.desc() if sort == "-created_at" else Ticket.created_at.asc()
    items = (await session.scalars(stmt.order_by(order_col).offset((page - 1) * page_size).limit(page_size))).all()
    return list(items), int(total or 0)


async def record_automation_run(session: AsyncSession, data: AutomationRunCreate) -> AutomationRun:
    run = AutomationRun(**data.model_dump())
    if data.status in {"completed", "failed"}:
        run.completed_at = datetime.now(UTC)
    session.add(run)
    return run
