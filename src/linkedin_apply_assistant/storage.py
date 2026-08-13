from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .models import Job


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  location TEXT NOT NULL,
  url TEXT NOT NULL,
  source TEXT NOT NULL,
  easy_apply INTEGER NOT NULL,
  posted_at TEXT NOT NULL,
  salary_text TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL,
  score INTEGER NOT NULL,
  reject_reason TEXT NOT NULL,
  fit_notes TEXT NOT NULL,
  estimated_tc INTEGER,
  search_preset TEXT NOT NULL DEFAULT '',
  discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


UPSERT = """
INSERT INTO jobs (
  job_id, title, company, location, url, source, easy_apply, posted_at, salary_text,
  description, status, score, reject_reason, fit_notes, estimated_tc, search_preset
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(job_id) DO UPDATE SET
  title=excluded.title,
  company=excluded.company,
  location=excluded.location,
  url=excluded.url,
  source=excluded.source,
  easy_apply=excluded.easy_apply,
  posted_at=excluded.posted_at,
  salary_text=excluded.salary_text,
  description=excluded.description,
  status=excluded.status,
  score=excluded.score,
  reject_reason=excluded.reject_reason,
  fit_notes=excluded.fit_notes,
  estimated_tc=excluded.estimated_tc,
  search_preset=excluded.search_preset,
  updated_at=CURRENT_TIMESTAMP;
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    return conn

def ensure_schema(conn: sqlite3.Connection) -> None:
    # Keep the historical estimated_tc column name for compatibility. Newer code
    # stores one normalized base-pay value there and labels it as base in output.
    conn.execute(SCHEMA)
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
    }
    if "estimated_tc" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN estimated_tc INTEGER")
    if "search_preset" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN search_preset TEXT NOT NULL DEFAULT ''")
    conn.commit()

def upsert_jobs(conn: sqlite3.Connection, jobs: list[Job]) -> None:
    conn.executemany(
        UPSERT,
        [
            (
                job.job_id,
                job.title,
                job.company,
                job.location,
                job.url,
                job.source,
                int(job.easy_apply),
                job.posted_at,
                job.salary_text,
                job.description,
                job.status.value,
                job.score,
                job.reject_reason,
                job.fit_notes,
                job.estimated_tc,
                job.search_preset,
            )
            for job in jobs
        ],
    )
    conn.commit()


def export_jobs(conn: sqlite3.Connection, status: Optional[str]) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    if status:
        return conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY score DESC, updated_at DESC",
            (status,),
        ).fetchall()
    return conn.execute("SELECT * FROM jobs ORDER BY updated_at DESC").fetchall()
