"""SmsProvider interface + mock (TDD A1). Real SMS is out of MVP scope."""
import logging
import random

from app.config import config

logger = logging.getLogger("hostello.sms")

FIXED_DEV_OTP = "123456"


class SmsProvider:
    def send_otp(self, phone: str) -> str:
        """Send an OTP to `phone` and return the code the server should expect."""
        raise NotImplementedError


class MockSmsProvider(SmsProvider):
    """Emits the fixed dev code under MOCK_OTP, else a random logged code."""

    def send_otp(self, phone: str) -> str:
        code = FIXED_DEV_OTP if config.MOCK_OTP else f"{random.randint(0, 999999):06d}"
        logger.info("OTP for %s: %s", phone, code)
        return code


sms_provider: SmsProvider = MockSmsProvider()
