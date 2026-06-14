from pydantic_settings import BaseSettings


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

    # Auth / session
    JWT_SECRET: str = "hostello-dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720

    # Persistence: SQLite locally, Neon Postgres in deploy (set DATABASE_URL on Render)
    DATABASE_URL: str = "sqlite:///./hostello.db"

    # Mocked external services (HLD A1/A2)
    MOCK_OTP: bool = True
    MOCK_KYC: bool = True

    # Cloudinary (room images). When unset, uploads fall back to local /static/uploads.
    CLOUDINARY_URL: str = ""

    class Config:
        env_file = ".env"


config = OperationalConfig()

# Alias used by HLD listings / Dev B modules
CONFIG = config
