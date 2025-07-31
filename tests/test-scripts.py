import sys
import os
import json
import requests
from typing import List
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas.query import SearchResult

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on a different port
SEARCH_ENDPOINT = f"{BASE_URL}/search"

def test_semantic_search(query: str, top_k: int = 5) -> List[SearchResult]:
    """
    Test the semantic search endpoint with the given query and parameters
    """
    params = {
        "query": query,
        "top_k": top_k
    }
    
    try:
        response = requests.post(SEARCH_ENDPOINT, params=params)
        response.raise_for_status()
        results = response.json()
        print(f"\n🔍 Search Results for query: '{query}' (top_k={top_k})")
        print(f"Found {len(results)} results")
        
        for idx, result in enumerate(results, 1):
            print(f"\nResult #{idx}")
            print(f"Relevance Score: {result['relevance_score']:.3f}")
            print(f"Log Content: {result['log_content']}")
            print("-" * 80)
            
        return results
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making request: {e}")
        return []

def run_test_suite():
    """
    Run a series of test cases for the semantic search functionality
    """
    print("🧪 Starting Semantic Search Test Suite")
    print("=" * 80)

    # Test Case 1: Basic search with default parameters
    print("\n📝 Test Case 1: Basic search")
    test_semantic_search("meditation practice")

    # Test Case 2: Search with specific tag-related content
    print("\n📝 Test Case 2: Search for entries with specific tags")
    test_semantic_search("mindfulness #meditation")

    # Test Case 3: Search with increased top_k
    print("\n📝 Test Case 3: Search with top_k=10")
    test_semantic_search("daily routine", top_k=10)

    # Test Case 4: Search for emotional content
    print("\n📝 Test Case 4: Search for emotional content")
    test_semantic_search("feeling grateful and happy")

    # Test Case 5: Search with minimum length query
    print("\n📝 Test Case 5: Minimum length query")
    test_semantic_search("a")  # Should trigger min_length validation

    # Test Case 6: Search with specific activity
    print("\n📝 Test Case 6: Activity-specific search")
    test_semantic_search("morning workout exercise")

if __name__ == "__main__":
    run_test_suite() 