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

        if 'anti_motivation_mode' not in column_names:
            print('Adding anti_motivation_mode column...')
            cursor.execute('ALTER TABLE users ADD COLUMN anti_motivation_mode BOOLEAN DEFAULT 0 NOT NULL')
            print('✓ Added anti_motivation_mode column')
        else:
            print('✓ anti_motivation_mode column already exists')

        if 'mode' not in column_names:
            print('Adding mode column...')
            cursor.execute('ALTER TABLE users ADD COLUMN mode VARCHAR DEFAULT "ripped" NOT NULL')
            print('✓ Added mode column')

            # Set mode based on anti_motivation_mode and gender
            print('Setting mode values for existing users...')

            # Set 'shame' for users with anti_motivation_mode = true
            cursor.execute("UPDATE users SET mode = 'shame' WHERE anti_motivation_mode = 1")
            shame_count = cursor.rowcount

            # Set 'toned' for female users without anti_motivation_mode
            cursor.execute("UPDATE users SET mode = 'toned' WHERE gender = 'female' AND (anti_motivation_mode = 0 OR anti_motivation_mode IS NULL)")
            toned_count = cursor.rowcount

            # Set 'ripped' for male users without anti_motivation_mode
            cursor.execute("UPDATE users SET mode = 'ripped' WHERE gender = 'male' AND (anti_motivation_mode = 0 OR anti_motivation_mode IS NULL)")
            ripped_count = cursor.rowcount

            print(f'  - Set {shame_count} users to "shame" mode')
            print(f'  - Set {toned_count} female users to "toned" mode')
            print(f'  - Set {ripped_count} male users to "ripped" mode')
        else:
            print('✓ mode column already exists')

            # Update any NULL mode values based on gender/anti_motivation_mode
            print('Updating NULL mode values for existing users...')

            # Set 'shame' for users with anti_motivation_mode = true and NULL mode
            cursor.execute("UPDATE users SET mode = 'shame' WHERE anti_motivation_mode = 1 AND mode IS NULL")
            shame_count = cursor.rowcount

            # Set 'toned' for female users without anti_motivation_mode and NULL mode
            cursor.execute("UPDATE users SET mode = 'toned' WHERE gender = 'female' AND (anti_motivation_mode = 0 OR anti_motivation_mode IS NULL) AND mode IS NULL")
            toned_count = cursor.rowcount

            # Set 'ripped' for male users without anti_motivation_mode and NULL mode
            cursor.execute("UPDATE users SET mode = 'ripped' WHERE gender = 'male' AND (anti_motivation_mode = 0 OR anti_motivation_mode IS NULL) AND mode IS NULL")
            ripped_count = cursor.rowcount

            # Set 'ripped' as default for any remaining NULL values (no gender detected)
            cursor.execute("UPDATE users SET mode = 'ripped' WHERE mode IS NULL")
            default_count = cursor.rowcount

            if shame_count > 0 or toned_count > 0 or ripped_count > 0 or default_count > 0:
                print(f'  - Set {shame_count} users to "shame" mode')
                print(f'  - Set {toned_count} female users to "toned" mode')
                print(f'  - Set {ripped_count} male users to "ripped" mode')
                print(f'  - Set {default_count} users with no gender to "ripped" (default)')

        # Migrate generated_images table (only if it exists)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='generated_images'")
        table_exists = cursor.fetchone()

        if table_exists:
            cursor.execute("PRAGMA table_info(generated_images)")
            gen_images_columns = cursor.fetchall()
            gen_images_column_names = [col[1] for col in gen_images_columns]

            print(f"Current columns in generated_images table: {gen_images_column_names}")

            if 'mode' not in gen_images_column_names:
                print('Adding mode column to generated_images...')
                cursor.execute('ALTER TABLE generated_images ADD COLUMN mode VARCHAR')
                print('✓ Added mode column to generated_images')
            else:
                print('✓ mode column already exists in generated_images')
        else:
            print('generated_images table does not exist yet, will be created with correct schema')

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

        if 'anti_motivation_mode' not in column_names:
            print('Adding anti_motivation_mode column...')
            cursor.execute('ALTER TABLE users ADD COLUMN anti_motivation_mode BOOLEAN DEFAULT false NOT NULL')
            print('✓ Added anti_motivation_mode column')
        else:
            print('✓ anti_motivation_mode column already exists')

        if 'mode' not in column_names:
            print('Adding mode column...')
            cursor.execute('ALTER TABLE users ADD COLUMN mode VARCHAR DEFAULT \'ripped\' NOT NULL')
            print('✓ Added mode column')

            # Set mode based on anti_motivation_mode and gender
            print('Setting mode values for existing users...')

            # Set 'shame' for users with anti_motivation_mode = true
            cursor.execute("UPDATE users SET mode = 'shame' WHERE anti_motivation_mode = true")
            shame_count = cursor.rowcount

            # Set 'toned' for female users without anti_motivation_mode
            cursor.execute("UPDATE users SET mode = 'toned' WHERE gender = 'female' AND (anti_motivation_mode = false OR anti_motivation_mode IS NULL)")
            toned_count = cursor.rowcount

            # Set 'ripped' for male users without anti_motivation_mode
            cursor.execute("UPDATE users SET mode = 'ripped' WHERE gender = 'male' AND (anti_motivation_mode = false OR anti_motivation_mode IS NULL)")
            ripped_count = cursor.rowcount

            print(f'  - Set {shame_count} users to "shame" mode')
            print(f'  - Set {toned_count} female users to "toned" mode')
            print(f'  - Set {ripped_count} male users to "ripped" mode')
        else:
            print('✓ mode column already exists')

            # Update any NULL mode values based on gender/anti_motivation_mode
            print('Updating NULL mode values for existing users...')

            # Set 'shame' for users with anti_motivation_mode = true and NULL mode
            cursor.execute("UPDATE users SET mode = 'shame' WHERE anti_motivation_mode = true AND mode IS NULL")
            shame_count = cursor.rowcount

            # Set 'toned' for female users without anti_motivation_mode and NULL mode
            cursor.execute("UPDATE users SET mode = 'toned' WHERE gender = 'female' AND (anti_motivation_mode = false OR anti_motivation_mode IS NULL) AND mode IS NULL")
            toned_count = cursor.rowcount

            # Set 'ripped' for male users without anti_motivation_mode and NULL mode
            cursor.execute("UPDATE users SET mode = 'ripped' WHERE gender = 'male' AND (anti_motivation_mode = false OR anti_motivation_mode IS NULL) AND mode IS NULL")
            ripped_count = cursor.rowcount

            # Set 'ripped' as default for any remaining NULL values (no gender detected)
            cursor.execute("UPDATE users SET mode = 'ripped' WHERE mode IS NULL")
            default_count = cursor.rowcount

            if shame_count > 0 or toned_count > 0 or ripped_count > 0 or default_count > 0:
                print(f'  - Set {shame_count} users to "shame" mode')
                print(f'  - Set {toned_count} female users to "toned" mode')
                print(f'  - Set {ripped_count} male users to "ripped" mode')
                print(f'  - Set {default_count} users with no gender to "ripped" (default)')

        # Migrate generated_images table
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'generated_images'
        """)
        gen_images_columns = cursor.fetchall()
        gen_images_column_names = [col[0] for col in gen_images_columns]

        print(f"Current columns in generated_images table: {gen_images_column_names}")

        if 'mode' not in gen_images_column_names:
            print('Adding mode column to generated_images...')
            cursor.execute('ALTER TABLE generated_images ADD COLUMN mode VARCHAR')
            print('✓ Added mode column to generated_images')
        else:
            print('✓ mode column already exists in generated_images')

        conn.commit()
        cursor.close()
        conn.close()
        print('PostgreSQL database migration completed successfully!')

    except Exception as e:
        print(f"Error during PostgreSQL migration: {e}")
        raise


if __name__ == "__main__":
    migrate_database()
