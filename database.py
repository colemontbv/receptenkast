import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS recipes (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        servings INTEGER NOT NULL DEFAULT 4,
        tags TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        photo TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingredients (
        id SERIAL PRIMARY KEY,
        recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        position INTEGER NOT NULL,
        amount REAL,
        unit TEXT DEFAULT '',
        name TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS steps (
        id SERIAL PRIMARY KEY,
        recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        position INTEGER NOT NULL,
        instruction TEXT NOT NULL
    )
    """,
]


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def init_db():
    conn = get_db()
    with conn:
        with conn.cursor() as cur:
            for stmt in SCHEMA:
                cur.execute(stmt)
    conn.close()
