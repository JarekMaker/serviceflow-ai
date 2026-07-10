import time
import uuid
from datetime import datetime

import structlog
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import classify_safely
from app.core.config import settings
from app.core.logging import configure_logging, mask, request_id_ctx
from app.core.security import create_access_token, require_admin, verify_hmac_signature, verify_password
from app.db import get_session
from app.integrations import send_customer_email, send_telegram, store_attachment, validate_upload
from app.models import Attachment, AutomationRun, Ticket, TicketEvent, User
from app.schemas import (
    AutomationRunCreate,
    AutomationRunRead,
    LoginRequest,
    TicketCreate,
    TicketEventRead,
    TicketList,
    TicketRead,
    TicketUpdate,
    TokenResponse,
)
from app.services import add_event, create_ticket, list_tickets, record_automation_run, update_ticket

configure_logging()
log = structlog.get_logger()
app = FastAPI(title="ServiceFlow AI API", default_response_class=ORJSONResponse)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id", str(uuid.uuid4()))
    request_id_ctx.set(rid)
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    log.info("request", method=request.method, path=request.url.path, status=response.status_code, ms=round((time.perf_counter() - started) * 1000, 2))
    return response


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "serviceflow-ai"}


@app.get("/api/v1/ready")
async def ready(session: AsyncSession = Depends(get_session)):
    await session.execute(text("select 1"))
    return {"status": "ready"}


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = (await session.scalars(select(User).where(User.email == data.email))).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@app.post("/api/v1/tickets", response_model=TicketRead, status_code=201)
async def create_public_ticket(data: TicketCreate, session: AsyncSession = Depends(get_session)):
    ai = await classify_safely(data)
    ticket = await create_ticket(session, data, ai, source="public_form")
    await session.commit()
    await session.refresh(ticket)
    try:
        await send_customer_email(ticket)
        await send_telegram(ticket)
    except Exception as exc:
        log.warning("notification_failed", public_reference=ticket.public_reference, error=str(exc))
    log.info("ticket_created", public_reference=ticket.public_reference, customer_email=mask(ticket.customer_email))
    return ticket


@app.get("/api/v1/tickets", response_model=TicketList, dependencies=[Depends(require_admin)])
async def get_tickets(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    manual_review: bool | None = None,
    customer_email: str | None = None,
    public_reference: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "-created_at",
    session: AsyncSession = Depends(get_session),
):
    items, total = await list_tickets(session, locals(), page, min(page_size, 100), sort)
    return TicketList(
        items=[TicketRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/api/v1/tickets/{ticket_id}", response_model=TicketRead, dependencies=[Depends(require_admin)])
async def get_ticket(ticket_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.patch("/api/v1/tickets/{ticket_id}", response_model=TicketRead, dependencies=[Depends(require_admin)])
async def patch_ticket(ticket_id: uuid.UUID, data: TicketUpdate, session: AsyncSession = Depends(get_session)):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await update_ticket(session, ticket, data)
    await session.commit()
    await session.refresh(ticket)
    return ticket


@app.post("/api/v1/tickets/{ticket_id}/review", response_model=TicketRead, dependencies=[Depends(require_admin)])
async def review_ticket(ticket_id: uuid.UUID, data: TicketUpdate, session: AsyncSession = Depends(get_session)):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    data = data.model_copy(update={"requires_manual_review": False, "status": data.status or "open"})
    await update_ticket(session, ticket, data)
    await add_event(session, ticket.id, "manual_review_completed", "admin", {})
    await session.commit()
    await session.refresh(ticket)
    return ticket


@app.post("/api/v1/tickets/{ticket_id}/attachments", dependencies=[Depends(require_admin)])
async def upload_attachment(ticket_id: uuid.UUID, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    ticket = await session.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    content = await file.read()
    try:
        await validate_upload(file, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    object_key = f"tickets/{ticket.public_reference}/{uuid.uuid4()}-{file.filename}"
    await store_attachment(object_key, file, content)
    session.add(Attachment(ticket_id=ticket.id, object_key=object_key, original_filename=file.filename or "attachment", content_type=file.content_type or "application/octet-stream", size_bytes=len(content)))
    await add_event(session, ticket.id, "attachment_stored", "api", {"object_key": object_key})
    await session.commit()
    return {"object_key": object_key, "size_bytes": len(content)}


@app.get("/api/v1/tickets/{ticket_id}/events", response_model=list[TicketEventRead], dependencies=[Depends(require_admin)])
async def ticket_events(ticket_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(TicketEvent).where(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.created_at))).all()


@app.post("/api/v1/automation/classify")
async def classify_endpoint(request: Request, data: TicketCreate):
    if not verify_hmac_signature(await request.body(), request.headers.get("x-serviceflow-signature")):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    ai = await classify_safely(data)
    if not ai:
        raise HTTPException(status_code=503, detail="AI classification unavailable")
    return ai


@app.post("/api/v1/automation/runs", response_model=AutomationRunRead)
async def automation_runs(request: Request, data: AutomationRunCreate, session: AsyncSession = Depends(get_session)):
    if not verify_hmac_signature(await request.body(), request.headers.get("x-serviceflow-signature")):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    run = await record_automation_run(session, data)
    await session.commit()
    await session.refresh(run)
    return run


@app.get("/api/v1/automation/runs", response_model=list[AutomationRunRead], dependencies=[Depends(require_admin)])
async def get_automation_runs(session: AsyncSession = Depends(get_session)):
    return (await session.scalars(select(AutomationRun).order_by(AutomationRun.started_at.desc()).limit(100))).all()


@app.get("/api/v1/metrics", dependencies=[Depends(require_admin)])
async def metrics(session: AsyncSession = Depends(get_session)):
    tickets = await session.scalar(select(func.count(Ticket.id)))
    manual = await session.scalar(select(func.count(Ticket.id)).where(Ticket.requires_manual_review))
    return {"tickets_total": tickets or 0, "manual_review_total": manual or 0}
