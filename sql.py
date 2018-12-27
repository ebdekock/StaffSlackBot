import sqlite3

import settings

# Sqlite3 does not currently support path objects
database = str(settings.DATABASE_LOCATION)


def basic_sql_query(sql, data):
    """
    Basic SQL query that connects, commits and closes off 
    the connection. It enforces foreign key constraints. 
    Supports most of the basic queries that doesnt expect 
    a response (INSERT, UPDATE, DELETE).

    :param sql: query to be executed
    :param data: iterable data to be substituted into query

    """
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute(sql, data)
    conn.commit()
    conn.close()


def fetch_one_row_sql(sql, data):
    """
    SQL query that retrieves a single row
    from database.

    :param sql: query to be executed
    :param data: iterable data to be substituted into query
    :returns: a row that matches or None
    """
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute(sql, data)
    row = cur.fetchone()
    conn.close()
    return row


def create_users_table():
    """
    SQL query that creates user table if it doesnt exist.
    Table order must match order defined on User class.
    """
    sql = """CREATE TABLE IF NOT EXISTS users (
        slack_id text UNIQUE NOT NULL PRIMARY KEY,
        email text UNIQUE,
        full_name text,
        pref_name text,
        phone text,
        photo_url text,
        challenge text,
        challenge_datetime timestamp
    );"""
    conn = sqlite3.connect(database)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    conn.close()


def create_challenges_table():
    """
    SQL query that creates challenges table if it doesnt exist.
    This will store challenges for the guessing game.
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
