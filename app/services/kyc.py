"""MockKycProvider (TDD A2): auto-returns VERIFIED behind a swappable interface."""
from app.config import config
from app.models import KycStatus


class KycProvider:
    def verify(self, doc_type: str, doc_ref: str) -> str:
        raise NotImplementedError


class MockKycProvider(KycProvider):
    def verify(self, doc_type: str, doc_ref: str) -> str:
        if config.MOCK_KYC:
            return KycStatus.VERIFIED.value
        # Non-mocked mode still has no real provider in MVP scope; stay PENDING
        return KycStatus.PENDING.value


kyc_provider: KycProvider = MockKycProvider()
