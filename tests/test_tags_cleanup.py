from datetime import datetime, timedelta
import requests
import time

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def create_test_tags():
    """Create test tags with different last_used_at dates directly in the database"""
    from app.database import SessionLocal
    from app.models.models import Tag
    
    db = SessionLocal()
    try:
        # Create tags with different last_used_at dates
        tags_data = [
            # Stale tags (no logs, old last_used_at)
            {"name": "stale_tag_1", "last_used_at": datetime.utcnow() - timedelta(days=40)},
            {"name": "stale_tag_2", "last_used_at": datetime.utcnow() - timedelta(days=35)},
            
            # Fresh tags (no logs, recent last_used_at)
            {"name": "fresh_tag_1", "last_used_at": datetime.utcnow() - timedelta(days=10)},
            {"name": "fresh_tag_2", "last_used_at": datetime.utcnow()}
        ]
        
        for data in tags_data:
            tag = Tag(name=data["name"], last_used_at=data["last_used_at"])
            db.add(tag)
        
        db.commit()
        print("Created test tags successfully!")
        
    finally:
        db.close()

def test_cleanup():
    """Test the cleanup endpoint"""
    # First, get all tags to see what we have
    response = requests.get(f"{BASE_URL}/tags")
    if response.status_code == 200:
        print("\nInitial tags:")
        for tag in response.json():
            print(f"- {tag['name']}")
    
    # Try cleanup with 30 days threshold
    print("\nCleaning up tags older than 30 days...")
    response = requests.delete(f"{BASE_URL}/tags/cleanup?days=30")
    if response.status_code == 200:
        result = response.json()
        print(f"Cleanup result: {result['message']}")
    
    # Get remaining tags
    response = requests.get(f"{BASE_URL}/tags")
    if response.status_code == 200:
        print("\nRemaining tags:")
        for tag in response.json():
            print(f"- {tag['name']}")

if __name__ == "__main__":
    print("Creating test tags...")
    create_test_tags()
    
    print("\nWaiting for server to process changes...")
    time.sleep(2)
    
    print("\nTesting cleanup...")
    test_cleanup() 