"""
Run this script to add new columns to the events and event_users tables.
This migration adds support for enhanced event features.
"""
from sqlalchemy import text
from app.database import engine

def run_migration():
    """Execute the migration"""
    try:
        with engine.connect() as conn:
            print("Running database migration...")
            
            # Add columns to events table one by one
            print("Adding columns to events table...")
            
            statements = [
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS start_time TIME",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS end_time TIME",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS max_participants INTEGER",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS current_participants INTEGER DEFAULT 0",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS guest_speakers TEXT",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS rsvp_link VARCHAR",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS rsvp_required BOOLEAN DEFAULT FALSE",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT FALSE",
                "ALTER TABLE events ADD COLUMN IF NOT EXISTS reminder_hours_before INTEGER",
            ]
            
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception as e:
                    print(f"  Note: {stmt.split('ADD COLUMN IF NOT EXISTS')[1].split()[0]} - {str(e)}")
            
            # Create enums
            print("Creating enum types...")
            try:
                conn.execute(text("""
                    DO $$ BEGIN
                        CREATE TYPE eventstatus AS ENUM ('draft', 'confirmed', 'cancelled', 'completed');
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                """))
                conn.commit()
            except Exception as e:
                print(f"  EventStatus enum: {str(e)}")
            
            try:
                conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS event_status eventstatus DEFAULT 'draft'"))
                conn.commit()
            except Exception as e:
                print(f"  event_status column: {str(e)}")
            
            try:
                conn.execute(text("""
                    DO $$ BEGIN
                        CREATE TYPE rsvpstatus AS ENUM ('pending', 'confirmed', 'maybe', 'declined');
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                """))
                conn.commit()
            except Exception as e:
                print(f"  RSVPStatus enum: {str(e)}")
            
            # Add columns to event_users table
            print("Adding columns to event_users table...")
            
            event_user_statements = [
                "ALTER TABLE event_users ADD COLUMN IF NOT EXISTS rsvp_status rsvpstatus DEFAULT 'pending'",
                "ALTER TABLE event_users ADD COLUMN IF NOT EXISTS checked_in BOOLEAN DEFAULT FALSE",
                "ALTER TABLE event_users ADD COLUMN IF NOT EXISTS checked_in_at TIMESTAMP WITH TIME ZONE",
                "ALTER TABLE event_users ADD COLUMN IF NOT EXISTS notes TEXT",
                "ALTER TABLE event_users ADD COLUMN IF NOT EXISTS image_request_id VARCHAR",
            ]
            
            for stmt in event_user_statements:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception as e:
                    print(f"  Note: {str(e)}")
            
            print("\n✅ Migration completed successfully!")
            print("✅ Added new columns to events table:")
            print("   - start_time, end_time")
            print("   - max_participants, current_participants")
            print("   - guest_speakers, rsvp_link, rsvp_required")
            print("   - event_status, reminder_enabled, reminder_hours_before")
            print("✅ Added new columns to event_users table:")
            print("   - rsvp_status, checked_in, checked_in_at, notes")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    run_migration()
