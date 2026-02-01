"""
Migration script to create event_messages table
"""
from sqlalchemy import text
from app.database import engine

def run_migration():
    """Create the event_messages table"""
    try:
        with engine.connect() as conn:
            print("Creating event_messages table...")
            
            sql = """
            CREATE TABLE IF NOT EXISTS event_messages (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (event_id) REFERENCES events(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
            
            try:
                conn.execute(text(sql))
                conn.commit()
                print("✅ Event messages table created successfully!")
            except Exception as e:
                print(f"Error creating table: {str(e)}")
                
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    run_migration()
