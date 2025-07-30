import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import shutil
import subprocess
from app.models.models import Base
from app.services.weaviate_rag_service import WeaviateRAGService
import time

def reset_weaviate(persistence_dir: str) -> bool:
    """Reset Weaviate database and verify it's clean
    
    Args:
        persistence_dir: Directory where Weaviate data is stored
        
    Returns:
        bool: True if reset was successful, False otherwise
    """
    try:
        # Delete the persistence directory if it exists
        if os.path.exists(persistence_dir):
            shutil.rmtree(persistence_dir)
            print("✅ Deleted existing Weaviate data directory")
        
        # Create a fresh Weaviate instance
        rag_service = WeaviateRAGService(persistence_dir=persistence_dir)
        
        # Ensure any existing schema is removed
        try:
            rag_service.client.schema.delete_all()
            print("✅ Cleaned up any existing Weaviate schema")
        except Exception as e:
            print(f"Note: No existing schema to clean up ({str(e)})")
        
        # Create fresh schema
        rag_service._ensure_schema()
        print("✅ Created fresh Weaviate schema")
        
        # Verify the database is empty
        result = (
            rag_service.client.query
            .aggregate(rag_service.class_name)
            .with_meta_count()
            .do()
        )
        count = result["data"]["Aggregate"][rag_service.class_name][0]["meta"]["count"]
        
        if count > 0:
            print(f"❌ Warning: Database not empty after reset! Found {count} objects")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error resetting Weaviate: {str(e)}")
        return False

def reset_databases():
    """Reset all databases to a clean state"""
    # Load environment variables
    load_dotenv()
    
    # Reset PostgreSQL
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/reflective")
    engine = create_engine(db_url)
    
    with engine.connect() as connection:
        # Drop and recreate all tables
        connection.execute(text("""
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO public;
        """))
        connection.commit()
        print("✅ PostgreSQL schema reset successfully!")
    
    # Run Alembic migrations
    alembic_ini = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'alembic.ini')
    try:
        subprocess.run(['alembic', '-c', alembic_ini, 'upgrade', 'head'], check=True)
        print("✅ Database migrations completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running migrations: {e}")
        return
    
    # Reset Embedded Weaviate
    persistence_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "weaviate-data")
    if reset_weaviate(persistence_dir):
        print("✅ Weaviate reset successfully!")
    else:
        print("❌ Error resetting Weaviate")
        return
        
    print("\n🎉 All databases have been reset!")

if __name__ == "__main__":
    reset_databases() 