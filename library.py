"""Einlesen von FLAC-Bibliotheken: Tags, Cover, Qualitätsinfo, Sortierung/Gruppierung/Suche."""

import os
import re

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from PySide6.QtCore import QFileInfo

# (Anzeigetext, interner Schlüssel) für die Gruppierungs-/Sortierauswahl
GROUP_OPTIONS = [
    ("Interpret", "artist"),
    ("Album", "album"),
    ("Jahr", "year"),
    ("Titel (ohne Gruppierung)", "title"),
]


def sort_key_for_group(group_by):
    if group_by == "artist":
        return lambda t: (t["artist"].lower(), t["album"].lower(), t["track_no"])
    if group_by == "album":
        return lambda t: (t["album"].lower(), t["artist"].lower(), t["track_no"])
    if group_by == "year":
        return lambda t: (t["year"], t["artist"].lower(), t["album"].lower(), t["track_no"])
    return lambda t: (t["title"].lower(),)


def track_matches_search(track, query):
    """True, wenn Titel, Interpret oder Album den Suchbegriff enthält (case-insensitive)."""
    if not query:
        return True
    query = query.lower()
    return (
        query in track["title"].lower()
        or query in track["artist"].lower()
        or query in track["album"].lower()
    )


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


def read_track(path: str) -> dict:
    """Pfad + FLAC-Tags in ein Track-Dict umwandeln. Fällt auf den Dateinamen zurück."""
    title = QFileInfo(path).completeBaseName()
    artist = ""
    album = ""
    track_no = 0
    year = 0
    duration_ms = 0
    cover_data = None

    try:
        audio = FLAC(path)
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
    except Exception:
        pass

    return {
        "path": path,
        "title": title,
        "artist": artist,
        "album": album,
        "track_no": track_no,
        "year": year,
        "duration_ms": duration_ms,
        "cover_data": cover_data,
    }


def scan_library(folder: str) -> list:
    """Verzeichnis rekursiv nach FLAC-Dateien durchsuchen und Tags lesen."""
    tracks = []
    for root, dirs, files in os.walk(folder):
        # Versteckte Ordner (z.B. .Trash, Cloud-Sync-Metadaten) überspringen
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            # AppleDouble-Begleitdateien (._Song.flac) sind keine echten Audiodateien
            if name.startswith("."):
                continue
            if name.lower().endswith(".flac"):
                tracks.append(read_track(os.path.join(root, name)))
    tracks.sort(key=lambda t: (t["artist"].lower(), t["album"].lower(), t["track_no"]))
    return tracks
