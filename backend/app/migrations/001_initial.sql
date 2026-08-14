PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY,
    education_office_code TEXT NOT NULL,
    school_code TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (education_office_code, school_code)
);

CREATE TABLE IF NOT EXISTS analysis_requests (
    id TEXT PRIMARY KEY,
    analysis_date TEXT NOT NULL,
    prompt TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('first', 'second', 'tie')),
    winner_school_id INTEGER REFERENCES schools(id),
    summary TEXT NOT NULL,
    key_reason TEXT NOT NULL,
    first_school_improvement TEXT NOT NULL,
    second_school_improvement TEXT NOT NULL,
    quality_warnings TEXT NOT NULL,
    disclaimer TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_schools (
    analysis_id TEXT NOT NULL REFERENCES analysis_requests(id) ON DELETE CASCADE,
    school_id INTEGER NOT NULL REFERENCES schools(id),
    position INTEGER NOT NULL CHECK (position IN (0, 1)),
    total_score REAL NOT NULL,
    PRIMARY KEY (analysis_id, school_id),
    UNIQUE (analysis_id, position)
);

CREATE TABLE IF NOT EXISTS agent_results (
    id INTEGER PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analysis_requests(id) ON DELETE CASCADE,
    school_id INTEGER NOT NULL REFERENCES schools(id),
    area TEXT NOT NULL CHECK (
        area IN ('nutrition_balance', 'healthiness', 'ingredient_menu_quality')
    ),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    weight INTEGER NOT NULL,
    weighted_score REAL NOT NULL,
    rationale TEXT NOT NULL,
    evidence TEXT NOT NULL,
    estimated_flags TEXT NOT NULL,
    UNIQUE (analysis_id, school_id, area)
);

PRAGMA user_version = 1;
