import hmac
from hashlib import sha256

from app.core.security import verify_hmac_signature


def test_webhook_signature_valid() -> None:
    body = b'{"ok":true}'
    signature = hmac.new(b"dev-webhook-secret", body, sha256).hexdigest()
    assert verify_hmac_signature(body, f"sha256={signature}")


def test_webhook_signature_invalid() -> None:
    assert not verify_hmac_signature(b"body", "sha256=bad")
