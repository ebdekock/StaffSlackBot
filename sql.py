import sqlite3
from typing import Any, Iterable, List, Optional, Tuple

# Local
import settings as s

# Sqlite3 does not currently support path objects
database = str(s.DATABASE_LOCATION)


def basic_sql_query(sql: str, data: Iterable) -> None:
    """
    Basic SQL query that connects, commits and closes off
    the connection. It enforces foreign key constraints.
    Supports most of the basic queries that doesnt expect
    a response (INSERT, UPDATE, DELETE).
    """
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute(sql, data)
    conn.commit()
    conn.close()


def fetch_one_row_sql(sql: str, data: Iterable) -> Optional[Tuple]:
    """
    SQL query that retrieves a single row
    from database.
    """
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute(sql, data)
    row = cur.fetchone()
    conn.close()
    return row


def fetch_all_rows_sql(sql: str, data: Iterable[Any] = []) -> List[Any]:
    """
    SQL query that retrieves all rows
    from database with optional data
    to be substitued into query.
    """
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute(sql, data)
    rows = cur.fetchall()
    conn.close()
    return [row for row in (rows or [])]


def create_users_table() -> None:
    """
    SQL query that creates user table if it doesnt exist.
    Table order must match order defined on User class.
    """
    sql = """CREATE TABLE IF NOT EXISTS users (
        slack_id text UNIQUE NOT NULL PRIMARY KEY,
        slack_channel text UNIQUE,
        email text UNIQUE,
        full_name text,
        pref_name text,
        phone text,
        photo_url text,
        challenge text,
        challenge_datetime timestamp,
        can_play_game boolean
    );"""
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    conn.close()


def create_challenges_table() -> None:
    """
    SQL query that creates challenges table if it doesnt exist.
    This will store challenges for the guessing game. Foreign key
    not really necessary, but ensures only users that exist can
    be issued challenges.
    """
    sql = """CREATE TABLE IF NOT EXISTS challenges (
        slack_id text NOT NULL,
        challenge text NOT NULL,
        FOREIGN KEY(slack_id) REFERENCES users(slack_id)
    );"""
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    conn.close()
