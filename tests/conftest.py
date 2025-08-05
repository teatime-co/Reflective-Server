import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from typing import Generator, Dict
from datetime import datetime
from faker import Faker
import warnings

from app.main import app
from app.database import get_db, Base
from app.models.models import User
from app.services.auth_service import create_access_token, get_password_hash
from app.services.weaviate_rag_service import WeaviateRAGService

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Warn about using main database
if "reflective" in DATABASE_URL and "test" not in DATABASE_URL:
    warnings.warn(
        "\n"
        "⚠️  WARNING: Using main reflective database for testing!\n"
        "    All data will be cleared before and after tests.\n"
        "    Make sure this is what you want.\n",
        RuntimeWarning
    )

# Setup test database
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Setup test environment
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only"

fake = Faker()

def override_get_db():
    """Override the get_db dependency for testing"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        transaction.rollback()
        connection.close()

def reset_postgres_db():
    """Reset PostgreSQL database by dropping all tables and recreating them"""
    print("\n🗑️  Clearing all data from database...")
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database reset complete")

def reset_weaviate():
    """Reset Weaviate by deleting and recreating schema"""
    print("\n🗑️  Clearing Weaviate data...")
    rag_service = WeaviateRAGService()
    
    # Delete existing schema
    try:
        rag_service.client.schema.delete_all()
        print("✅ Weaviate schema deleted")
    except Exception as e:
        print(f"❌ Error deleting Weaviate schema: {e}")
    
    # Recreate schema
    try:
        # Add your schema recreation logic here
        # This should match your production schema creation
        rag_service.client.schema.create_class({
            "class": "Log",
            "vectorizer": "none",
            "vectorIndexConfig": {
                "distance": "cosine"
            },
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"]
                },
                {
                    "name": "tags",
                    "dataType": ["text[]"]
                },
                {
                    "name": "sql_id",
                    "dataType": ["text"]
                }
            ]
        })
        
        rag_service.client.schema.create_class({
            "class": "Query",
            "vectorizer": "none",
            "vectorIndexConfig": {
                "distance": "cosine"
            },
            "properties": [
                {
                    "name": "query_text",
                    "dataType": ["text"]
                },
                {
                    "name": "sql_id",
                    "dataType": ["text"]
                },
                {
                    "name": "result_count",
                    "dataType": ["int"]
                },
                {
                    "name": "execution_time",
                    "dataType": ["number"]
                },
                {
                    "name": "created_at",
                    "dataType": ["date"]
                }
            ]
        })
        print("✅ Weaviate schema recreated")
    except Exception as e:
        print(f"❌ Error recreating Weaviate schema: {e}")

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Reset both PostgreSQL and Weaviate before running tests"""
    print("\n🧪 Setting up test environment...")
    reset_postgres_db()
    reset_weaviate()
    yield
    # Cleanup after all tests
    print("\n🧹 Cleaning up test environment...")
    reset_postgres_db()
    reset_weaviate()
    print("✅ Test cleanup complete")

@pytest.fixture(autouse=True)
def cleanup_after_test(db):
    """Clean up database after each test"""
    yield
    
    # Only rollback, don't close the session here
    db.rollback()

@pytest.fixture
def db() -> Generator:
    """Get test database session"""
    # Create a new session for each test
    connection = engine.connect()
    # Begin a non-ORM transaction
    transaction = connection.begin()
    
    # Configure the session with the connection
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        # Rollback any pending changes
        session.rollback()
        # Close the session
        session.close()
        # Rollback the transaction
        transaction.rollback()
        # Close the connection
        connection.close()

@pytest.fixture
def client(db) -> TestClient:
    """Get test client with database dependency override"""
    def override_get_db_for_test():
        try:
            yield db
        finally:
            pass  # Let the db fixture handle cleanup
    
    app.dependency_overrides[get_db] = override_get_db_for_test
    yield TestClient(app)
    app.dependency_overrides.clear()  # Clean up the override after the test

@pytest.fixture
def test_user(db) -> Dict:
    """Create a test user and return user data with tokens"""
    password = "testpassword123"
    user_data = {
        "email": fake.email(),
        "display_name": fake.name(),
        "password": password,
        "timezone": "UTC",
        "locale": "en-US",
        "daily_word_goal": 750,
    }
    
    db_user = User(
        email=user_data["email"],
        display_name=user_data["display_name"],
        hashed_password=get_password_hash(password),
        timezone=user_data["timezone"],
        locale=user_data["locale"],
        daily_word_goal=user_data["daily_word_goal"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(db_user.id), "email": db_user.email}
    )
    
    return {
        "user": db_user,
        "access_token": access_token,
        "token_type": "bearer",
        "password": password,
        "headers": {"Authorization": f"Bearer {access_token}"}
    }

@pytest.fixture
def test_user2(db) -> Dict:
    """Create a second test user for testing user isolation"""
    password = "testpassword456"
    user_data = {
        "email": fake.email(),
        "display_name": fake.name(),
        "password": password,
        "timezone": "UTC",
        "locale": "en-US",
        "daily_word_goal": 500,
    }
    
    db_user = User(
        email=user_data["email"],
        display_name=user_data["display_name"],
        hashed_password=get_password_hash(password),
        timezone=user_data["timezone"],
        locale=user_data["locale"],
        daily_word_goal=user_data["daily_word_goal"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    access_token = create_access_token(
        data={"sub": str(db_user.id), "email": db_user.email}
    )
    
    return {
        "user": db_user,
        "access_token": access_token,
        "token_type": "bearer",
        "password": password,
        "headers": {"Authorization": f"Bearer {access_token}"}
    } 

@pytest.fixture
def test_log(client, test_user, db) -> Dict:
    """Create a test log with a tag and return it"""
    from app.models.models import Log, Tag
    import uuid
    
    # Create a test tag
    tag = Tag(
        name=f"test_tag_{uuid.uuid4().hex[:8]}",
        color="#FF0000",
        created_at=datetime.utcnow(),
        last_used_at=datetime.utcnow()
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    
    # Create a test log with the tag
    log = Log(
        id=uuid.uuid4(),
        user_id=test_user["user"].id,
        content="Test log content",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        tags=[tag],
        word_count=3,
        processing_status="processed"
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return {
        "id": log.id,
        "content": log.content,
        "tags": [{
            "id": tag.id,  # This is already a UUID from the database
            "name": tag.name,
            "color": tag.color,
            "created_at": tag.created_at
        }]
    } 