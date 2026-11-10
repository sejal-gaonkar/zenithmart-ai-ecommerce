"""
database.py - SQLite Chat Logging & Analytics for AuraStyle E-Commerce Assistant
Stores conversation logs, timestamps, latency (ms), and token metrics with connection management.
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_logs.db")

@contextmanager
def db_session():
    """Context manager that handles connection opening, committing, and closing."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db() -> None:
    """Initialize SQLite tables for chat interactions and sessions."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                response_time_ms REAL NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'success',
                error_details TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id ON chat_logs (session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON chat_logs (timestamp)
        """)

def log_interaction(
    session_id: str,
    user_message: str,
    bot_response: str,
    response_time_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    status: str = "success",
    error_details: Optional[str] = None
) -> int:
    """Logs a single conversation turn to SQLite."""
    timestamp = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_logs (
                session_id, timestamp, user_message, bot_response,
                response_time_ms, prompt_tokens, completion_tokens,
                total_tokens, status, error_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, timestamp, user_message, bot_response,
            response_time_ms, prompt_tokens, completion_tokens,
            total_tokens, status, error_details
        ))
        return cursor.lastrowid

def get_session_history(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves chronological conversation history for a given session."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, timestamp, user_message, bot_response,
                   response_time_ms, prompt_tokens, completion_tokens, total_tokens, status
            FROM chat_logs
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_all_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves recent logs across all sessions for audit and analytics."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, timestamp, user_message, bot_response,
                   response_time_ms, prompt_tokens, completion_tokens, total_tokens, status, error_details
            FROM chat_logs
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_analytics_summary() -> Dict[str, Any]:
    """Retrieves quick summary metrics from the chat log database."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_messages,
                COUNT(DISTINCT session_id) as total_sessions,
                AVG(response_time_ms) as avg_latency_ms,
                SUM(total_tokens) as sum_tokens,
                SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as error_count
            FROM chat_logs
        """)
        row = cursor.fetchone()
        return {
            "total_messages": row["total_messages"] or 0,
            "total_sessions": row["total_sessions"] or 0,
            "avg_latency_ms": round(row["avg_latency_ms"] or 0.0, 2),
            "sum_tokens": row["sum_tokens"] or 0,
            "error_count": row["error_count"] or 0
        }

def clear_session(session_id: str) -> int:
    """Clears history for a specific session."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_logs WHERE session_id = ?", (session_id,))
        return cursor.rowcount

if __name__ == "__main__":
    init_db()
    print("Database initialized at:", DB_PATH)
