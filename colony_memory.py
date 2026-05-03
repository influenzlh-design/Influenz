"""
influenz / colony_memory.py
---------------------------
Shared memory layer for the entire colony.
All agents read and write through this single interface.
No agent talks to the database directly.

Tables:
    tasks        — general task queue (original)
    interactions — action log (original)
    topics       — YouTube trending topics (new — Sprint 1)
    scripts      — generated Shorts scripts (new — Sprint 1)
"""

import sqlite3
from datetime import datetime, timezone


class ColonyMemory:
    def __init__(self, db_path="colony.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row   # access columns by name
        self.create_tables()

    # ── Schema ────────────────────────────────────────────────────────────────

    def create_tables(self):
        self.conn.executescript("""

            -- Original task queue (used by Queen, Scout, Worker)
            CREATE TABLE IF NOT EXISTS tasks (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type      TEXT,
                content        TEXT,
                status         TEXT         DEFAULT 'pending',
                assigned_agent TEXT,
                created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
            );

            -- Original interaction/action log
            CREATE TABLE IF NOT EXISTS interactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id   TEXT,
                agent_role TEXT,
                action     TEXT,
                timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Sprint 1: YouTube trending topics (Scout writes, Forager reads)
            CREATE TABLE IF NOT EXISTS topics (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                query            TEXT    NOT NULL,
                video_id         TEXT    NOT NULL UNIQUE,
                title            TEXT    NOT NULL,
                channel          TEXT,
                view_count       INTEGER DEFAULT 0,
                like_count       INTEGER DEFAULT 0,
                comment_count    INTEGER DEFAULT 0,
                engagement_ratio REAL    DEFAULT 0,
                scouted_at       TEXT    NOT NULL,
                status           TEXT    NOT NULL DEFAULT 'queued',
                score            REAL    DEFAULT 0
            );

            -- Sprint 1: Generated Shorts scripts (Forager writes, Worker reads)
            CREATE TABLE IF NOT EXISTS scripts (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id       INTEGER  REFERENCES topics(id),
                short_title    TEXT,
                hook           TEXT,
                script_body    TEXT,
                cta            TEXT,
                yt_description TEXT,
                hashtags       TEXT,
                word_count     INTEGER  DEFAULT 0,
                estimated_secs INTEGER  DEFAULT 0,
                generated_at   TEXT,
                status         TEXT     DEFAULT 'pending_review',
                approved_at    TEXT,
                notes          TEXT
            );

        """)
        self.conn.commit()

    # ── Task queue (original interface — Queen + Worker use these) ────────────

    def add_task(self, task_type, content):
        self.conn.execute(
            "INSERT INTO tasks (task_type, content, status, created_at) VALUES (?, ?, 'pending', ?)",
            (task_type, content, datetime.now())
        )
        self.conn.commit()

    def get_pending_task(self, agent_type):
        cursor = self.conn.execute(
            "SELECT id, content FROM tasks WHERE status='pending' LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            self.conn.execute(
                "UPDATE tasks SET status='in_progress', assigned_agent=? WHERE id=?",
                (agent_type, row["id"])
            )
            self.conn.commit()
            return row["content"]
        return None

    def complete_task(self, task_id):
        self.conn.execute(
            "UPDATE tasks SET status='done' WHERE id=?", (task_id,)
        )
        self.conn.commit()

    def fail_task(self, task_id, reason=""):
        self.conn.execute(
            "UPDATE tasks SET status='failed' WHERE id=?", (task_id,)
        )
        self.conn.commit()

    # ── Interaction log (original interface) ──────────────────────────────────

    def log_interaction(self, tweet_id, agent_role, action):
        self.conn.execute(
            "INSERT INTO interactions (tweet_id, agent_role, action, timestamp) VALUES (?, ?, ?, ?)",
            (tweet_id, agent_role, action, datetime.now())
        )
        self.conn.commit()

    # ── Topics (Scout writes these) ───────────────────────────────────────────

    def save_topic(self, query, video_id, title, channel,
                   view_count, like_count, comment_count,
                   engagement_ratio, score) -> bool:
        """
        Insert a topic. Returns True if it was new, False if already existed.
        """
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("""
            INSERT OR IGNORE INTO topics
                (query, video_id, title, channel, view_count, like_count,
                 comment_count, engagement_ratio, scouted_at, status, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?)
        """, (query, video_id, title, channel,
              view_count, like_count, comment_count,
              engagement_ratio, now, score))
        self.conn.commit()
        return self.conn.execute("SELECT changes()").fetchone()[0] > 0

    def get_queued_topics(self, limit=1):
        """Return top-scored queued topics for Forager to process."""
        rows = self.conn.execute("""
            SELECT id, title, query
            FROM topics
            WHERE status = 'queued'
            ORDER BY score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_topic(self, topic_id, status):
        self.conn.execute(
            "UPDATE topics SET status=? WHERE id=?", (status, topic_id)
        )
        self.conn.commit()

    def peek_topics(self, limit=10):
        rows = self.conn.execute("""
            SELECT id, score, engagement_ratio, view_count, title
            FROM topics WHERE status='queued'
            ORDER BY score DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ── Scripts (Forager writes, Worker reads) ────────────────────────────────

    def save_script(self, topic_id, short_title, hook, script_body,
                    cta, yt_description, hashtags,
                    word_count, estimated_secs) -> int:
        """Save a generated script. Returns the new script id."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute("""
            INSERT INTO scripts
                (topic_id, short_title, hook, script_body, cta,
                 yt_description, hashtags, word_count, estimated_secs,
                 generated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review')
        """, (topic_id, short_title, hook, script_body, cta,
              yt_description, hashtags, word_count, estimated_secs, now))
        self.conn.commit()
        return cursor.lastrowid

    def get_pending_scripts(self, limit=5):
        rows = self.conn.execute("""
            SELECT id, short_title, hook, script_body, cta,
                   yt_description, hashtags, estimated_secs
            FROM scripts
            WHERE status = 'pending_review'
            ORDER BY generated_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def approve_script(self, script_id):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute("""
            UPDATE scripts SET status='approved', approved_at=?
            WHERE id=?
        """, (now, script_id))
        self.conn.commit()

    def get_approved_scripts(self, limit=5):
        rows = self.conn.execute("""
            SELECT id, short_title, hook, script_body, cta,
                   yt_description, hashtags, estimated_secs
            FROM scripts
            WHERE status = 'approved'
            ORDER BY approved_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_script(self, script_id, status, notes=""):
        self.conn.execute(
            "UPDATE scripts SET status=?, notes=? WHERE id=?",
            (status, notes, script_id)
        )
        self.conn.commit()

    # ── Colony stats (Queen uses this for reporting) ──────────────────────────

    def get_stats(self) -> dict:
        stats = {}
        for table, col in [
            ("topics",  "status"),
            ("scripts", "status"),
            ("tasks",   "status"),
        ]:
            rows = self.conn.execute(
                f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col}"
            ).fetchall()
            stats[table] = {r[0]: r[1] for r in rows}
        return stats

    # ── Utility ───────────────────────────────────────────────────────────────

    def close(self):
        self.conn.close()
