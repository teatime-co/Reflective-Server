#!/usr/bin/env python3

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

from tests.reset_dbs import reset_databases
from app.database import SessionLocal
from app.models.models import Query as QueryModel, QueryResult as QueryResultModel

# Configuration
API_BASE_URL = "http://localhost:8000/api"  # Adjust if needed

def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 20} {title} {'=' * 20}")

class TestSearchEndpoints:
    @classmethod
    def setup_class(cls):
        """Reset databases before any tests run"""
        print_section("Resetting Databases")
        reset_databases()
        time.sleep(2)  # Give some time for services to stabilize
        
    def setup_method(self):
        """Setup test data before each test method"""
        # Test data
        self.test_logs = [
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
            },
            {
                "content": "The new testing framework I implemented last week is already proving its worth. Caught several edge cases in the registration flow that would have been hard to spot manually. The team's initial skepticism about the extra setup time has turned into appreciation for the time saved during QA. Feeling proud of pushing for this change despite the initial resistance. Need to remember that sometimes taking the longer path up front leads to better outcomes.",
                "tags": ["testing", "quality"]
            },
            {
                "content": "Today was all about optimization. The database queries that seemed fine during development are showing their limitations in production. Spent hours analyzing query plans and looking for opportunities to improve performance. It's fascinating how small changes in index usage can have such dramatic effects. The login time improved by 60% after implementing the changes. These are the kinds of wins that make the detailed analysis worth it.",
                "tags": ["performance", "database"]
            },
            {
                "content": "Mentoring our new team member has been a rewarding experience. Today we pair programmed through some complex state management issues in the frontend. Explaining the concepts helped me identify gaps in our documentation. It's amazing how teaching others forces you to question your own assumptions. Created some diagrams to better illustrate the data flow, which the whole team found helpful. Need to do more of this kind of knowledge sharing.",
                "tags": ["mentoring", "documentation"]
            },
            {
                "content": "The cross-team architecture meeting was eye-opening. Learning about how other teams handle similar challenges gave me new perspectives on our own solutions. The discussion about message queues and event-driven architecture was particularly relevant to our current scaling challenges. Started prototyping a new approach based on these insights. It's exciting to see how different parts of the system could work together more efficiently.",
                "tags": ["architecture", "collaboration"]
            },
            {
                "content": "Spent the day refactoring our error handling logic. What started as a simple cleanup turned into a deep dive into error patterns across the application. Created a more consistent approach to error messages and logging. The challenge was balancing informative error messages for debugging with user-friendly notifications. Added structured error logging that should make future troubleshooting much easier. Sometimes the unglamorous work is the most important.",
                "tags": ["refactoring", "maintenance"]
            },
            {
                "content": "Today's focus was on accessibility improvements. Conducted an audit of our main user flows using screen readers and keyboard navigation. The results were humbling - found several issues that make the application difficult for users with disabilities. Started implementing ARIA labels and improving keyboard focus indicators. This work reminds me that web development isn't just about making things work, but making them work for everyone.",
                "tags": ["accessibility", "inclusion"]
            },
            {
                "content": "The deployment automation scripts I've been working on finally came together today. What used to take hours of manual checking can now be done in minutes with better consistency. The challenge was handling environment-specific configurations without making the scripts too complex. Added detailed logging and rollback capabilities for when things go wrong. It's satisfying to build tools that make everyone's work easier.",
                "tags": ["automation", "devops"]
            },
            {
                "content": "Interesting day exploring different approaches to state management. The current Redux setup is showing its age, and the team is divided between Context API and newer solutions like Jotai. Spent time building proof-of-concept implementations with each option. The comparative analysis revealed some surprising performance implications. Need to consider the learning curve for the team alongside the technical benefits.",
                "tags": ["frontend", "architecture"]
            },
            {
                "content": "Today marked a significant milestone in our API modernization effort. Finally completed the transition from the old REST endpoints to the new GraphQL API. The journey has been challenging but rewarding. The new API is more flexible and efficient, though I'm a bit concerned about the learning curve for external developers. Started working on comprehensive documentation with interactive examples. Change is hard, but sometimes necessary for progress.",
                "tags": ["api", "documentation"]
            },
            {
                "content": "Experimented with different caching strategies today to improve application performance. The challenge lies in finding the right balance between data freshness and speed. Implemented a hybrid approach using both browser and server-side caching. The results are promising - page load times improved significantly for returning users. Still need to figure out the best invalidation strategy for real-time data. Sometimes the hardest part is knowing when to refresh the cache.",
                "tags": ["performance", "caching"]
            }
        ]
        
        # Store created log IDs for cleanup
        self.created_log_ids = []
        
        # Create test logs
        for log in self.test_logs:
            log_id = str(uuid4())
            response = requests.post(
                f"{API_BASE_URL}/logs/",
                json={
                    "id": log_id,
                    "content": log["content"],
                    "tags": log["tags"]
                }
            )
            assert response.status_code == 200, f"Failed to create test log: {response.text}"
            self.created_log_ids.append(log_id)
            
            # Verify the log was created with proper tags
            verify_response = requests.get(f"{API_BASE_URL}/logs/{log_id}")
            assert verify_response.status_code == 200, f"Failed to verify log: {verify_response.text}"
            created_log = verify_response.json()
            assert "tags" in created_log, "Log missing tags field"
            assert "weaviate_id" in created_log, "Log missing weaviate_id field"
            created_tags = {tag["name"] for tag in created_log["tags"]}
            expected_tags = set(log["tags"])
            assert created_tags == expected_tags, f"Tag mismatch. Expected: {expected_tags}, Got: {created_tags}"

        # Wait for embeddings to be processed
        time.sleep(2)

    def teardown_method(self):
        """Cleanup after each test method"""
        print("\nCleaning up test data...")
        reset_databases()
        time.sleep(1)  # Give some time for services to stabilize

    def test_semantic_search(self):
        """Test the main semantic search endpoint"""
        print_section("Testing Semantic Search")
        
        test_queries = [
            ("authentication and security implementation", 3),  # Auth system, login flow, and security practices
            ("team collaboration and mentoring", 3),  # Team retrospective, mentoring experience, and cross-team architecture meeting
            ("performance optimization work", 3),  # Database optimization, caching strategies, and performance issues discussion
            ("user interface and accessibility", 2),  # Dashboard redesign and accessibility improvements
            ("documentation and knowledge sharing", 3)  # API docs, mentoring documentation, and data flow diagrams
        ]
        
        for query, min_expected_results in test_queries:
            print(f"\nTesting query: '{query}' (expecting {min_expected_results} results)")
            response = requests.post(
                f"{API_BASE_URL}/search",
                params={"query": query, "top_k": 5}
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
                
                print(f"\n✅ Verified PostgreSQL persistence for query: '{query}'")
                print(f"Found {len(saved_results)} saved results")
            finally:
                db.close()

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
                params={"query": query, "top_k": 3}
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
        
        for query in initial_queries:
            requests.post(
                f"{API_BASE_URL}/search",
                params={"query": query, "top_k": 3}
            )
        
        # Wait for processing
        time.sleep(1)
        
        # Test partial queries
        test_partials = [
            "auth",
            "auto",
            "implementation"
        ]
        
        for partial in test_partials:
            print(f"\nGetting suggestions for: '{partial}'")
            response = requests.get(
                f"{API_BASE_URL}/search/suggest",
                params={
                    "partial_query": partial,
                    "limit": 5
                }
            )
            
            assert response.status_code == 200, "Suggestions request failed"
            suggestions = response.json()
            
            # Verify response structure
            assert isinstance(suggestions, list), "Suggestions should be a list"
            
            # Verify each suggestion
            for suggestion in suggestions:
                assert "query_text" in suggestion, "Suggestion missing query text"
                assert "result_count" in suggestion, "Suggestion missing result count"
                assert suggestion["query_text"].lower().startswith(partial.lower()), \
                    "Suggestion should start with partial query"
                
                print(f"\nSuggestion:")
                print(f"Query: {suggestion['query_text']}")
                print(f"Results: {suggestion['result_count']}")

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