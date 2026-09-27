"""One local SQLite authority shared by cooperating workers and controllers."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time


class Store:
    def __init__(self, root, clock=time.time):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.now = clock
        self.db = sqlite3.connect(self.root / "state.sqlite3", timeout=10,
                                  isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA journal_mode = WAL")
        self.db.execute("PRAGMA synchronous = FULL")
        try:
            with self.transaction():
                self.db.execute("CREATE TABLE IF NOT EXISTS store_version "
                                "(id INTEGER PRIMARY KEY CHECK (id = 1), version INTEGER NOT NULL)")
                row = self.db.execute("SELECT version FROM store_version WHERE id = 1").fetchone()
                if row is None:
                    self.db.execute("INSERT INTO store_version VALUES (1, 1)")
                elif row["version"] != 1:
                    raise ValueError("Unsupported store schema version")
        except BaseException:
            self.db.close()
            raise

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
        except BaseException:
            self.db.rollback()
            raise
        else:
            self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
