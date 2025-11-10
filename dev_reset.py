#!/usr/bin/env python3
"""
Development Database Reset and Seed Utility

This script provides a convenient way to reset your development environment
and seed it with test users for frontend testing.

Usage:
    python dev_reset.py                    # Reset and create basic test users
    python dev_reset.py --skip-reset       # Only create users (don't reset DBs)
    python dev_reset.py --user-only EMAIL  # Create a single custom test user

Safety: This script will ONLY run in development mode. It checks:
    - DATABASE_URL must contain 'localhost' or '127.0.0.1'
    - Will prompt for confirmation before resetting

Test User Credentials:
    Email: test@example.com
    Password: testpass123
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import argparse
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.services.auth_service import create_user, get_user_by_email
from app.schemas.user import UserCreate
from app.models.models import Base

# Import reset functions
from tests.db.reset_dbs import reset_databases

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def check_development_environment() -> bool:
    """Verify we're running in a development environment"""
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "")

    # Check if database URL indicates local development
    is_local = any(host in db_url.lower() for host in ['localhost', '127.0.0.1', '@localhost/', '@127.0.0.1/'])

    if not is_local:
        print_error("SAFETY CHECK FAILED!")
        print_error(f"DATABASE_URL does not appear to be localhost: {db_url}")
        print_error("This script should only be run in development environments.")
        return False

    print_success(f"Development environment confirmed: {db_url}")
    return True

def confirm_reset() -> bool:
    """Ask user to confirm database reset"""
    print_warning("This will DELETE ALL DATA in your local databases (PostgreSQL + Weaviate)")
    response = input(f"{Colors.BOLD}Are you sure you want to continue? (yes/no): {Colors.ENDC}").strip().lower()
    return response in ['yes', 'y']

def create_test_user(db: Session, email: str, password: str, display_name: str) -> bool:
    """Create a single test user"""
    try:
        # Check if user exists
        existing = get_user_by_email(db, email)
        if existing:
            print_warning(f"User {email} already exists, skipping...")
            return False

        # Create user
        user_create = UserCreate(
            email=email,
            password=password,
            display_name=display_name,
            timezone="UTC",
            locale="en-US",
            daily_word_goal=750
        )

        user = create_user(db, user_create)
        print_success(f"Created user: {email} (ID: {user.id})")
        return True

    except Exception as e:
        print_error(f"Failed to create user {email}: {e}")
        return False

def seed_basic_users(db: Session) -> int:
    """Create basic test users"""
    print_header("Creating Test Users")

    users = [
        {
            "email": "test@example.com",
            "password": "testpass123",
            "display_name": "Test User"
        },
        {
            "email": "love@food.com",
            "password": "foodlover123",
            "display_name": "Culinary Explorer"
        },
        {
            "email": "cell@apoptosis.com",
            "password": "researcher123",
            "display_name": "Cell Biology Researcher"
        },
        {
            "email": "hike@man.com",
            "password": "hiker123",
            "display_name": "Mountain Wanderer"
        }
    ]

    created = 0
    for user_data in users:
        if create_test_user(db, **user_data):
            created += 1

    return created

def print_credentials():
    """Print test user credentials for easy reference"""
    print_header("Test User Credentials")
    print(f"""
{Colors.BOLD}Quick Test User:{Colors.ENDC}
  Email:    test@example.com
  Password: testpass123

{Colors.BOLD}Additional Test Accounts:{Colors.ENDC}
  Food Lover:
    Email:    love@food.com
    Password: foodlover123

  Cell Researcher:
    Email:    cell@apoptosis.com
    Password: researcher123

  Mountain Hiker:
    Email:    hike@man.com
    Password: hiker123

{Colors.BOLD}API Usage Example:{Colors.ENDC}
  POST http://localhost:8000/api/auth/token
  Body: {{"username": "test@example.com", "password": "testpass123"}}
""")

def main():
    parser = argparse.ArgumentParser(
        description="Reset development databases and seed test users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dev_reset.py                   # Full reset with basic users
  python dev_reset.py --skip-reset      # Only create users (no DB reset)
  python dev_reset.py --user-only EMAIL # Create a single custom test user
        """
    )

    parser.add_argument('--skip-reset', action='store_true',
                      help='Skip database reset, only create users')
    parser.add_argument('--user-only', metavar='EMAIL',
                      help='Create only a single test user with specified email')
    parser.add_argument('--no-confirm', action='store_true',
                      help='Skip confirmation prompt (use with caution)')

    args = parser.parse_args()

    # Safety check
    if not check_development_environment():
        sys.exit(1)

    print_header("Development Database Reset Utility")

    # Reset databases if not skipped
    if not args.skip_reset:
        if not args.no_confirm and not confirm_reset():
            print_info("Reset cancelled by user")
            sys.exit(0)

        print_header("Resetting Databases")
        if not reset_databases():
            print_error("Database reset failed!")
            sys.exit(1)
        print_success("Databases reset successfully!")
    else:
        print_info("Skipping database reset")

    # Create users
    db = SessionLocal()
    try:
        if args.user_only:
            # Create single custom user
            email = args.user_only
            password = input("Enter password (or press Enter for 'testpass123'): ").strip() or "testpass123"
            display_name = input("Enter display name (or press Enter for 'Test User'): ").strip() or "Test User"

            create_test_user(db, email, password, display_name)
            print_info(f"\nCredentials: {email} / {password}")

        else:
            # Create basic users
            created = seed_basic_users(db)
            print_success(f"\nCreated {created} test users")

        db.commit()

    except Exception as e:
        print_error(f"Error during user creation: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

    # Print credentials for reference
    if not args.user_only:
        print_credentials()

    print_success("\n✨ Development environment ready for testing!")

if __name__ == "__main__":
    main()
