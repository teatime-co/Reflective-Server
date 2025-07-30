#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import weaviate
from pprint import pprint
import time
from typing import List, Dict
from app.services.weaviate_rag_service import WeaviateRAGService
from reset_dbs import reset_databases

def print_section(title):
    print(f"\n{'=' * 20} {title} {'=' * 20}")

# Reset all databases and initialize services
print_section("Database Reset")
reset_databases()

# Initialize the RAG service with clean database
rag_service = WeaviateRAGService(persistence_dir="./weaviate-data")

# 1. Check Schema
print_section("Schema Check")
schema = rag_service.client.schema.get()
pprint(schema)

# 2. Get initial statistics
print_section("Initial Statistics")
stats = rag_service.client.query.aggregate("Log").with_meta_count().do()
total_logs = stats["data"]["Aggregate"]["Log"][0]["meta"]["count"]
print(f"Total logs in database: {total_logs}")

# 3. Add test logs
print_section("Adding Test Logs")
test_logs = [
    {
        "content": "Just finished implementing a new authentication system using JWT tokens. The integration with our React frontend was smooth. #development #auth",
        "tags": ["development", "auth"]
    },
    {
        "content": "Today's meeting about security measures was productive. We discussed implementing 2FA and password policies. #security #meeting",
        "tags": ["security", "meeting"]
    },
    {
        "content": "Debugging the authentication flow in the login system. Found an issue with token expiration. #debug #auth",
        "tags": ["debug", "auth"]
    },
    {
        "content": "Working on the UI design for our dashboard. Added new charts and improved the layout. #frontend #design",
        "tags": ["frontend", "design"]
    },
    {
        "content": "Optimized database queries for the user authentication system. Reduced login time by 50%. #performance #database",
        "tags": ["performance", "database"]
    }
]

test_ids = []
for log in test_logs:
    test_id = rag_service.add_log(log["content"], log["tags"])
    if test_id:
        test_ids.append(test_id)
        print(f"Added test log with ID: {test_id}")

time.sleep(1)  # Give Weaviate a moment to process

# 4. Test semantic search with various queries
print_section("Semantic Search Tests")

test_queries = [
    "authentication implementation details",
    "security measures and 2FA",
    "frontend UI improvements",
    "database performance optimization",
    "debugging authentication issues",
    "meeting discussions",
    "React frontend development",
]

for query in test_queries:
    print(f"\nSearching for: '{query}'")
    results = rag_service.semantic_search(query, limit=3)
    if results:
        for result in results:
            print(f"\nMatch (relevance score: {result['relevance_score']:.3f}):")
            print(f"Content: {result['content']}")
            print(f"Tags: {', '.join(result['tags'])}")
    else:
        print("No results found")

# 5. Test semantic search with conceptually related but differently worded queries
print_section("Conceptual Similarity Tests")

conceptual_queries = [
    "user login system",  # Should match authentication-related entries
    "web interface updates",  # Should match UI/frontend entries
    "system speed improvements",  # Should match performance optimization
    "bug fixes in user system",  # Should match debugging entries
    "team discussions about protection",  # Should match security meeting
]

for query in conceptual_queries:
    print(f"\nSearching for: '{query}'")
    results = rag_service.semantic_search(query, limit=3)
    if results:
        for result in results:
            print(f"\nMatch (relevance score: {result['relevance_score']:.3f}):")
            print(f"Content: {result['content']}")
            print(f"Tags: {', '.join(result['tags'])}")
    else:
        print("No results found")

# 6. Test tag-based search
print_section("Tag-Based Search Tests")
tag_tests = [
    "auth",      # Should match multiple entries
    "frontend",  # Should match UI-related entry
    "security",  # Should match security meeting entry
    "nonexistent"  # Should return empty results
]

for tag in tag_tests:
    print(f"\nSearching for logs with tag: '{tag}'")
    results = rag_service.get_logs_by_tag(tag)
    if results:
        print(f"Found {len(results)} logs with tag '{tag}':")
        for result in results:
            print("\n---")
            print(f"ID: {result['id']}")
            print(f"Content: {result['content']}")
            print(f"Tags: {', '.join(result['tags'])}")
    else:
        print(f"No logs found with tag '{tag}'")

# 7. Clean up test data
print_section("Cleanup")
for test_id in test_ids:
    if rag_service.delete_log(test_id):
        print(f"Successfully deleted test log with ID: {test_id}")
    else:
        print(f"Failed to delete test log with ID: {test_id}")

print_section("Test Complete") 