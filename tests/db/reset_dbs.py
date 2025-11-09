import sys
import os

# Get the project root directory (where app/ is located)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import shutil
import subprocess
from app.models.models import Base, Log, Tag, Query, QueryResult
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
        if os.path.exists(persistence_dir):
            shutil.rmtree(persistence_dir)
            print("Deleted existing Weaviate data directory")
        
        # Create a fresh Weaviate instance
        rag_service = WeaviateRAGService(persistence_dir=persistence_dir)
        
        try:
            rag_service.client.schema.delete_all()
            print("Cleaned up any existing Weaviate schema")
        except Exception as e:
            print(f"Note: No existing schema to clean up ({str(e)})")

        rag_service._ensure_schema()
        print("Created fresh Weaviate schema")
        
        # Verify both Log and Query classes are empty
        for class_name in [rag_service.log_class, rag_service.query_class]:
            result = (
                rag_service.client.query
                .aggregate(class_name)
                .with_meta_count()
                .do()
            )
            count = result["data"]["Aggregate"][class_name][0]["meta"]["count"]

            if count > 0:
                print(f"Warning: Class {class_name} not empty after reset! Found {count} objects")
                return False
            
        return True

    except Exception as e:
        print(f"Error resetting Weaviate: {str(e)}")
        return False

def verify_postgres_tables(engine) -> bool:
    """Verify that all expected tables exist and are empty
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        bool: True if verification passes, False otherwise
    """
    try:
        inspector = inspect(engine)
        expected_tables = {
            'logs', 'tags', 'queries', 'query_results', 'tag_log',
            'alembic_version'  # Include Alembic version table
        }
        
        actual_tables = set(inspector.get_table_names())
        missing_tables = expected_tables - actual_tables
        if missing_tables:
            print(f"Missing tables: {missing_tables}")
            return False

        with engine.connect() as conn:
            for table in actual_tables - {'alembic_version'}:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if result > 0:
                    print(f"Table '{table}' is not empty: {result} rows")
                    return False
                    
        return True

    except Exception as e:
        print(f"Error verifying PostgreSQL tables: {str(e)}")
        return False

def reset_postgres(engine) -> bool:
    """Reset PostgreSQL database
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        bool: True if reset was successful, False otherwise
    """
    try:
        Base.metadata.drop_all(engine)
        print("Dropped all tables successfully!")

        Base.metadata.create_all(engine)
        print("Recreated all tables successfully!")

        return True

    except Exception as e:
        print(f"Error resetting PostgreSQL: {str(e)}")
        return False

def reset_databases():
    """Reset all databases to a clean state"""
    # Load environment variables
    load_dotenv()
    
    # Initialize PostgreSQL connection
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/reflective")
    engine = create_engine(db_url)
    
    if not reset_postgres(engine):
        print("Failed to reset PostgreSQL")
        return False

    alembic_ini = os.path.join(project_root, 'alembic.ini')
    try:
        subprocess.run(['alembic', '-c', alembic_ini, 'upgrade', 'head'], check=True)
        print("Database migrations completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")
        return False

    if not verify_postgres_tables(engine):
        print("PostgreSQL verification failed")
        return False

    persistence_dir = os.path.join(project_root, "weaviate-data")
    if not reset_weaviate(persistence_dir):
        print("Error resetting Weaviate")
        return False

    print("\nAll databases have been reset successfully!")
    return True

if __name__ == "__main__":
    reset_databases() 