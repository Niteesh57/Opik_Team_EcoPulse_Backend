"""
Migration script to change event_image_url to TEXT type
"""
from sqlalchemy import text
from app.database import engine

def run_migration():
    """Alter events table to change event_image_url type to TEXT"""
    try:
        with engine.connect() as conn:
            print("Altering events table...")
            
            try:
                # Alter column type to TEXT (PostgreSQL specific, but widely supported as TEXT or similar)
                conn.execute(text("ALTER TABLE events ALTER COLUMN event_image_url TYPE TEXT"))
                print("✅ event_image_url column type changed to TEXT")
            except Exception as e:
                print(f"Error altering column: {str(e)}")
                
            conn.commit()
            print("Migration completed.")
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    run_migration()
