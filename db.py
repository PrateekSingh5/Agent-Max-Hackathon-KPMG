# db.py
import os
import psycopg2
import psycopg2.extras
from psycopg2 import pool
from contextlib import contextmanager
from dotenv import load_dotenv

# ------------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------------
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "agent_max"),
    "user": os.getenv("DB_USER", "myuser"),
    "password": os.getenv("DB_PASSWORD", "rootpassword"),
}

DB_MIN_CONN = int(os.getenv("DB_MIN_CONN", 1))
DB_MAX_CONN = int(os.getenv("DB_MAX_CONN", 10))


# ------------------------------------------------------------------
# Create PostgreSQL connection pool
# ------------------------------------------------------------------
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        DB_MIN_CONN,
        DB_MAX_CONN,
        **DB_CONFIG
    )
    if connection_pool:
        print("✅ PostgreSQL connection pool created successfully.")
except Exception as e:
    print(f"❌ Error creating connection pool: {e}")
    raise e


# ------------------------------------------------------------------
# Context manager for safe DB access
# ------------------------------------------------------------------
@contextmanager
def get_connection():
    conn = None
    try:
        conn = connection_pool.getconn()
        yield conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise e
    finally:
        if conn:
            connection_pool.putconn(conn)


# ------------------------------------------------------------------
# Safe query executor (used by queries.py)
# ------------------------------------------------------------------
def safe_query(conn, sql, params=None):
    """
    Execute a SQL query safely and return result as list of dicts.
    Params:
        conn: active psycopg2 connection
        sql: SQL string
        params: tuple or list of parameters (optional)
    """
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if cur.description:  # if query returns data
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            conn.commit()
            return []
    except Exception as e:
        conn.rollback()
        print(f"❌ Query failed: {e}\nSQL: {sql}\nParams: {params}")
        raise e


# ------------------------------------------------------------------
# Shutdown pool gracefully
# ------------------------------------------------------------------
def close_connection_pool():
    """Close all connections in pool."""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        print("🛑 Connection pool closed.")
