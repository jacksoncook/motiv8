"""
Database migration script to add columns to existing users table
Supports both SQLite (development) and PostgreSQL (production)
"""

import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_database():
    """Add columns to users table if they don't exist"""
    # Check if using PostgreSQL (production) or SQLite (development)
    DB_HOST = os.getenv("DB_HOST")
    DB_USERNAME = os.getenv("DB_USERNAME")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    if DB_HOST and DB_USERNAME and DB_PASSWORD:
        # PostgreSQL migration
        migrate_postgresql()
    else:
        # SQLite migration
        migrate_sqlite()

def migrate_sqlite():
    """Migrate SQLite database"""
    db_path = Path("motiv8.db")

    if not db_path.exists():
        print("SQLite database doesn't exist yet, will be created with correct schema")
        return

    print(f"Found existing SQLite database at: {db_path.absolute()}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check current schema
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        print(f"Current columns in users table: {column_names}")

        # Add missing columns if they don't exist
        if 'selfie_filename' not in column_names:
            print('Adding selfie_filename column...')
            cursor.execute('ALTER TABLE users ADD COLUMN selfie_filename VARCHAR')
            print('✓ Added selfie_filename column')
        else:
            print('✓ selfie_filename column already exists')

        if 'selfie_embedding_filename' not in column_names:
            print('Adding selfie_embedding_filename column...')
            cursor.execute('ALTER TABLE users ADD COLUMN selfie_embedding_filename VARCHAR')
            print('✓ Added selfie_embedding_filename column')
        else:
            print('✓ selfie_embedding_filename column already exists')

        if 'workout_days' not in column_names:
            print('Adding workout_days column...')
            # Add workout_days as JSON column with default value
            default_workout_days = '{"monday": false, "tuesday": false, "wednesday": false, "thursday": false, "friday": false, "saturday": false, "sunday": false}'
            cursor.execute(f"ALTER TABLE users ADD COLUMN workout_days JSON DEFAULT '{default_workout_days}'")
            print('✓ Added workout_days column')
        else:
            print('✓ workout_days column already exists')

        if 'gender' not in column_names:
            print('Adding gender column...')
            cursor.execute('ALTER TABLE users ADD COLUMN gender VARCHAR')
            print('✓ Added gender column')
        else:
            print('✓ gender column already exists')

        conn.commit()
        conn.close()
        print('SQLite database migration completed successfully!')

    except Exception as e:
        print(f"Error during SQLite migration: {e}")
        raise

def migrate_postgresql():
    """Migrate PostgreSQL database"""
    import psycopg2

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME")
    DB_USERNAME = os.getenv("DB_USERNAME")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    print(f"Connecting to PostgreSQL database at {DB_HOST}...")

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USERNAME,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()

        # Check current schema
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
        """)
        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]

        print(f"Current columns in users table: {column_names}")

        # Add missing columns if they don't exist
        if 'selfie_filename' not in column_names:
            print('Adding selfie_filename column...')
            cursor.execute('ALTER TABLE users ADD COLUMN selfie_filename VARCHAR')
            print('✓ Added selfie_filename column')
        else:
            print('✓ selfie_filename column already exists')

        if 'selfie_embedding_filename' not in column_names:
            print('Adding selfie_embedding_filename column...')
            cursor.execute('ALTER TABLE users ADD COLUMN selfie_embedding_filename VARCHAR')
            print('✓ Added selfie_embedding_filename column')
        else:
            print('✓ selfie_embedding_filename column already exists')

        if 'workout_days' not in column_names:
            print('Adding workout_days column...')
            cursor.execute('ALTER TABLE users ADD COLUMN workout_days JSON')
            print('✓ Added workout_days column')
        else:
            print('✓ workout_days column already exists')

        if 'gender' not in column_names:
            print('Adding gender column...')
            cursor.execute('ALTER TABLE users ADD COLUMN gender VARCHAR')
            print('✓ Added gender column')
        else:
            print('✓ gender column already exists')

        conn.commit()
        cursor.close()
        conn.close()
        print('PostgreSQL database migration completed successfully!')

    except Exception as e:
        print(f"Error during PostgreSQL migration: {e}")
        raise


if __name__ == "__main__":
    migrate_database()
