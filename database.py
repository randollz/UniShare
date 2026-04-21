import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(__file__), 'unishare.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    xp            INTEGER DEFAULT 0,
    rank          TEXT DEFAULT 'Newbie',
    rating_sum    INTEGER DEFAULT 0,
    rating_count  INTEGER DEFAULT 0,
    bio           TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS listings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id   INTEGER NOT NULL REFERENCES users(id),
    title       TEXT NOT NULL,
    unit_code   TEXT NOT NULL,
    price       REAL NOT NULL,
    condition   TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id   INTEGER NOT NULL REFERENCES users(id),
    title       TEXT NOT NULL,
    unit_code   TEXT NOT NULL,
    semester    TEXT DEFAULT '',
    description TEXT DEFAULT '',
    upvotes     INTEGER DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    host_id        INTEGER NOT NULL REFERENCES users(id),
    title          TEXT NOT NULL,
    unit_code      TEXT NOT NULL,
    location       TEXT DEFAULT '',
    session_date   DATETIME,
    max_attendees  INTEGER DEFAULT 10,
    description    TEXT DEFAULT '',
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_rsvps (
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    user_id     INTEGER NOT NULL REFERENCES users(id),
    PRIMARY KEY (session_id, user_id)
);

CREATE TABLE IF NOT EXISTS bounties (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    poster_id   INTEGER NOT NULL REFERENCES users(id),
    title       TEXT NOT NULL,
    unit_code   TEXT DEFAULT '',
    reward      REAL DEFAULT 0,
    description TEXT DEFAULT '',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS saved_listings (
    user_id     INTEGER NOT NULL REFERENCES users(id),
    listing_id  INTEGER NOT NULL REFERENCES listings(id),
    PRIMARY KEY (user_id, listing_id)
);

CREATE TABLE IF NOT EXISTS ratings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rater_id    INTEGER NOT NULL REFERENCES users(id),
    rated_id    INTEGER NOT NULL REFERENCES users(id),
    listing_id  INTEGER NOT NULL REFERENCES listings(id),
    score       INTEGER NOT NULL,
    comment     TEXT DEFAULT ''
);
"""


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
