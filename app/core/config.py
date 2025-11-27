"""Core configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator, field_validator
from typing import Optional, List


# Valid log levels
VALID_LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/ffbot.db"
    
    # Redis (redis_url should contain full connection string including port)
    redis_url: str
    
    # Telegram
    telegram_bot_token: str
    invite_code: str
    
    # API Keys
    polygon_api_key: str
    
    # Scan Cadence (minutes)
    scan_cadence_high: int = 3
    scan_cadence_medium: int = 15
    scan_cadence_low: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    # Default Settings
    default_ff_threshold: float = 0.20
    default_sigma_fwd_floor: float = 0.05
    default_min_open_interest: int = 100
    default_min_volume: int = 10
    default_max_bid_ask_pct: float = 0.08
    default_stability_scans: int = 2
    default_cooldown_minutes: int = 120
    default_timezone: str = "America/Vancouver"
    
    # JWT Authentication
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Registration Control
    registration_enabled: bool = True  # Set to False to disable new user registrations
    
    # Frontend Configuration
    frontend_url: str = "http://localhost:3000"
    frontend_port: int = 3000
    
    # API Configuration
    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"
    
    # CORS Configuration
    cors_origins: str = "http://localhost:3000"  # Comma-separated list of allowed origins
    
    # Default Admin Account
    admin_email: Optional[str] = None  # If set, creates admin account on startup
    admin_password: Optional[str] = None
    
    # Rate Limiting
    rate_limit_login: str = "5/minute"  # Login attempts per minute
    rate_limit_register: str = "3/minute"  # Registration attempts per minute
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        upper_v = v.upper()
        if upper_v not in VALID_LOG_LEVELS:
            raise ValueError(f"log_level must be one of {VALID_LOG_LEVELS}")
        return upper_v
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string to list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @model_validator(mode='after')
    def validate_config(self) -> 'Settings':
        """Validate configuration after all fields are set."""
        # Validate JWT secret strength
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT secret must be at least 32 characters for security")
        return self


# Global settings instance
settings = Settings()
