from pydantic import model_validator
from pydantic_settings import BaseSettings

DEFAULT_DEV_JWT_SECRET = "hostello-dev-secret-change-me"


class OperationalConfig(BaseSettings):
    # Core engine coefficient weights (HLD §7.2, constrained to sum to 1.0)
    W_PRICE: float = 0.40
    W_LOCATION: float = 0.40
    W_AMENITY: float = 0.20

    # Matching parameter slacks
    BUDGET_SLACK: float = 500.00
    CLEAN_BAND: int = 1

    # System scoring shifts
    PREMIUM_BOOST: float = 1.15
    VERIFIED_BOOST: float = 0.05

    # Security configuration bounds
    MAX_OTP_ATTEMPTS: int = 5
    OTP_WINDOW_SECONDS: int = 300

    # OTP delivery throttling (in-memory; single-worker deploy, HLD §7.3)
    OTP_MAX_SENDS_PER_WINDOW: int = 5

    # Deployment environment: "development" | "production". Production fails fast
    # on insecure defaults (mock auth, default JWT secret) — see the validator below.
    ENVIRONMENT: str = "development"

    # Comma-separated host allowlist for TrustedHostMiddleware (e.g. "hostello.onrender.com").
    ALLOWED_HOSTS: str = "*"

    # Auth / session
    JWT_SECRET: str = DEFAULT_DEV_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720

    # Persistence: SQLite locally, Neon Postgres in deploy (set DATABASE_URL on Render)
    DATABASE_URL: str = "sqlite:///./hostello.db"

    # Mocked external services (HLD A1/A2). Default OFF so production fails safe;
    # dev/test opt in explicitly (see tests/conftest.py).
    MOCK_OTP: bool = False
    MOCK_KYC: bool = False

    # Cloudinary (room images). When unset, uploads fall back to a local, gated store.
    CLOUDINARY_URL: str = ""

    # Upload hardening
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MiB

    # Built React bundle (Vite output). FastAPI serves index.html for non-API
    # routes and the hashed assets under <dist>/assets.
    FRONTEND_DIST: str = "frontend/dist"

    class Config:
        env_file = ".env"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() == "production"

    @property
    def cookie_secure(self) -> bool:
        """Session cookie gets the Secure flag everywhere except local dev/test."""
        return self.is_production

    @property
    def allowed_hosts(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()] or ["*"]

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "OperationalConfig":
        if self.is_production:
            problems = []
            if self.JWT_SECRET == DEFAULT_DEV_JWT_SECRET or len(self.JWT_SECRET) < 32:
                problems.append("JWT_SECRET must be set to a strong, non-default value")
            if self.MOCK_OTP:
                problems.append("MOCK_OTP must be false in production")
            if self.MOCK_KYC:
                problems.append("MOCK_KYC must be false in production")
            if problems:
                raise ValueError(
                    "Refusing to start in production with insecure config: "
                    + "; ".join(problems)
                )
        return self


config = OperationalConfig()

# Alias used by HLD listings / Dev B modules
CONFIG = config
