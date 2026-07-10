import smtplib
from email.message import EmailMessage

import aioboto3
import httpx
from fastapi import UploadFile

from app.core.config import settings
from app.models import Ticket


async def send_customer_email(ticket: Ticket) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = ticket.customer_email
    message["Subject"] = f"Service request {ticket.public_reference} received"
    message.set_content(
        f"Hello {ticket.customer_name},\n\nYour request {ticket.public_reference} was received. "
        f"Current priority: {ticket.priority}.\n\nServiceFlow AI"
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def send_telegram(ticket: Ticket) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    text = f"{ticket.public_reference}: {ticket.priority.upper()} {ticket.device_type} - {ticket.ai_summary or ticket.description[:120]}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
        )
        response.raise_for_status()


async def validate_upload(file: UploadFile, content: bytes) -> None:
    if file.content_type not in settings.allowed_content_types:
        raise ValueError("Unsupported attachment type")
    if len(content) > settings.max_attachment_mb * 1024 * 1024:
        raise ValueError("Attachment too large")


async def store_attachment(object_key: str, file: UploadFile, content: bytes) -> None:
    endpoint = settings.minio_endpoint
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    ) as client:
        buckets = await client.list_buckets()
        if settings.minio_bucket not in {bucket["Name"] for bucket in buckets.get("Buckets", [])}:
            await client.create_bucket(Bucket=settings.minio_bucket)
        await client.put_object(
            Bucket=settings.minio_bucket,
            Key=object_key,
            Body=content,
            ContentType=file.content_type or "application/octet-stream",
        )
