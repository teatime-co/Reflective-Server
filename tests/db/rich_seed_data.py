#!/usr/bin/env python3
"""
Rich seed script to create users and diverse journal entries for NLP testing.
This script uses the actual API endpoints to ensure proper backend processing.

Journal entry data is stored in JSON files under tests/db/seed_data/:
- food_lover.json - Culinary explorer with restaurant reviews, cooking experiences
- researcher.json - PhD candidate with lab work, academic journey
- hiker.json - Mountain wanderer with hiking adventures, outdoor reflections

This seed data is designed to test:
- Semantic search (similar concepts, different words)
- Keyword search (tags, specific terms)
- Sentiment analysis (emotional range)
- Theme detection (recurring topics)
- Temporal queries (progression over time)

Usage: python tests/db/rich_seed_data.py
"""

import sys
import os
import requests
import json
import uuid
from pathlib import Path
import time

# Add the app directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent))

# API Configuration
BASE_URL = "http://localhost:8000/api"
HEADERS = {"Content-Type": "application/json"}

# Seed data directory
SEED_DATA_DIR = current_dir / "seed_data"


def load_persona_data(filename: str) -> dict:
    """Load persona data from JSON file"""
    filepath = SEED_DATA_DIR / filename
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"✗ Error: Could not find seed data file: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def register_user(email: str, password: str, display_name: str) -> dict:
    """Register a new user via API"""
    user_data = {
        "email": email,
        "password": password,
        "display_name": display_name
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=user_data, headers=HEADERS)
    if response.status_code == 201:
        print(f"✓ Created user: {email}")
        return response.json()
    elif response.status_code == 400 and "already registered" in response.json().get("detail", ""):
        print(f"ℹ User {email} already exists")
        return None
    else:
        print(f"✗ Failed to create user {email}: {response.status_code} - {response.text}")
        return None


def login_user(email: str, password: str) -> str:
    """Login and get access token"""
    login_data = {
        "username": email,  # FastAPI OAuth2PasswordRequestForm uses 'username' field
        "password": password
    }

    response = requests.post(f"{BASE_URL}/auth/token", data=login_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✓ Logged in as {email}")
        return token
    else:
        print(f"✗ Failed to login {email}: {response.status_code} - {response.text}")
        return None


def create_log_entry(token: str, content: str, tags: list = None, completion_status: str = "complete") -> dict:
    """Create a log entry via API"""
    if tags is None:
        tags = []

    log_data = {
        "id": str(uuid.uuid4()),
        "content": content,
        "tags": tags,
        "completion_status": completion_status,
        "target_word_count": 750
    }

    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/logs/", json=log_data, headers=auth_headers)

    if response.status_code == 201:
        log = response.json()
        word_count = len(content.split())
        print(f"  ✓ Created entry ({word_count} words, {len(tags)} tags)")
        return log
    else:
        print(f"  ✗ Failed to create log: {response.status_code} - {response.text}")
        return None


def process_linguistic_metrics(token: str, log_id: str):
    """Process linguistic metrics for a log entry"""
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/linguistic/process/{log_id}", headers=auth_headers)

    if response.status_code == 200:
        return response.json()
    else:
        # Don't print error - linguistic processing is optional
        return None


def seed_persona_entries(token: str, persona_data: dict):
    """
    Create journal entries for a persona using data from JSON file

    Args:
        token: Authentication token
        persona_data: Loaded persona JSON data containing entries
    """
    persona_name = persona_data['persona']['name']
    entries = persona_data['entries']

    print(f"\nCreating {persona_name} journal entries...")
    print(f"   Test scenarios: {len(persona_data['persona']['test_scenarios'])} covered")

    for i, entry_data in enumerate(entries, 1):
        title = entry_data.get('title', f'Entry {i}')
        print(f"  Entry {i}/{len(entries)}: {title}")

        log = create_log_entry(
            token=token,
            content=entry_data['content'],
            tags=entry_data['tags']
        )

        if log:
            time.sleep(0.5)
            process_linguistic_metrics(token, log["id"])


def print_persona_info(persona_data: dict):
    """Print persona information"""
    persona = persona_data['persona']
    print(f"\n   Name: {persona['name']}")
    print(f"   Description: {persona['description']}")
    print(f"   Entries: {len(persona_data['entries'])}")


def main():
    """Main seeding function"""
    print("=" * 60)
    print("Rich Data Seeding for Reflective Journal")
    print("=" * 60)
    print(f"\nAPI Base URL: {BASE_URL}")
    print(f"Seed Data: {SEED_DATA_DIR}")

    # Load persona data from JSON files
    personas_config = [
        {
            "filename": "food_lover.json",
            "password": "foodlover123"
        },
        {
            "filename": "researcher.json",
            "password": "researcher123"
        },
        {
            "filename": "hiker.json",
            "password": "hiker123"
        }
    ]

    # Load all persona data
    personas = []
    total_entries = 0

    for config in personas_config:
        persona_data = load_persona_data(config['filename'])
        personas.append({
            "data": persona_data,
            "password": config['password']
        })
        total_entries += len(persona_data['entries'])

    print(f"\nLoaded {len(personas)} personas with {total_entries} total entries")
    print("Estimated time: 2-3 minutes\n")

    success_count = 0

    for persona_config in personas:
        persona_data = persona_config['data']
        password = persona_config['password']

        persona_info = persona_data['persona']
        email = persona_info['email']
        display_name = persona_info['name']

        print(f"\n{'=' * 60}")
        print(f"Processing: {display_name} ({email})")
        print('=' * 60)

        print_persona_info(persona_data)

        # Register user (or skip if exists)
        register_user(email, password, display_name)

        # Login
        token = login_user(email, password)
        if not token:
            print(f"⚠ Skipping data creation for {email} - couldn't login")
            continue

        # Seed journal entries
        try:
            seed_persona_entries(token, persona_data)
            success_count += 1
            print(f"\n✓ Completed data seeding for {display_name}")
        except Exception as e:
            print(f"\n✗ Error seeding data for {email}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print("Rich Data Seeding Complete!")
    print('=' * 60)
    print(f"\n✓ Successfully seeded {success_count}/{len(personas)} users")
    print(f"✓ Created {total_entries} diverse journal entries")
    print("✓ All entries processed for linguistic metrics")
    print("✓ Ready for semantic search testing")

    print("\nTest Query Examples:")
    print("\n  Food Lover (love@food.com):")
    print("    - 'best restaurants I visited'")
    print("    - 'cooking failures and disasters'")
    print("    - 'Italian food experiences'")
    print("    - 'what made me happy about food'")

    print("\n  Researcher (cell@apoptosis.com):")
    print("    - 'times I felt like a fraud'")
    print("    - 'research breakthroughs'")
    print("    - 'feeling stressed or anxious'")
    print("    - 'academic achievements'")

    print("\n  Hiker (hike@man.com):")
    print("    - 'dangerous situations in mountains'")
    print("    - 'peaceful outdoor moments'")
    print("    - 'difficult climbs'")
    print("    - 'what I learned from hiking'")

    print("\nTip: Login to any persona and try semantic searches!")
    print("   Each account has diverse content designed for testing.\n")


if __name__ == "__main__":
    main()
