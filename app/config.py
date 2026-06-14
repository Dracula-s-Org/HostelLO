from pydantic_settings import BaseSettings

class OperationalConfig(BaseSettings):
    # Core engine calculation coefficient weights [cite: 796]
    W_PRICE: float = 0.40 [cite: 797]
    W_LOCATION: float = 0.40 [cite: 798]
    W_AMENITY: float = 0.20 [cite: 799]
    
    # Matching parameter slack values [cite: 800]
    BUDGET_SLACK: float = 50.00 [cite: 818]
    CLEAN_BAND: int = 1 [cite: 818]
    
    # System evaluation score adjustments [cite: 819]
    PREMIUM_BOOST: float = 1.15 [cite: 820]
    VERIFIED_BOOST: float = 0.05 [cite: 821]

    class Config:
        env_file = ".env" [cite: 826]

config = OperationalConfig() [cite: 827]