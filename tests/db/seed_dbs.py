import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime
from app.models.models import Base, Log, Tag
from app.services.weaviate_rag_service import WeaviateRAGService

def extract_tags(content: str) -> list[str]:
    """Extract hashtags from content"""
    tags = []
    words = content.split()
    for word in words:
        if word.startswith('#') and len(word) > 1:
            # Remove the # and any punctuation
            tag = word[1:].strip('.,!?')
            if tag:
                tags.append(tag)
    return tags

def get_or_create_tag(session, tag_name: str, tag_color: str = None) -> Tag:
    """Get existing tag or create a new one"""
    return Tag.get_or_create(session, tag_name, color=tag_color)

def seed_databases():
    # Load environment variables
    load_dotenv()
    
    # Setup PostgreSQL
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/reflective")
    engine = create_engine(db_url)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Initialize Weaviate RAG service
    persistence_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "weaviate-data")
    rag_service = WeaviateRAGService(persistence_dir=persistence_dir)
    
    # Read test data
    test_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'journal_entries_with_tags.jsonl')
    with open(test_data_path, 'r') as f:
        entries = [json.loads(line) for line in f if line.strip()]
    
    print(f"Found {len(entries)} entries to seed...")
    
    # Process each entry
    for entry in entries:
        try:
            # Extract tags
            tag_names = extract_tags(entry['content'])
            print(f"Processing entry with tags: {tag_names}")
            
            # Get or create tags, using colors from entry if available
            tag_objects = []
            for tag_name in tag_names:
                # Check if this tag has a color in the entry data
                tag_color = None
                if 'tags' in entry and tag_name in entry['tags']:
                    tag_color = entry['tags'][tag_name].get('color')
                
                tag = get_or_create_tag(session, tag_name, tag_color)
                tag_objects.append(tag)
            
            # Create log entry in PostgreSQL
            log = Log(
                id=entry['id'],
                content=entry['content'],
                created_at=datetime.fromisoformat(entry['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(entry['updated_at'].replace('Z', '+00:00')),
                word_count=entry['word_count'],
                processing_status='processed',
                tags=tag_objects
            )
            session.add(log)
            
            # Add to Weaviate with embeddings
            try:
                # Add to Weaviate using the RAG service
                weaviate_id = rag_service.add_log(entry['content'], tag_names)
                if weaviate_id:
                    # Update PostgreSQL log with Weaviate ID
                    log.weaviate_id = weaviate_id
                    session.flush()  # Flush changes but don't commit yet
                else:
                    print(f"Failed to add entry to Weaviate: {entry['id']}")
                
            except Exception as e:
                print(f"Error adding entry to Weaviate: {e}")
                session.rollback()
                continue
            
        except Exception as e:
            print(f"Error processing entry: {e}")
            session.rollback()
            continue
    
    try:
        session.commit()
        print("Successfully seeded PostgreSQL database!")
    except Exception as e:
        session.rollback()
        print(f"Error committing to PostgreSQL: {e}")
        return
    finally:
        session.close()

    print("\nAll databases have been seeded!")

if __name__ == "__main__":
    seed_databases() 