"""Core configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
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
    postgres_port: int = 5432
    
    # Redis
    redis_url: str
    redis_port: int = 6379
    
    # Telegram
    telegram_bot_token: str
    
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
    
    # Frontend Configuration
    frontend_url: str = "http://localhost:3000"
    frontend_port: int = 3000
    
    # API Configuration
    backend_port: int = 8000
    backend_url: str = "http://localhost:8000"


# Global settings instance
settings = Settings()
