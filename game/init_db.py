"""
Initialize database tables for Anachron V2.
Run this once to create the required tables in your Postgres database.
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    exit(1)

SCHEMA = """
-- Game saves table
CREATE TABLE IF NOT EXISTS game_saves (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR NOT NULL,
    game_id VARCHAR NOT NULL,
    player_name VARCHAR,
    current_era VARCHAR,
    phase VARCHAR,
    state JSONB NOT NULL,
    saved_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_game_saves_user ON game_saves(user_id);
CREATE INDEX IF NOT EXISTS idx_game_saves_user_game ON game_saves(user_id, game_id);

-- Leaderboard entries table
CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR NOT NULL,
    game_id VARCHAR,
    player_name VARCHAR NOT NULL,
    turns_survived INTEGER DEFAULT 0,
    eras_visited INTEGER DEFAULT 0,
    belonging_score INTEGER DEFAULT 0,
    legacy_score INTEGER DEFAULT 0,
    freedom_score INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    ending_type VARCHAR,
    final_era VARCHAR,
    blurb TEXT,
    ending_narrative TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leaderboard_user ON leaderboard_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_total ON leaderboard_entries(total_score);

-- Game histories table
CREATE TABLE IF NOT EXISTS game_histories (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    game_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    player_name VARCHAR,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    eras JSONB DEFAULT '[]',
    final_score JSONB,
    ending_type VARCHAR,
    blurb TEXT
);

CREATE INDEX IF NOT EXISTS idx_game_histories_user ON game_histories(user_id);
CREATE INDEX IF NOT EXISTS idx_game_histories_game ON game_histories(game_id);

-- Annals of Anachron entries table
CREATE TABLE IF NOT EXISTS aoa_entries (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    entry_id VARCHAR NOT NULL UNIQUE,
    user_id VARCHAR NOT NULL,
    game_id VARCHAR,
    player_name VARCHAR,
    character_name VARCHAR,
    final_era VARCHAR,
    final_era_year INTEGER,
    eras_visited INTEGER DEFAULT 0,
    turns_survived INTEGER DEFAULT 0,
    ending_type VARCHAR,
    belonging_score INTEGER DEFAULT 0,
    legacy_score INTEGER DEFAULT 0,
    freedom_score INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    key_npcs JSONB DEFAULT '[]',
    defining_moments JSONB DEFAULT '[]',
    wisdom_moments JSONB DEFAULT '[]',
    items_used JSONB DEFAULT '[]',
    player_narrative TEXT,
    historian_narrative TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aoa_user ON aoa_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_aoa_created ON aoa_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_aoa_entry_id ON aoa_entries(entry_id);

-- Sessions table (for auth)
CREATE TABLE IF NOT EXISTS sessions (
    sid VARCHAR PRIMARY KEY,
    sess JSONB NOT NULL,
    expire TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_expire ON sessions(expire);

-- Users table (for OAuth)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    profile_image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
"""

def init_db():
    print(f"Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Creating tables...")
    cur.execute(SCHEMA)
    conn.commit()

    print("Done! Tables created successfully.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    init_db()
