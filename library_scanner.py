"""Einlesen der Bibliothek im Hintergrund, damit die Oberfläche bedienbar bleibt."""

import os
import time
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QThread, Signal

from library import find_library_files, read_track
from library_cache import LibraryCache

# Mindestabstand zwischen zwei Fortschrittsmeldungen, um die Oberfläche nicht zu fluten
_PROGRESS_INTERVAL_S = 0.1


class LibraryScanner(QThread):
    """Liest `folder` ein und meldet das Ergebnis über `scanned(tracks, covers)`.

    Unveränderte Dateien kommen aus dem Cache, alles andere wird parallel mit mutagen gelesen.
    """

    progress = Signal(int, int)  # erledigt, gesamt
    scanned = Signal(object, object)  # Liste von Track-Dicts, dict Cover-ID -> JPEG-Bytes

    def __init__(self, folder: str, cache_path: str, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.cache_path = cache_path

    def run(self):
        paths = find_library_files(self.folder)
        total = len(paths)

        cache = self._open_cache()
        cached = {}
        if cache is not None:
            try:
                cached = cache.load_tracks(self.folder)
            except Exception:
                cache.close()
                cache = None

        tracks = []
        to_read = []
        for path in paths:
            try:
                stat = os.stat(path)
            except OSError:
                continue
            hit = cached.get(path)
            if hit is not None and hit[0] == stat.st_mtime_ns and hit[1] == stat.st_size:
                tracks.append(hit[2])
            else:
                to_read.append((path, stat.st_mtime_ns, stat.st_size))

        covers = {}
        if cache is not None:
            try:
                covers.update(cache.load_covers(
                    {t["cover_id"] for t in tracks if t["cover_id"] is not None}
                ))
            except Exception:
                pass

        done = len(tracks)
        self.progress.emit(done, total)
        new_entries = []
        new_covers = {}
        last_emit = time.monotonic()
        workers = min(8, os.cpu_count() or 4)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = pool.map(lambda item: read_track(item[0], new_covers), to_read)
            for (path, mtime_ns, size), track in zip(to_read, results):
                if self.isInterruptionRequested():
                    pool.shutdown(wait=True, cancel_futures=True)
                    break
                tracks.append(track)
                new_entries.append((mtime_ns, size, track))
                done += 1
                now = time.monotonic()
                if now - last_emit >= _PROGRESS_INTERVAL_S:
                    self.progress.emit(done, total)
                    last_emit = now

        if self.isInterruptionRequested():
            if cache is not None:
                cache.close()
            return

        covers.update((cover_id, data) for cover_id, data in new_covers.items() if data is not None)

        if cache is not None:
            try:
                cache.save(self.folder, new_entries, new_covers, {t["path"] for t in tracks})
            except Exception:
                pass
            cache.close()

        tracks.sort(key=lambda t: (t["artist"].lower(), t["album"].lower(), t["track_no"]))
        self.scanned.emit(tracks, covers)

    def _open_cache(self):
        """Cache öffnen; ohne Cache wird eben alles neu eingelesen."""
        try:
            return LibraryCache(self.cache_path)
        except Exception:
            return None
