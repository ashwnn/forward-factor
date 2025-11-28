#!/usr/bin/env python3
"""
User Provisioning Script

This script creates users directly in the database, bypassing registration requirements.
It creates users with default settings and optionally links Telegram chats.

Usage:
    python scripts/provision_users.py users.json
    
    Or with inline data:
    python scripts/provision_users.py --inline '[{"email": "user@example.com"}]'

Input Format (JSON):
[
    {
        "email": "user1@example.com",
        "password": "optional_password",  // If omitted, user can reset password later
        "telegram_chat_id": "123456789",  // Optional
        "telegram_username": "username",  // Optional
        "telegram_first_name": "John",    // Required if telegram_chat_id provided
        "telegram_last_name": "Doe"       // Optional
    },
    {
        "email": "user2@example.com"
    }
]
"""
import asyncio
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models import User, UserSettings
from app.models.telegram_chat import TelegramChat
from app.core.config import settings as app_settings
from app.services.auth_service import AuthService
from sqlalchemy import select


async def create_user(
    db,
    email: str,
    password: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
    telegram_username: Optional[str] = None,
    telegram_first_name: Optional[str] = None,
    telegram_last_name: Optional[str] = None
) -> User:
    """
    Create a user with default settings.
    
    Args:
        db: Database session
        email: User email
        password: Optional password (will be hashed)
        telegram_chat_id: Optional Telegram chat ID
        telegram_username: Optional Telegram username
        telegram_first_name: Optional Telegram first name (required if chat_id provided)
        telegram_last_name: Optional Telegram last name
        
    Returns:
        Created User object
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        print(f"⚠️  User {email} already exists (ID: {existing_user.id})")
        return existing_user
    
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        status="active",
        created_at=datetime.now(timezone.utc)
    )
    
    # Hash password if provided
    if password:
        user.password_hash = AuthService.hash_password(password)
    
    # Generate link code for Telegram linking
    user.link_code = AuthService.generate_link_code()
    
    db.add(user)
    await db.flush()
    
    # Create default settings
    user_settings = UserSettings(
        user_id=user.id,
        ff_threshold=app_settings.default_ff_threshold,
        min_open_interest=app_settings.default_min_open_interest,
        min_volume=app_settings.default_min_volume,
        max_bid_ask_pct=app_settings.default_max_bid_ask_pct,
        sigma_fwd_floor=app_settings.default_sigma_fwd_floor,
        stability_scans=app_settings.default_stability_scans,
        cooldown_minutes=app_settings.default_cooldown_minutes,
        timezone=app_settings.default_timezone,
        scan_priority="standard",
        discovery_mode=False
    )
    db.add(user_settings)
    
    # Create Telegram chat link if provided
    if telegram_chat_id:
        if not telegram_first_name:
            raise ValueError(f"telegram_first_name is required when telegram_chat_id is provided for {email}")
        
        telegram_chat = TelegramChat(
            user_id=user.id,
            chat_id=telegram_chat_id,
            username=telegram_username,
            first_name=telegram_first_name,
            last_name=telegram_last_name
        )
        db.add(telegram_chat)
    
    await db.commit()
    await db.refresh(user)
    
    return user


async def provision_users(users_data: List[Dict]) -> None:
    """
    Provision multiple users from a list of user data.
    
    Args:
        users_data: List of user dictionaries
    """
    async with AsyncSessionLocal() as db:
        created_count = 0
        skipped_count = 0
        
        for user_data in users_data:
            email = user_data.get("email")
            if not email:
                print("❌ Skipping user: email is required")
                skipped_count += 1
                continue
            
            try:
                user = await create_user(
                    db,
                    email=email,
                    password=user_data.get("password"),
                    telegram_chat_id=user_data.get("telegram_chat_id"),
                    telegram_username=user_data.get("telegram_username"),
                    telegram_first_name=user_data.get("telegram_first_name"),
                    telegram_last_name=user_data.get("telegram_last_name")
                )
                
                # Check if user was just created or already existed
                result = await db.execute(
                    select(User).where(User.id == user.id)
                )
                fresh_user = result.scalar_one()
                
                if fresh_user.created_at > datetime.now(timezone.utc).replace(microsecond=0):
                    # Just created
                    created_count += 1
                    print(f"✅ Created user: {email}")
                    print(f"   User ID: {user.id}")
                    print(f"   Link Code: {user.link_code}")
                    if user_data.get("telegram_chat_id"):
                        print(f"   Telegram: Linked to chat {user_data['telegram_chat_id']}")
                else:
                    # Already existed
                    skipped_count += 1
                    
            except Exception as e:
                print(f"❌ Error creating user {email}: {e}")
                skipped_count += 1
                continue
        
        print("\n" + "="*60)
        print(f"Summary:")
        print(f"  ✅ Created: {created_count}")
        print(f"  ⚠️  Skipped: {skipped_count}")
        print(f"  📊 Total: {len(users_data)}")
        print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Provision users in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From a JSON file
  python scripts/provision_users.py users.json
  
  # Inline JSON
  python scripts/provision_users.py --inline '[{"email": "test@example.com"}]'
  
  # With password
  python scripts/provision_users.py --inline '[{"email": "test@example.com", "password": "secret123"}]'
  
  # With Telegram
  python scripts/provision_users.py --inline '[{
    "email": "test@example.com",
    "telegram_chat_id": "123456789",
    "telegram_first_name": "John",
    "telegram_last_name": "Doe",
    "telegram_username": "johndoe"
  }]'
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "file",
        nargs="?",
        help="Path to JSON file containing user data"
    )
    group.add_argument(
        "--inline",
        help="Inline JSON string containing user data"
    )
    
    args = parser.parse_args()
    
    # Load user data
    try:
        if args.inline:
            users_data = json.loads(args.inline)
        else:
            with open(args.file, 'r') as f:
                users_data = json.load(f)
        
        if not isinstance(users_data, list):
            print("❌ Error: User data must be a JSON array")
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {args.file}")
        sys.exit(1)
    
    # Provision users
    print("🚀 Starting user provisioning...")
    print("="*60)
    asyncio.run(provision_users(users_data))


if __name__ == "__main__":
    main()
