from datetime import UTC, datetime

from app.ai import MockAIProvider
from app.schemas import TicketCreate
from app.services import calculate_sla, fingerprint


def test_sla_calculation() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert calculate_sla("critical", now).hour == 2
    assert calculate_sla("low", now).day == 4


def test_description_fingerprint_normalizes_text() -> None:
    assert fingerprint("Printer toner error!") == fingerprint("printer   toner error")


async def test_mock_ai_schema() -> None:
    ticket = TicketCreate(customer_name="A User", customer_email="a@example.com", device_type="printer", description="The printer has a toner error and is urgent for administration.")
    result = await MockAIProvider().classify(ticket)
    assert result.category == "consumables"
    assert result.confidence >= 0.75
