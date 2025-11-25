"""Core configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database
    database_url: str
    postgres_password: str  # Used by docker-compose.yml for PostgreSQL initialization
    postgres_port: int = 5432
    
    # Redis
    redis_url: str
    redis_port: int = 6379
    
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
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string to list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @model_validator(mode='after')
    def expand_database_url(self) -> 'Settings':
        """
        Expand ${POSTGRES_PASSWORD} in database_url if present.
        
        Pydantic Settings does NOT expand shell-style ${VARIABLE} references,
        so we manually replace them with the actual values after loading.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if '${POSTGRES_PASSWORD}' in self.database_url:
            original_url = self.database_url
            self.database_url = self.database_url.replace(
                '${POSTGRES_PASSWORD}',
                self.postgres_password
            )
            # Log expansion without exposing the password
            logger.debug(
                f"Expanded DATABASE_URL: password placeholder replaced "
                f"(password length: {len(self.postgres_password)} chars)"
            )
        else:
            logger.debug("DATABASE_URL: no password expansion needed")
        
        return self


# Global settings instance
settings = Settings()
