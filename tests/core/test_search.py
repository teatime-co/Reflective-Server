#!/usr/bin/env python3
"""
Integration tests for search endpoints.

These tests require:
1. Ollama running at http://localhost:11434
2. The server running at http://localhost:8000

To run these tests:
    pytest tests/core/test_search.py -v

Or skip them in CI:
    pytest -m "not integration"
"""

import requests
import pytest
from datetime import datetime
from typing import List, Dict
import time
from uuid import UUID, uuid4
from pydantic import UUID4
import sys
import os
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.db.reset_dbs import reset_databases
from app.database import SessionLocal
from app.models.models import Query as QueryModel, QueryResult as QueryResultModel

# Configuration
API_BASE_URL = "http://localhost:8000/api"  # Adjust if needed

def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 20} {title} {'=' * 20}")

@pytest.mark.integration
@pytest.mark.skip(reason="Integration test - requires Ollama and running server")
class TestSearchEndpoints:
    @classmethod
    def setup_class(cls):
        """Reset databases before any tests run"""
        print_section("Resetting Databases")
        reset_databases()
        time.sleep(2)  # Give some time for services to stabilize
        
    def setup_method(self):
        """Setup test data before each test method"""
        # Create test user and get access token
        self.test_user = {
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        
        # Register test user
        try:
            register_response = requests.post(
                f"{API_BASE_URL}/auth/register",
                json=self.test_user
            )
            if register_response.status_code not in [201, 400]:  # 400 means user exists
                raise Exception(f"Failed to register test user: {register_response.text}")
            print("Successfully registered test user or user already exists")
        except Exception as e:
            print(f"Registration error: {str(e)}")
            raise
        
        # Get access token using OAuth2 password flow
        try:
            token_response = requests.post(
                f"{API_BASE_URL}/auth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "password",
                    "username": self.test_user["email"],
                    "password": self.test_user["password"]
                }
            )
            if token_response.status_code != 200:
                raise Exception(f"Failed to get access token: {token_response.text}")
            
            self.access_token = token_response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.access_token}"}
            print(f"Successfully obtained access token")
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            raise

        # Default fields for all logs
        default_log_fields = {
            "mood_score": None,
            "completion_status": "draft",
            "target_word_count": 750,
            "writing_duration": None
        }

        # Test data
        base_logs = [
            {
                "content": "Started my morning feeling energized after finally getting a good night's sleep. The meditation practice I began last week is starting to show results - my mind feels clearer during work hours. Made significant progress on the user authentication system today, though I had to spend more time than expected reading documentation. The team seemed to appreciate my attention to detail during code review. Found myself explaining the security implications of different approaches, which helped solidify my own understanding. Ended the day with a sense of accomplishment, though I need to remember to take more breaks.",
                "tags": ["wellbeing", "work"]
            },
            {
                "content": "Today was challenging. Spent hours trying to figure out why the login flow wasn't working as expected. What initially looked like a simple token expiration issue turned out to be much more complex, involving race conditions I hadn't considered. The frustration led to some good learning though - documented everything I discovered about the system's behavior under load. Had a breakthrough around 4 PM when I realized we needed to handle concurrent requests differently. Sometimes the hardest bugs teach the most valuable lessons.",
                "tags": ["technical", "learning"]
            },
            {
                "content": "The team retrospective was particularly insightful today. We discussed the recent performance issues users have been experiencing during peak hours. While some suggested quick fixes, I advocated for a more thorough analysis of our database queries. Shared my observations about query patterns and suggested implementing caching at strategic points. It's satisfying when technical discussions lead to meaningful improvements in user experience. Looking forward to implementing these changes tomorrow.",
                "tags": ["teamwork", "planning"]
            },
            {
                "content": "Took a different approach to the dashboard redesign today. Instead of jumping straight into coding, I spent the morning sketching out user flows and thinking about the information hierarchy. It's amazing how stepping away from the computer can lead to better solutions. The new layout should make it much more intuitive for users to find what they need. Still need to figure out how to present the analytics data without overwhelming new users. Maybe progressive disclosure is the answer.",
                "tags": ["design", "ux"]
            },
            {
                "content": "Had an enlightening conversation with the security team about our current authentication practices. They raised concerns I hadn't considered about session management across different devices. Spent the afternoon researching industry best practices and modern approaches to secure session handling. It's humbling to realize how many edge cases we need to consider. Started drafting a proposal for implementing biometric authentication as an optional second factor. The complexity of security never ceases to amaze me.",
                "tags": ["security", "research"]
            }
        ]

        # Combine default fields with each log
        self.test_logs = []
        for base_log in base_logs:
            log = {**default_log_fields, **base_log}
            self.test_logs.append(log)
        
        # Store created log IDs for cleanup
        self.created_log_ids = []
        
        # Create test logs with authentication
        for log in self.test_logs:
            try:
                log_id = str(uuid4())
                log_data = {
                    "id": log_id,
                    **log  # Spread all log fields
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/logs/",
                    headers=self.headers,
                    json=log_data
                )
                
                if response.status_code != 201:  # Changed from 200 to 201 for creation
                    print(f"Response status: {response.status_code}")
                    print(f"Response body: {response.text}")
                    raise Exception(f"Failed to create test log: {response.text}")
                
                self.created_log_ids.append(log_id)
                print(f"Successfully created log with ID: {log_id}")
                
                # Verify the log was created with proper tags
                verify_response = requests.get(
                    f"{API_BASE_URL}/logs/{log_id}",
                    headers=self.headers
                )
                if verify_response.status_code != 200:
                    raise Exception(f"Failed to verify log: {verify_response.text}")
                
                created_log = verify_response.json()
                assert "tags" in created_log, "Log missing tags field"
                assert "weaviate_id" in created_log, "Log missing weaviate_id field"
                created_tags = {tag["name"] for tag in created_log["tags"]}
                expected_tags = set(log["tags"])
                assert created_tags == expected_tags, f"Tag mismatch. Expected: {expected_tags}, Got: {created_tags}"
                print(f"Successfully verified log {log_id} with tags: {created_tags}")
            except Exception as e:
                print(f"Error creating/verifying log: {str(e)}")
                raise

        # Wait for embeddings to be processed
        time.sleep(2)

    def teardown_method(self):
        """Cleanup after each test method"""
        print("\nCleaning up test data...")
        # Delete created logs
        for log_id in self.created_log_ids:
            try:
                requests.delete(
                    f"{API_BASE_URL}/logs/{log_id}",
                    headers=self.headers
                )
            except Exception as e:
                print(f"Error deleting log {log_id}: {str(e)}")
        
        reset_databases()
        time.sleep(1)  # Give some time for services to stabilize

    def test_semantic_search(self):
        """Test the main semantic search endpoint"""
        print_section("Testing Semantic Search")
        
        test_queries = [
            ("authentication and security implementation", 3),
            ("team collaboration and mentoring", 3),
            ("performance optimization work", 3),
            ("user interface and accessibility", 2),
            ("documentation and knowledge sharing", 3)
        ]
        
        for query, min_expected_results in test_queries:
            print(f"\nTesting query: '{query}' (expecting {min_expected_results} results)")
            try:
                response = requests.post(
                    f"{API_BASE_URL}/search",
                    headers=self.headers,
                    json={"query": query, "top_k": 5}
                )
                
                assert response.status_code == 200, f"Search request failed: {response.text}"
                results = response.json()
                
                # Verify response structure and minimum results
                assert isinstance(results, list), "Results should be a list"
                assert len(results) >= min_expected_results, (
                    f"Expected at least {min_expected_results} results, but got {len(results)}.\n"
                    f"Query: {query}\n"
                    f"Results: {[r['content'][:100] + '...' for r in results]}"
                )
                
                # Verify each result has required fields
                for result in results:
                    assert "content" in result, "Result missing content"
                    assert "relevance_score" in result, "Result missing relevance score"
                    assert "tags" in result, "Result missing tags"
                    assert "snippet_text" in result, "Result missing snippet"
                    assert 0 <= result["relevance_score"] <= 1, "Relevance score should be between 0 and 1"
                    
                    print(f"\nMatch (score: {result['relevance_score']:.3f}):")
                    print(f"Content: {result['content']}")
                    print(f"Tags: {', '.join(tag['name'] for tag in result['tags'])}")
                    print(f"Weaviate ID: {result.get('weaviate_id', 'Not available')}")

                # Verify data persistence in PostgreSQL
                db = SessionLocal()
                try:
                    # Verify query was saved
                    saved_query = db.query(QueryModel).filter(QueryModel.query_text == query).first()
                    assert saved_query is not None, f"Query '{query}' was not saved to PostgreSQL"
                    assert saved_query.result_count == len(results), "Saved result count doesn't match"
                    
                    # Verify query results were saved
                    saved_results = db.query(QueryResultModel).filter(
                        QueryResultModel.query_id == saved_query.id
                    ).all()
                    assert len(saved_results) == len(results), "Not all results were saved to PostgreSQL"
                    
                    # Verify result details
                    for saved_result in saved_results:
                        assert saved_result.relevance_score is not None, "Missing relevance score in saved result"
                        assert saved_result.snippet_text is not None, "Missing snippet text in saved result"
                        assert saved_result.rank > 0, "Invalid rank in saved result"
                    
                    print(f"\nVerified PostgreSQL persistence for query: '{query}'")
                    print(f"Found {len(saved_results)} saved results")
                finally:
                    db.close()
            except Exception as e:
                print(f"Error during semantic search test: {str(e)}")
                raise

    def test_similar_queries(self):
        """Test the similar queries endpoint"""
        print_section("Testing Similar Queries")
        
        # First make some searches to populate query history
        initial_queries = [
            "authentication system implementation",
            "security measures in auth",
            "frontend dashboard design",
            "database optimization techniques"
        ]
        
        for query in initial_queries:
            requests.post(
                f"{API_BASE_URL}/search",
                headers=self.headers,  # Add authentication headers
                json={"query": query, "top_k": 3}
            )
        
        # Wait for query embeddings to be processed
        time.sleep(1)
        
        # Test similar queries
        test_queries = [
            "how to implement auth",
            "security best practices",
            "UI design patterns",
            "database performance"
        ]
        
        for query in test_queries:
            print(f"\nFinding similar queries to: '{query}'")
            response = requests.get(
                f"{API_BASE_URL}/search/similar",
                headers=self.headers,  # Add authentication headers
                params={
                    "query": query,
                    "limit": 3,
                    "min_certainty": 0.5
                }
            )
            
            assert response.status_code == 200, "Similar queries request failed"
            results = response.json()
            
            # Verify response structure
            assert isinstance(results, list), "Results should be a list"
            
            # Verify each result
            for result in results:
                assert "query_text" in result, "Result missing query text"
                assert "result_count" in result, "Result missing result count"
                assert "created_at" in result, "Result missing timestamp"
                assert "relevance_score" in result, "Result missing relevance score"
                
                print(f"\nSimilar Query (score: {result['relevance_score']:.3f}):")
                print(f"Query: {result['query_text']}")
                print(f"Results: {result['result_count']}")

    def test_query_suggestions(self):
        """Test the query suggestions endpoint"""
        print_section("Testing Query Suggestions")
        
        # First make some searches to populate suggestion database
        initial_queries = [
            "authentication implementation",
            "auth system design",
            "authorization flow",
            "automated testing",
            "automation scripts"
        ]
        
        print("\nPopulating suggestion database with initial queries:")
        for query in initial_queries:
            print(f"  - {query}")
            requests.post(
                f"{API_BASE_URL}/search",
                headers=self.headers,  # Add authentication headers
                json={"query": query, "top_k": 3}
            )
        
        # Wait for processing
        time.sleep(1)
        
        # Test partial queries
        test_partials = [
            "auth",
            "auto",
            "implementation"
        ]
        
        print("\nTesting partial queries against initial queries:")
        for partial in test_partials:
            print(f"\nPartial query: '{partial}'")
            print("Checking against initial queries:")
            for initial in initial_queries:
                print(f"  - '{initial}': ", end="")
                if initial.lower().startswith(partial.lower()):
                    print("prefix match", end="")
                elif partial.lower() in initial.lower():
                    print("contains word", end="")
                else:
                    print("no match", end="")
                print()
                
            response = requests.get(
                f"{API_BASE_URL}/search/suggest",
                headers=self.headers,  # Add authentication headers
                params={
                    "partial_query": partial,
                    "limit": 5
                }
            )
            
            assert response.status_code == 200, "Suggestions request failed"
            suggestions = response.json()
            
            # Verify response structure
            assert isinstance(suggestions, list), "Suggestions should be a list"
            
            print("\nReceived suggestions:")
            # Verify each suggestion
            for suggestion in suggestions:
                assert "query_text" in suggestion, "Suggestion missing query text"
                assert "result_count" in suggestion, "Suggestion missing result count"
                # Allow both prefix matches and word containment
                query_text_lower = suggestion["query_text"].lower()
                partial_lower = partial.lower()
                assert (query_text_lower.startswith(partial_lower) or 
                       partial_lower in query_text_lower), \
                    "Suggestion should either start with or contain the partial query"
                
                print(f"  - Query: {suggestion['query_text']}")
                print(f"    Results: {suggestion['result_count']}")

def run_tests():
    """Run all tests"""
    test = TestSearchEndpoints()
    
    try:
        # Setup
        test.setup_method()
        
        # Run tests
        test.test_semantic_search()
        test.test_similar_queries()
        test.test_query_suggestions()
        print("\nAll tests completed successfully!")
        
    finally:
        # Cleanup
        # pass
        test.teardown_method()

if __name__ == "__main__":
    run_tests() 