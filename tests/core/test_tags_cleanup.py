from datetime import datetime, timedelta
import pytest
from fastapi import status

def test_cleanup_stale_tags(client, test_user, db):
    """Test cleaning up stale tags (tags must have user_id now)"""
    from app.models.models import Tag

    # Create tags with different last_used_at dates for this user
    tags_data = [
        # Stale tags (no logs, old last_used_at)
        {"name": "stale_tag_1", "last_used_at": datetime.utcnow() - timedelta(days=40)},
        {"name": "stale_tag_2", "last_used_at": datetime.utcnow() - timedelta(days=35)},

        # Fresh tags (no logs, recent last_used_at)
        {"name": "fresh_tag_1", "last_used_at": datetime.utcnow() - timedelta(days=10)},
        {"name": "fresh_tag_2", "last_used_at": datetime.utcnow()}
    ]

    for data in tags_data:
        tag = Tag(
            user_id=test_user["user"].id,
            name=data["name"],
            last_used_at=data["last_used_at"]
        )
        db.add(tag)

    db.commit()

    # Get all tags to verify setup
    response = client.get("/api/tags", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    initial_tags = response.json()
    print(f"\nInitial tags: {len(initial_tags)}")

    # Try cleanup with 30 days threshold
    print("\nCleaning up tags older than 30 days...")
    response = client.delete(
        "/api/tags/cleanup",
        headers=test_user["headers"],
        params={"days": 30}
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    print(f"Cleanup result: {result['message']}")

    # Should have deleted 2 stale tags
    assert result["deleted_count"] == 2

    # Verify remaining tags
    response = client.get("/api/tags", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    remaining_tags = response.json()
    print(f"\nRemaining tags: {len(remaining_tags)}")

    # Should only have the 2 fresh tags left (plus any from test_log fixture)
    stale_tag_names = {"stale_tag_1", "stale_tag_2"}
    for tag in remaining_tags:
        assert tag["name"] not in stale_tag_names, f"Stale tag {tag['name']} should have been deleted" 