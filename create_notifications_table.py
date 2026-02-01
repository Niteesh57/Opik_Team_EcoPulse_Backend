"""
Migration script to create notifications table
"""
from sqlalchemy import text
from app.database import engine

def run_migration():
    """Create the notifications table"""
    try:
        with engine.connect() as conn:
            print("Creating notifications table...")
            
            sql = """
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                value INTEGER DEFAULT 0,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (from_user_id) REFERENCES users(id),
                FOREIGN KEY (to_user_id) REFERENCES users(id)
            );
            """
            
            try:
                conn.execute(text(sql))
                conn.commit()
                print("✅ Notifications table created successfully!")
            except Exception as e:
                print(f"Error creating table: {str(e)}")
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    run_migration()
