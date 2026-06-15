"""SmsProvider interface + mock (TDD A1). Real SMS is out of MVP scope."""
import logging
import secrets

from app.config import config

logger = logging.getLogger("hostello.sms")

FIXED_DEV_OTP = "123456"


def _mask(phone: str) -> str:
    return phone[:3] + "****" + phone[-2:] if len(phone) >= 5 else "****"


class SmsProvider:
    def send_otp(self, phone: str) -> str:
        """Send an OTP to `phone` and return the code the server should expect."""
        raise NotImplementedError


class MockSmsProvider(SmsProvider):
    """Dev/test provider. Under MOCK_OTP it returns the fixed dev code; otherwise
    it generates a cryptographically-random code. The code is NEVER logged or
    returned to the client — production must wire a real delivery integration.
    """

    def send_otp(self, phone: str) -> str:
        if config.MOCK_OTP:
            # Dev/test only: a known code, logged at DEBUG with a masked phone.
            logger.debug("Mock OTP issued for %s", _mask(phone))
            return FIXED_DEV_OTP
        # No real SMS integration in MVP scope: a real code is generated (so the
        # store stays consistent) but cannot be delivered. Never logged.
        logger.info("OTP requested for %s (delivery provider not configured)", _mask(phone))
        return f"{secrets.randbelow(1_000_000):06d}"


sms_provider: SmsProvider = MockSmsProvider()
