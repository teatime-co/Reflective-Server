#!/usr/bin/env python3

import sys
import os
from pathlib import Path
import requests
import json
from pprint import pprint
import time
from typing import List, Dict

# Configuration
API_BASE_URL = "http://localhost:8000/api"  # Adjust port if needed

def print_section(title):
    print(f"\n{'=' * 20} {title} {'=' * 20}")

# Helper function to make API requests
def api_request(method, endpoint, data=None, params=None):
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = getattr(requests, method.lower())(url, json=data, params=params)
        response.raise_for_status()
        return response.json() if response.text else None
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

# 1. Check if server is running
print_section("Server Check")
try:
    response = requests.get(f"{API_BASE_URL}/logs")
    print("Server is running and accessible")
except requests.exceptions.ConnectionError:
    print("Error: Cannot connect to the server. Please ensure it's running.")
    sys.exit(1)

# 2. Get initial statistics
print_section("Initial Statistics")
initial_logs = api_request("GET", "/logs")
total_logs = len(initial_logs) if initial_logs else 0
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
    result = api_request("POST", "/logs", data={"content": log["content"]})
    if result:
        test_ids.append(result["id"])
        print(f"Added test log with ID: {result['id']}")

time.sleep(1)  # Give server a moment to process

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
    results = api_request("POST", "/logs/search", params={"query": query})
    if results:
        for result in results:
            print(f"\nMatch (relevance score: {result.get('relevance_score', 0):.3f}):")
            print(f"Content: {result['content']}")
            print(f"Tags: {', '.join(result.get('tags', []))}")
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
    results = api_request("POST", "/logs/search", params={"query": query})
    if results:
        for result in results:
            print(f"\nMatch (relevance score: {result.get('relevance_score', 0):.3f}):")
            print(f"Content: {result['content']}")
            print(f"Tags: {', '.join(result.get('tags', []))}")
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
    results = api_request("GET", "/logs", params={"tag": tag})
    if results:
        print(f"Found {len(results)} logs with tag '{tag}':")
        for result in results:
            print("\n---")
            print(f"ID: {result['id']}")
            print(f"Content: {result['content']}")
            print(f"Tags: {', '.join(result.get('tags', []))}")
    else:
        print(f"No logs found with tag '{tag}'")

# 7. Clean up test data
print_section("Cleanup")
for test_id in test_ids:
    if api_request("DELETE", f"/logs/{test_id}"):
        print(f"Successfully deleted test log with ID: {test_id}")
    else:
        print(f"Failed to delete test log with ID: {test_id}")

print_section("Test Complete") 