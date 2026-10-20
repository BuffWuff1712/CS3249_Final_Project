"""SQLite snapshots are committed atomically with their audit and receipts."""

import os, sqlite3
from pathlib import Path
from threading import RLock
from contextlib import contextmanager
from .schemas import Session

lock = RLock()


@contextmanager
def connection():
    path = Path(os.getenv("BEANY_DB", "data/beany.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.execute(
        "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, body TEXT NOT NULL)"
    )
    try:
        with db:
            yield db
    finally:
        db.close()


def save(session):
    with connection() as db:
        db.execute(
            "INSERT INTO sessions VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
            (session.id, session.model_dump_json()),
        )


def load(sid):
    with connection() as db:
        row = db.execute("SELECT body FROM sessions WHERE id=?", (sid,)).fetchone()
    if row is None:
        raise LookupError("Session not found. Start a fresh session.")
    return Session.model_validate_json(row[0])


def delete(sid):
    with connection() as db:
        db.execute("DELETE FROM sessions WHERE id=?", (sid,))
