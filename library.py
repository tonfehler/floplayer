"""Einlesen von FLAC-Bibliotheken: Tags, Cover, Qualitätsinfo, Sortierung/Gruppierung/Suche."""

import hashlib
import os
import re

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from PySide6.QtCore import QBuffer, QByteArray, QFileInfo, QIODevice, Qt
from PySide6.QtGui import QImage

from theme import PLAYER_COVER_SIZE

# (Anzeigetext, interner Schlüssel) für die Gruppierungs-/Sortierauswahl
GROUP_OPTIONS = [
    ("Interpret", "artist"),
    ("Album", "album"),
    ("Jahr", "year"),
    ("Titel (ohne Gruppierung)", "title"),
]

# Cover werden nur als kleine Vorschaubilder im Speicher/Cache gehalten (2x für HiDPI)
THUMBNAIL_SIZE = PLAYER_COVER_SIZE * 2


def sort_key_for_group(group_by):
    if group_by == "artist":
        return lambda t: (t["artist"].lower(), t["album"].lower(), t["track_no"])
    if group_by == "album":
        return lambda t: (t["album"].lower(), t["artist"].lower(), t["track_no"])
    if group_by == "year":
        return lambda t: (t["year"], t["artist"].lower(), t["album"].lower(), t["track_no"])
    return lambda t: (t["title"].lower(),)


def track_matches_search(track, query):
    """True, wenn Titel, Interpret oder Album den (bereits kleingeschriebenen) Suchbegriff enthält."""
    return not query or query in track["search_text"]


def group_label(track, group_by):
    """Überschrift für eine Gruppe, oder None wenn nicht gruppiert werden soll."""
    if group_by == "artist":
        return track["artist"] or "Unbekannter Interpret"
    if group_by == "album":
        album = track["album"] or "Unbekanntes Album"
        return f"{album} – {track['artist']}" if track["artist"] else album
    if group_by == "year":
        return str(track["year"]) if track["year"] else "Unbekanntes Jahr"
    return None


def quality_badge_info(path):
    """(Art, Anzeigetext) für das Qualitäts-Badge in der Playerleiste, oder None."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".flac":
            FLAC(path)
            return ("flac", "FLAC")
        if ext == ".mp3":
            bitrate_kbps = round(MP3(path).info.bitrate / 1000)
            return ("bitrate", f"{bitrate_kbps} kbps")
    except Exception:
        pass
    return None


def select_cover(pictures):
    """Bevorzugt das Front-Cover (Typ 3), sonst das erste eingebettete Bild."""
    if not pictures:
        return None
    for picture in pictures:
        if picture.type == 3:
            return picture.data
    return pictures[0].data


def cover_id_for(data: bytes) -> str:
    """Inhalts-Hash als ID, damit identische Cover (z.B. eines Albums) nur einmal vorliegen."""
    return hashlib.sha1(data).hexdigest()


def make_thumbnail(data: bytes):
    """Cover auf THUMBNAIL_SIZE verkleinern und als JPEG-Bytes zurückgeben (None bei Fehler)."""
    image = QImage.fromData(data)
    if image.isNull():
        return None
    image = image.scaled(THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    buffer = QByteArray()
    device = QBuffer(buffer)
    device.open(QIODevice.WriteOnly)
    if not image.convertToFormat(QImage.Format_RGB32).save(device, "JPEG", 90):
        return None
    return bytes(buffer.data())


def finalize_track(track: dict) -> dict:
    """Abgeleitete Felder ergänzen, die nicht gespeichert werden müssen."""
    track["search_text"] = "\n".join((track["title"], track["artist"], track["album"])).lower()
    return track


def read_track(path: str, covers: dict) -> dict:
    """Pfad + FLAC-Tags in ein Track-Dict umwandeln. Fällt auf den Dateinamen zurück.

    Das Cover landet (einmal pro Inhalt) als Vorschaubild in `covers` (ID -> JPEG-Bytes),
    der Track verweist nur per `cover_id` darauf.
    """
    title = QFileInfo(path).completeBaseName()
    artist = ""
    album = ""
    track_no = 0
    year = 0
    duration_ms = 0
    cover_id = None
    badge = None

    try:
        audio = FLAC(path)
        badge = ("flac", "FLAC")
        title = (audio.get("title", [title])[0] or title)
        artist = (audio.get("artist", [""])[0] or "")
        album = (audio.get("album", [""])[0] or "")
        raw_track_no = audio.get("tracknumber", ["0"])[0] or "0"
        track_no = int(str(raw_track_no).split("/")[0] or 0)
        raw_date = audio.get("date", [""])[0] or audio.get("year", [""])[0] or ""
        match = re.match(r"(\d{4})", str(raw_date).strip())
        year = int(match.group(1)) if match else 0
        if audio.info is not None:
            duration_ms = int(audio.info.length * 1000)
        cover_data = select_cover(audio.pictures)
        if cover_data:
            cover_id = cover_id_for(cover_data)
            # Bei parallelem Einlesen wird ein Cover schlimmstenfalls doppelt verkleinert
            if cover_id not in covers:
                covers[cover_id] = make_thumbnail(cover_data)
            if covers[cover_id] is None:
                cover_id = None
    except Exception:
        pass

    return finalize_track({
        "path": path,
        "title": title,
        "artist": artist,
        "album": album,
        "track_no": track_no,
        "year": year,
        "duration_ms": duration_ms,
        "cover_id": cover_id,
        "badge": badge,
    })


def find_library_files(folder: str) -> list:
    """Verzeichnis rekursiv nach FLAC-Dateien durchsuchen."""
    paths = []
    for root, dirs, files in os.walk(folder):
        # Versteckte Ordner (z.B. .Trash, Cloud-Sync-Metadaten) überspringen
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            # AppleDouble-Begleitdateien (._Song.flac) sind keine echten Audiodateien
            if name.startswith("."):
                continue
            if name.lower().endswith(".flac"):
                paths.append(os.path.join(root, name))
    return paths
