"""
Database migration script to add selfie columns to existing users table
"""

import sqlite3
import os
from pathlib import Path


def migrate_database():
    """Add selfie columns to users table if they don't exist"""
    db_path = Path("motiv8.db")

    if not db_path.exists():
        print("Database doesn't exist yet, will be created with correct schema")
        return

    print(f"Found existing database at: {db_path.absolute()}")

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

        conn.commit()
        conn.close()
        print('Database migration completed successfully!')

    except Exception as e:
        print(f"Error during migration: {e}")
        raise


if __name__ == "__main__":
    migrate_database()
