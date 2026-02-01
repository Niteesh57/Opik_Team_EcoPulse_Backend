"""
Migration script to add lang column to users table
"""
from sqlalchemy import text
from app.database import engine

def run_migration():
    """Alter users table to add lang column"""
    try:
        with engine.connect() as conn:
            print("Altering users table...")
            
            try:
                # Add lang column
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS lang VARCHAR DEFAULT 'en'"))
                print("✅ lang column added to users table")
            except Exception as e:
                print(f"Error adding lang column: {str(e)}")
                
            conn.commit()
            print("Migration completed.")
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    run_migration()
