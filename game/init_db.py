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

-- ==================== Narrative Lab Tables ====================

-- Lab snapshots: captured game states for branching/comparison
CREATE TABLE IF NOT EXISTS lab_snapshots (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR NOT NULL,
    label VARCHAR NOT NULL,
    tags JSONB DEFAULT '[]',
    game_state JSONB NOT NULL,
    conversation_history JSONB DEFAULT '[]',
    system_prompt TEXT,
    era_id VARCHAR,
    era_name VARCHAR,
    era_year INTEGER,
    era_location VARCHAR,
    total_turns INTEGER DEFAULT 0,
    phase VARCHAR,
    player_name VARCHAR,
    belonging_value INTEGER DEFAULT 0,
    legacy_value INTEGER DEFAULT 0,
    freedom_value INTEGER DEFAULT 0,
    available_choices JSONB DEFAULT '[]',
    source VARCHAR DEFAULT 'manual',
    source_game_id VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lab_snapshots_user ON lab_snapshots(user_id);
CREATE INDEX IF NOT EXISTS idx_lab_snapshots_era ON lab_snapshots(era_id);
CREATE INDEX IF NOT EXISTS idx_lab_snapshots_tags ON lab_snapshots USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_lab_snapshots_created ON lab_snapshots(created_at DESC);

-- Lab generations: every AI narrative generation with params and parsed results
CREATE TABLE IF NOT EXISTS lab_generations (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR NOT NULL,
    snapshot_id VARCHAR NOT NULL REFERENCES lab_snapshots(id) ON DELETE CASCADE,
    choice_id VARCHAR NOT NULL,
    choice_text TEXT,
    model VARCHAR NOT NULL,
    system_prompt TEXT NOT NULL,
    turn_prompt TEXT NOT NULL,
    dice_roll INTEGER,
    temperature REAL DEFAULT 1.0,
    max_tokens INTEGER DEFAULT 1500,
    raw_response TEXT NOT NULL,
    narrative_text TEXT,
    anchor_deltas JSONB,
    parsed_npcs JSONB DEFAULT '[]',
    parsed_wisdom VARCHAR,
    parsed_character_name VARCHAR,
    parsed_choices JSONB DEFAULT '[]',
    rating INTEGER,
    notes TEXT,
    comparison_group VARCHAR,
    comparison_label VARCHAR,
    generation_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lab_generations_user ON lab_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_lab_generations_snapshot ON lab_generations(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_lab_generations_comparison ON lab_generations(comparison_group);
CREATE INDEX IF NOT EXISTS idx_lab_generations_rating ON lab_generations(rating);
CREATE INDEX IF NOT EXISTS idx_lab_generations_model ON lab_generations(model);
CREATE INDEX IF NOT EXISTS idx_lab_generations_created ON lab_generations(created_at DESC);

-- Lab prompt variants: saved prompt template variations with version control
CREATE TABLE IF NOT EXISTS lab_prompt_variants (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    prompt_type VARCHAR NOT NULL,
    template TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_live BOOLEAN DEFAULT FALSE,
    version_number INTEGER DEFAULT 1,
    diff_vs_baseline TEXT,
    diff_vs_previous TEXT,
    change_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lab_prompts_user ON lab_prompt_variants(user_id);
CREATE INDEX IF NOT EXISTS idx_lab_prompts_type ON lab_prompt_variants(prompt_type);
CREATE INDEX IF NOT EXISTS idx_lab_prompts_live ON lab_prompt_variants(is_live) WHERE is_live = TRUE;
"""

MIGRATIONS = """
-- Migration: Add version control columns to lab_prompt_variants
ALTER TABLE lab_prompt_variants ADD COLUMN IF NOT EXISTS is_live BOOLEAN DEFAULT FALSE;
ALTER TABLE lab_prompt_variants ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE lab_prompt_variants ADD COLUMN IF NOT EXISTS diff_vs_baseline TEXT;
ALTER TABLE lab_prompt_variants ADD COLUMN IF NOT EXISTS diff_vs_previous TEXT;
ALTER TABLE lab_prompt_variants ADD COLUMN IF NOT EXISTS change_summary TEXT;
CREATE INDEX IF NOT EXISTS idx_lab_prompts_live ON lab_prompt_variants(is_live) WHERE is_live = TRUE;
"""

def init_db():
    print(f"Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Creating tables...")
    cur.execute(SCHEMA)
    conn.commit()

    print("Running migrations...")
    cur.execute(MIGRATIONS)
    conn.commit()

    print("Done! Tables created/updated successfully.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    init_db()
