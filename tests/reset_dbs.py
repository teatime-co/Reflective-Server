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

def reset_databases():
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
        print(f"Error running migrations: {e}")
        return
    
    # Reset Embedded Weaviate
    persistence_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "weaviate-data")
    
    # Delete the persistence directory if it exists
    if os.path.exists(persistence_dir):
        shutil.rmtree(persistence_dir)
        print("✅ Deleted existing Weaviate data directory")
    
    # Create a fresh Weaviate instance and schema
    rag_service = WeaviateRAGService(persistence_dir=persistence_dir)
    print("✅ Recreated Weaviate schema")
    print("\n🎉 All databases have been reset!")

if __name__ == "__main__":
    reset_databases() 