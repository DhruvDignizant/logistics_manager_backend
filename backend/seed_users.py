"""
Database seeding script for initial users.

Creates ADMIN, HUB_OWNER, and FLEET_OWNER users for testing and development.
Run this script after database is set up but before first use.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.db.session import AsyncSessionLocal
from backend.app.models.user import User
from backend.app.models.enums import UserRole
from backend.app.core.security import get_password_hash
from sqlalchemy import select


async def seed_users():
    """
    Seed initial users with different roles.
    
    Creates:
    - 1 ADMIN user
    - 1 HUB_OWNER user  
    - 1 FLEET_OWNER user
    """
    async with AsyncSessionLocal() as db:
        print("🌱 Starting user seeding...")
        
        # Check if ADMIN already exists
        result = await db.execute(
            select(User).where(User.username == "admin")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print("ℹ️  ADMIN user already exists, skipping seeding")
            return
        
        # Create ADMIN
        admin_user = User(
            email="admin@logistics.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            fleet_owner_id=None,
            is_active=True,
            is_superuser=True
        )
        db.add(admin_user)
        print("✅ Created ADMIN user (username: admin, password: admin123)")
        
        # Create HUB OWNER
        hub_owner = User(
            email="hubowner@logistics.com",
            username="hubowner",
            hashed_password=get_password_hash("hub123"),
            role=UserRole.HUB_OWNER,
            fleet_owner_id=None,
            is_active=True,
            is_superuser=False
        )
        db.add(hub_owner)
        print("✅ Created HUB_OWNER user (username: hubowner, password: hub123)")
        
        # Create FLEET OWNER
        fleet_owner = User(
            email="fleetowner@logistics.com",
            username="fleetowner",
            hashed_password=get_password_hash("fleetowner123"),
            role=UserRole.FLEET_OWNER,
            is_active=True,
            is_superuser=False
        )
        db.add(fleet_owner)
        print("✅ Created FLEET_OWNER user (username: fleetowner, password: fleetowner123)")
        
        # Commit all users
        await db.commit()
        
        print("\n🎉 User seeding completed successfully!")
        print("\nSeeded users:")
        print("  - ADMIN:       admin / admin123")
        print("  - HUB_OWNER:   hubowner / hubowner123")
        print("  - FLEET_OWNER: fleetowner / fleetowner123")
        print("\nNote: DRIVER users register via POST /auth/register endpoint")


if __name__ == "__main__":
    asyncio.run(seed_users())
