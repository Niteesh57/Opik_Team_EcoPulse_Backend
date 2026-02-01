"""
Migration script to make notification user columns nullable
"""
from sqlalchemy import text
from app.database import engine

def run_migration():
    """Alter notifications table to make user columns nullable"""
    try:
        with engine.connect() as conn:
            print("Altering notifications table...")
            
            # Alter to_user_id
            try:
                conn.execute(text("ALTER TABLE notifications ALTER COLUMN to_user_id DROP NOT NULL"))
                print("✅ to_user_id is now nullable")
            except Exception as e:
                print(f"Error altering to_user_id: {str(e)}")

            # Alter from_user_id
            try:
                conn.execute(text("ALTER TABLE notifications ALTER COLUMN from_user_id DROP NOT NULL"))
                print("✅ from_user_id is now nullable")
            except Exception as e:
                print(f"Error altering from_user_id: {str(e)}")
                
            conn.commit()
            print("Migration completed.")
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    run_migration()
