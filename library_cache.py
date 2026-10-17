"""Persistenter Cache (SQLite) für eingelesene Tags und Cover-Vorschaubilder.

Ein Eintrag gilt, solange Änderungszeit und Größe der Datei unverändert sind. So muss beim
Start nur noch eingelesen werden, was seit dem letzten Mal neu dazugekommen oder geändert ist.
"""

import os
import sqlite3

from library import finalize_track

# Bei Änderungen am Schema oder am Einlesen hochzählen, dann wird der Cache verworfen
SCHEMA_VERSION = 1

_TRACK_COLUMNS = ("title", "artist", "album", "track_no", "year", "duration_ms", "cover_id")


class LibraryCache:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            self.conn.executescript("""
                DROP TABLE IF EXISTS tracks;
                DROP TABLE IF EXISTS covers;
            """)
        self.conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS tracks (
                path TEXT PRIMARY KEY,
                mtime_ns INTEGER NOT NULL,
                size INTEGER NOT NULL,
                title TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT NOT NULL,
                track_no INTEGER NOT NULL,
                year INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                cover_id TEXT,
                badge_kind TEXT,
                badge_text TEXT
            );
            CREATE TABLE IF NOT EXISTS covers (
                id TEXT PRIMARY KEY,
                data BLOB NOT NULL
            );
            PRAGMA user_version = {SCHEMA_VERSION};
        """)

    def close(self):
        self.conn.close()

    def load_tracks(self, folder: str) -> dict:
        """Pfad -> (mtime_ns, size, Track-Dict) für alle gespeicherten Tracks unterhalb von `folder`."""
        prefix = os.path.join(folder, "")
        rows = self.conn.execute(
            f"SELECT path, mtime_ns, size, {', '.join(_TRACK_COLUMNS)}, badge_kind, badge_text "
            "FROM tracks WHERE substr(path, 1, ?) = ?",
            (len(prefix), prefix),
        )
        result = {}
        for path, mtime_ns, size, *values, badge_kind, badge_text in rows:
            track = dict(zip(_TRACK_COLUMNS, values))
            track["path"] = path
            track["badge"] = (badge_kind, badge_text) if badge_kind else None
            result[path] = (mtime_ns, size, finalize_track(track))
        return result

    def load_covers(self, cover_ids) -> dict:
        covers = {}
        ids = list(cover_ids)
        # SQLite begrenzt die Anzahl der Parameter pro Abfrage
        for start in range(0, len(ids), 500):
            chunk = ids[start:start + 500]
            placeholders = ", ".join("?" * len(chunk))
            for cover_id, data in self.conn.execute(
                f"SELECT id, data FROM covers WHERE id IN ({placeholders})", chunk
            ):
                covers[cover_id] = data
        return covers

    def save(self, folder: str, entries, covers: dict, seen_paths: set):
        """Neu eingelesene Tracks/Cover speichern und verschwundene Dateien aus `folder` entfernen.

        `entries` ist eine Liste von (mtime_ns, size, Track-Dict).
        """
        prefix = os.path.join(folder, "")
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO tracks (path, mtime_ns, size, "
                f"{', '.join(_TRACK_COLUMNS)}, badge_kind, badge_text) "
                f"VALUES ({', '.join('?' * (len(_TRACK_COLUMNS) + 5))})",
                [
                    (track["path"], mtime_ns, size,
                     *(track[column] for column in _TRACK_COLUMNS),
                     *(track["badge"] or (None, None)))
                    for mtime_ns, size, track in entries
                ],
            )
            self.conn.executemany(
                "INSERT OR IGNORE INTO covers (id, data) VALUES (?, ?)",
                [(cover_id, data) for cover_id, data in covers.items() if data is not None],
            )
            stale = [
                (path,)
                for (path,) in self.conn.execute(
                    "SELECT path FROM tracks WHERE substr(path, 1, ?) = ?", (len(prefix), prefix)
                )
                if path not in seen_paths
            ]
            self.conn.executemany("DELETE FROM tracks WHERE path = ?", stale)
            # Geänderte Dateien können ihr altes Cover verwaisen lassen
            if stale or entries:
                self.conn.execute(
                    "DELETE FROM covers WHERE id NOT IN "
                    "(SELECT cover_id FROM tracks WHERE cover_id IS NOT NULL)"
                )
