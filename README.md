# Music Player

Basic Desktop-Player mit PySide6 (Qt 6). Spielt FLAC, MP3, OGG, WAV, M4A und AAC ab.

## Einrichtung

```bash
cd music-player
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Starten

```bash
python main.py
```

## Geplant

- Metadaten (Titel, Künstler, Cover) mit `mutagen`
- Ordnerbibliothek mit Playlist und SQLite
- Discord Rich Presence über `pypresence`
- Media-Keys und Tray-Icon
