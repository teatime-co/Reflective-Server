import pytest
from fastapi import status
from faker import Faker

fake = Faker()

def test_register_user(client):
    """Test user registration"""
    user_data = {
        "email": fake.email(),
        "display_name": fake.name(),
        "password": "testpassword123",
        "timezone": "UTC",
        "locale": "en-US",
        "daily_word_goal": 750
    }
    
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["display_name"] == user_data["display_name"]
    assert "password" not in data
    assert "hashed_password" not in data

def test_register_duplicate_email(client, test_user):
    """Test registration with existing email"""
    user_data = {
        "email": test_user["user"].email,  # Use existing email
        "display_name": fake.name(),
        "password": "testpassword123",
        "timezone": "UTC",
        "locale": "en-US",
        "daily_word_goal": 750
    }
    
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in response.json()["detail"]

def test_login_success(client, test_user):
    """Test successful login"""
    login_data = {
        "username": test_user["user"].email,
        "password": test_user["password"]
    }
    
    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, test_user):
    """Test login with wrong password"""
    login_data = {
        "username": test_user["user"].email,
        "password": "wrongpassword"
    }
    
    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]

def test_login_nonexistent_user(client):
    """Test login with non-existent user"""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "testpassword123"
    }
    
    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]

def test_protected_route_with_token(client, test_user):
    """Test accessing protected route with valid token"""
    response = client.get("/api/users/me", headers=test_user["headers"])
    print('right here boss', response)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user["user"].email

def test_protected_route_without_token(client):
    """Test accessing protected route without token"""
    response = client.get("/api/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"]

def test_protected_route_invalid_token(client):
    """Test accessing protected route with invalid token"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"] 