-- migrations/001_create_tables.sql

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    concept_data JSON,
    next_q_idx INTEGER DEFAULT 0,
    hint_level INTEGER DEFAULT 0
);

-- Turns table
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    speaker TEXT,
    text TEXT,
    time_spent REAL
);

-- Progress table
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE REFERENCES sessions(id),
    questions_answered INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    concepts_covered JSON,
    times_per_question JSON
);