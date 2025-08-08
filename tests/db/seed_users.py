#!/usr/bin/env python3
"""
Seed script to create initial users in the reflective app database.
Usage: python seed_users.py
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
current_dir = Path(__file__).parent
app_dir = current_dir / "app"
sys.path.insert(0, str(app_dir))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.services.auth_service import create_user, get_user_by_email
from app.schemas.user import UserCreate
from app.models.models import Base

def create_tables():
    """Create database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

def seed_users():
    """Create seed users."""
    # Create a database session
    db: Session = SessionLocal()
    
    try:
        # Define the users to create
        users_data = [
            {
                "email": "love@food.com",
                "password": "123456",
                "display_name": "Food Lover"
            },
            {
                "email": "cell@apoptosis.com", 
                "password": "123456",
                "display_name": "Cell Researcher"
            },
            {
                "email": "hike@man.com",
                "password": "123456", 
                "display_name": "Hiking Enthusiast"
            }
        ]
        
        created_count = 0
        
        for user_data in users_data:
            # Check if user already exists
            existing_user = get_user_by_email(db, user_data["email"])
            if existing_user:
                print(f"User with email {user_data['email']} already exists, skipping...")
                continue
            
            # Create UserCreate object
            user_create = UserCreate(
                email=user_data["email"],
                password=user_data["password"],
                display_name=user_data["display_name"]
            )
            
            # Create the user
            try:
                user = create_user(db, user_create)
                print(f"Created user: {user.email} (ID: {user.id})")
                created_count += 1
            except Exception as e:
                print(f"Error creating user {user_data['email']}: {e}")
        
        print(f"\nSeed completed! Created {created_count} new users.")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting user seeding...")
    
    # Ensure tables exist
    create_tables()
    
    # Seed users
    seed_users()
    
    print("Seeding complete!") 