"""
Migration script to create champions table
"""
from sqlalchemy import text
from app.database import engine

def run_migration():
    """Create the champions table"""
    try:
        with engine.connect() as conn:
            print("Creating champions table...")
            
            # Simple CREATE TABLE IF NOT EXISTS
            sql = """
            CREATE TABLE IF NOT EXISTS champions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                points INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
            # Adjust for SQLite/PostgreSQL differences if needed, but standard SQL usually works.
            # However, since we are likely using PostgreSQL (based on psycopg2 errors earlier),
            # 'SERIAL' is correct. Check if users table uses 'id' as integer.
            
            try:
                conn.execute(text(sql))
                conn.commit()
                print("✅ Champions table created successfully!")
            except Exception as e:
                print(f"Error creating table: {str(e)}")
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    run_migration()
