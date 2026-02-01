-- Migration script to create near_people table
-- Run this script to add the near_people feature to your database

CREATE TABLE IF NOT EXISTS near_people (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    near_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    room_id VARCHAR NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    nickname VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_near_person UNIQUE (user_id, near_user_id),
    CONSTRAINT no_self_add CHECK (user_id != near_user_id)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_near_people_user_id ON near_people(user_id);
CREATE INDEX IF NOT EXISTS idx_near_people_near_user_id ON near_people(near_user_id);
CREATE INDEX IF NOT EXISTS idx_near_people_room_id ON near_people(room_id);
