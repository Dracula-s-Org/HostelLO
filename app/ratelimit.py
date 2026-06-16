"""IP-based rate limiting (slowapi).

A DoS + SMS-toll-fraud defense layered on top of the per-phone OTP throttle: an
attacker rotating fake phone numbers bypasses the per-phone cap but not a
per-IP cap. Lives in its own module so routers can import `limiter` for their
decorators without a circular dependency on app.main.

The in-memory store matches the single-worker deploy (HLD §7.3). A multi-worker
deploy must point slowapi (and the OTP store) at Redis instead — see render.yaml.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import config


def client_ip(request: Request) -> str:
    """Behind Render the socket peer is the proxy, so trust the left-most
    X-Forwarded-For hop as the real client IP (single trusted proxy). Falls
    back to the socket address for direct/local connections.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=client_ip,
    default_limits=["100/minute"],
    enabled=config.RATE_LIMIT_ENABLED,
)
