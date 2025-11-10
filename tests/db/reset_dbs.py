import sys
import os

# Get the project root directory (where app/ is located)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import subprocess
from app.models.models import Base

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
            'users', 'tags', 'encrypted_metrics', 'encrypted_backups', 'sync_conflicts',
            'alembic_version'
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
    load_dotenv()

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

    print("\nDatabase has been reset successfully!")
    return True

if __name__ == "__main__":
    reset_databases()
