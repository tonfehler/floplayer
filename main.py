import os
import re
import sys

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from PySide6.QtCore import Qt, QUrl, QFileInfo, QSize, QPointF, QRectF, QSettings
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QPolygonF, QAction, QActionGroup
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit,
    QGraphicsDropShadowEffect, QToolButton, QMenu,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

COVER_SIZE = 48
PLAYER_COVER_SIZE = 56

# Dunkles Farbschema im Stil von Apple Music / Spotify, Akzent in Hellblau statt Grün
BG = "#1c1c1e"
PANEL_BG = "#222224"
ELEVATED = "#2c2c2e"
BORDER = "#3a3a3c"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#A7A7A7"
ACCENT = "#4FC3F7"
ACCENT_HOVER = "#7AD6FA"

STYLE_SHEET = f"""
QMainWindow, QWidget#centralWidget {{
    background-color: {BG};
}}
QLabel {{
    color: {TEXT_PRIMARY};
}}
QLabel#secondaryLabel {{
    color: {TEXT_SECONDARY};
    font-size: 9pt;
}}
QPushButton {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    color: {TEXT_PRIMARY};
}}
QPushButton:disabled {{
    color: #4d4d4d;
}}
QToolButton#iconButton {{
    background-color: {ELEVATED};
    border: none;
    border-radius: 18px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    padding: 0px;
}}
QToolButton#iconButton:hover {{
    background-color: #2f2f2f;
}}
QToolButton#iconButton::menu-indicator {{
    image: none;
    width: 0px;
}}
QMenu {{
    background-color: {ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: #0b0b0b;
}}
QPushButton#playButton {{
    background-color: {ACCENT};
    color: #0b0b0b;
    border-radius: 22px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    font-size: 15pt;
    padding: 0px;
}}
QPushButton#playButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#transportButton {{
    font-size: 13pt;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    border-radius: 16px;
}}
QLineEdit#searchEdit {{
    background-color: {ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 5px 12px;
}}
QLineEdit#searchEdit:focus {{
    border: 1px solid {ACCENT};
}}
QTableWidget {{
    background-color: {BG};
    alternate-background-color: #242426;
    gridline-color: transparent;
    border: none;
    color: {TEXT_PRIMARY};
}}
QTableWidget::item {{
    padding: 4px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: #1c323c;
    color: {ACCENT};
}}
QLabel#qualityBadge {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 1px 7px;
    font-size: 8pt;
    font-weight: 700;
    color: {TEXT_SECONDARY};
    background-color: {ELEVATED};
}}
QLabel#qualityBadge[flac="true"] {{
    border: 1px solid {ACCENT};
    color: {ACCENT};
    background-color: #16303a;
}}
QHeaderView::section {{
    background-color: {BG};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px;
    font-weight: 600;
}}
QWidget#playerBar {{
    background-color: {PANEL_BG};
    border-top: 1px solid {BORDER};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: #3a3a3a;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::add-page:horizontal {{
    background: #3a3a3a;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TEXT_PRIMARY};
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT};
}}
QScrollBar:vertical {{
    background: {BG};
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: #3a3a3a;
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    height: 0px;
}}
"""

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


def format_ms(ms: int) -> str:
    """Millisekunden in m:ss bzw. h:mm:ss umwandeln."""
    total_seconds = ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"


def make_volume_icon(color: str, size: int = 18) -> QPixmap:
    """Minimalistisches Lautsprecher-Icon (Körper + Schallwellen) statt Emoji."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))

    cone = QPolygonF([
        QPointF(2.5, 7), QPointF(5.5, 7), QPointF(9.5, 3.5),
        QPointF(9.5, 14.5), QPointF(5.5, 11), QPointF(2.5, 11),
    ])
    painter.drawPolygon(cone)

    pen = painter.pen()
    pen.setColor(QColor(color))
    pen.setWidthF(1.3)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(QRectF(10.5, 4.5, 5, 9), -55 * 16, 110 * 16)
    painter.drawArc(QRectF(12.5, 2, 8.5, 14), -55 * 16, 110 * 16)

    painter.end()
    return pixmap


def make_folder_icon(color: str, size: int = 18) -> QPixmap:
    """Minimalistisches Ordner-Icon für den Bibliotheks-Button."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = painter.pen()
    pen.setColor(QColor(color))
    pen.setWidthF(1.4)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    folder = QPolygonF([
        QPointF(2, 5.5), QPointF(7, 5.5), QPointF(8.5, 7.5),
        QPointF(16, 7.5), QPointF(16, 14.5), QPointF(2, 14.5),
    ])
    painter.drawPolygon(folder)

    painter.end()
    return pixmap


def make_file_icon(color: str, size: int = 18) -> QPixmap:
    """Minimalistisches Datei-Icon für den 'Datei öffnen'-Button."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = painter.pen()
    pen.setColor(QColor(color))
    pen.setWidthF(1.3)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    body = QPolygonF([
        QPointF(4, 2), QPointF(11, 2), QPointF(14, 5),
        QPointF(14, 16), QPointF(4, 16),
    ])
    painter.drawPolygon(body)
    painter.drawLine(QPointF(11, 2), QPointF(11, 5))
    painter.drawLine(QPointF(11, 5), QPointF(14, 5))
    painter.drawLine(QPointF(6.5, 9.5), QPointF(11.5, 9.5))
    painter.drawLine(QPointF(6.5, 12.5), QPointF(11.5, 12.5))

    painter.end()
    return pixmap


def make_sort_icon(color: str, size: int = 18) -> QPixmap:
    """Minimalistisches Sortier-Icon (Pfeile + absteigende Linien) für den Sortier-Button."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))

    painter.drawPolygon(QPolygonF([QPointF(4.5, 8), QPointF(8.5, 8), QPointF(6.5, 4)]))
    painter.drawPolygon(QPolygonF([QPointF(4.5, 10), QPointF(8.5, 10), QPointF(6.5, 14)]))

    pen = painter.pen()
    pen.setColor(QColor(color))
    pen.setWidthF(1.3)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(10.5, 5), QPointF(15.5, 5))
    painter.drawLine(QPointF(10.5, 9), QPointF(14.5, 9))
    painter.drawLine(QPointF(10.5, 13), QPointF(13.5, 13))

    painter.end()
    return pixmap


def make_repeat_icon(color: str, mode: str = "off", size: int = 18) -> QPixmap:
    """Loop-Icon (kreisender Pfeil); bei mode='one' zusätzlich mit kleiner '1'."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.4)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    rect = QRectF(3, 3, 12, 12)
    painter.drawArc(rect, 20 * 16, 300 * 16)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    arrow = QPolygonF([QPointF(13.6, 3.0), QPointF(16.2, 4.4), QPointF(13.5, 6.2)])
    painter.drawPolygon(arrow)

    if mode == "one":
        font = painter.font()
        font.setPixelSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "1")

    painter.end()
    return pixmap


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


class PlayerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FloPlayer")
        self.resize(1000, 640)

        # Audio-Pipeline: QMediaPlayer -> QAudioOutput
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)

        # Verhindert, dass der Player den Slider überschreibt, während er gezogen wird
        self._seeking = False

        self.tracks = []
        self.current_index = -1
        # Zuordnung Tabellenzeile -> Track-Index (None für Gruppen-Überschriften)
        self.row_to_track = []
        self.track_to_row = {}
        self.search_query = ""
        self.group_by = GROUP_OPTIONS[0][1]
        self.repeat_mode = "off"  # "off", "all" (Bibliothek) oder "one" (aktueller Titel)

        self.settings = QSettings("FloPlayer", "FloPlayer")

        self._build_ui()
        self._connect_signals()
        self._update_controls()
        self._update_repeat_button()
        self._restore_last_library()

    # ---------- UI aufbauen ----------

    def _build_ui(self):
        self.setStyleSheet(STYLE_SHEET)

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_library_view(), stretch=1)
        root_layout.addWidget(self._build_player_bar())

    def _build_library_view(self):
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 12)
        content_layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.library_button = QToolButton()
        self.library_button.setObjectName("iconButton")
        self.library_button.setIcon(QIcon(make_folder_icon(TEXT_PRIMARY)))
        self.library_button.setIconSize(QSize(18, 18))
        self.library_button.setToolTip("Bibliothek wählen…")
        toolbar.addWidget(self.library_button)

        self.open_button = QToolButton()
        self.open_button.setObjectName("iconButton")
        self.open_button.setIcon(QIcon(make_file_icon(TEXT_PRIMARY)))
        self.open_button.setIconSize(QSize(18, 18))
        self.open_button.setToolTip("Datei öffnen…")
        toolbar.addWidget(self.open_button)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchEdit")
        self.search_edit.setPlaceholderText("Suchen…")
        self.search_edit.setClearButtonEnabled(True)
        toolbar.addWidget(self.search_edit, stretch=1)

        self.sort_button = QToolButton()
        self.sort_button.setObjectName("iconButton")
        self.sort_button.setIcon(QIcon(make_sort_icon(TEXT_PRIMARY)))
        self.sort_button.setIconSize(QSize(18, 18))
        self.sort_button.setPopupMode(QToolButton.InstantPopup)
        self.sort_button.setMenu(self._build_sort_menu())
        toolbar.addWidget(self.sort_button)

        content_layout.addLayout(toolbar)

        self.playlist_table = QTableWidget(0, 5)
        self.playlist_table.setHorizontalHeaderLabels(["", "Titel", "Interpret", "Album", "Jahr"])
        self.playlist_table.setIconSize(QSize(COVER_SIZE, COVER_SIZE))
        self.playlist_table.verticalHeader().setDefaultSectionSize(COVER_SIZE + 4)
        self.playlist_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.playlist_table.setColumnWidth(0, COVER_SIZE + 8)
        self.playlist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.playlist_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.playlist_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.playlist_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.playlist_table.verticalHeader().setVisible(False)
        self.playlist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.playlist_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.playlist_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.playlist_table.setShowGrid(False)
        self.playlist_table.setAlternatingRowColors(True)
        self.playlist_table.setFocusPolicy(Qt.NoFocus)
        content_layout.addWidget(self.playlist_table, stretch=1)

        return content

    def _build_sort_menu(self):
        menu = QMenu(self)
        group = QActionGroup(self)
        group.setExclusive(True)
        for text, key in GROUP_OPTIONS:
            action = QAction(text, self)
            action.setCheckable(True)
            action.setChecked(key == self.group_by)
            action.triggered.connect(lambda _checked, key=key: self._set_group_by(key))
            group.addAction(action)
            menu.addAction(action)
        self._update_sort_tooltip()
        return menu

    def _set_group_by(self, key):
        self.group_by = key
        self._update_sort_tooltip()
        self._resort_and_populate()

    def _update_sort_tooltip(self):
        label = next((text for text, key in GROUP_OPTIONS if key == self.group_by), "")
        self.sort_button.setToolTip(f"Sortieren nach: {label}")

    def _build_player_bar(self):
        player_bar = QWidget()
        player_bar.setObjectName("playerBar")
        player_bar.setFixedHeight(96)
        bar_layout = QHBoxLayout(player_bar)
        bar_layout.setContentsMargins(16, 12, 16, 12)
        bar_layout.setSpacing(16)

        # Links: Cover + Titel/Interpret des aktuellen Songs
        now_playing = QHBoxLayout()
        now_playing.setSpacing(10)

        self.cover_art_label = QLabel()
        self.cover_art_label.setAlignment(Qt.AlignCenter)
        self.cover_art_label.setFixedSize(PLAYER_COVER_SIZE, PLAYER_COVER_SIZE)
        self.cover_art_label.setStyleSheet(
            f"background-color: {ELEVATED}; border-radius: 4px;"
        )
        now_playing.addWidget(self.cover_art_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.now_playing_title = QLabel("Keine Datei geladen")
        self.now_playing_title.setStyleSheet("font-size: 11pt; font-weight: 600;")

        artist_row = QHBoxLayout()
        artist_row.setSpacing(6)
        self.now_playing_artist = QLabel("")
        self.now_playing_artist.setObjectName("secondaryLabel")
        artist_row.addWidget(self.now_playing_artist)
        artist_row.addStretch(1)
        self.quality_badge = QLabel("")
        self.quality_badge.setObjectName("qualityBadge")
        self.quality_badge.setVisible(False)
        artist_row.addWidget(self.quality_badge)

        text_col.addStretch(1)
        text_col.addWidget(self.now_playing_title)
        text_col.addLayout(artist_row)
        text_col.addStretch(1)
        now_playing.addLayout(text_col, stretch=1)

        now_playing_widget = QWidget()
        now_playing_widget.setLayout(now_playing)
        now_playing_widget.setFixedWidth(300)
        bar_layout.addWidget(now_playing_widget)

        # Mitte: Transportsteuerung + Fortschritt
        center_col = QVBoxLayout()
        center_col.setSpacing(6)

        transport_row = QHBoxLayout()
        transport_row.setSpacing(12)
        transport_row.addStretch(1)
        self.prev_button = QPushButton("⏮")
        self.prev_button.setObjectName("transportButton")
        self.play_button = QPushButton("▶")
        self.play_button.setObjectName("playButton")
        self.stop_button = QPushButton("⏹")
        self.stop_button.setObjectName("transportButton")
        self.next_button = QPushButton("⏭")
        self.next_button.setObjectName("transportButton")
        self.repeat_button = QPushButton()
        self.repeat_button.setObjectName("transportButton")
        self.repeat_button.setIconSize(QSize(18, 18))
        for btn in (self.prev_button, self.play_button, self.stop_button,
                    self.next_button, self.repeat_button):
            transport_row.addWidget(btn)
        transport_row.addStretch(1)
        center_col.addLayout(transport_row)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        self.time_current = QLabel("0:00")
        self.time_current.setObjectName("secondaryLabel")
        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("secondaryLabel")
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        progress_row.addWidget(self.time_current)
        progress_row.addWidget(self.position_slider, stretch=1)
        progress_row.addWidget(self.time_total)
        center_col.addLayout(progress_row)

        bar_layout.addLayout(center_col, stretch=1)

        # Rechts: Lautstärke
        volume_row = QHBoxLayout()
        volume_row.setSpacing(8)
        volume_icon = QLabel()
        volume_icon.setPixmap(make_volume_icon(TEXT_SECONDARY))
        volume_row.addWidget(volume_icon)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        volume_row.addWidget(self.volume_slider)

        volume_widget = QWidget()
        volume_widget.setLayout(volume_row)
        volume_widget.setFixedWidth(160)
        bar_layout.addWidget(volume_widget, alignment=Qt.AlignRight)

        return player_bar

    def _connect_signals(self):
        self.library_button.clicked.connect(self.choose_library)
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.playlist_table.cellDoubleClicked.connect(self._on_table_double_clicked)

        self.open_button.clicked.connect(self.open_file)
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button.clicked.connect(self.stop)
        self.prev_button.clicked.connect(self.play_previous)
        self.next_button.clicked.connect(self.play_next)
        self.repeat_button.clicked.connect(self.toggle_repeat_mode)

        self.volume_slider.valueChanged.connect(
            lambda v: self.audio_output.setVolume(v / 100)
        )

        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.playbackStateChanged.connect(self._update_controls)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.errorOccurred.connect(self.on_error)

        self.position_slider.sliderPressed.connect(self._on_slider_pressed)
        self.position_slider.sliderMoved.connect(self._on_slider_moved)
        self.position_slider.sliderReleased.connect(self._on_slider_released)

    # ---------- Bibliothek ----------

    def choose_library(self):
        folder = QFileDialog.getExistingDirectory(self, "FLAC-Bibliothek wählen")
        if not folder:
            return
        self._load_library_folder(folder)

    def _restore_last_library(self):
        folder = self.settings.value("library/path", "")
        if folder and os.path.isdir(folder):
            self._load_library_folder(folder)

    def _load_library_folder(self, folder: str):
        self.search_query = ""
        self.search_edit.clear()
        self.library_button.setEnabled(False)
        self.library_button.setToolTip("Lese Bibliothek…")
        QApplication.processEvents()
        try:
            self.tracks = scan_library(folder)
        finally:
            self.library_button.setEnabled(True)
            self.library_button.setToolTip("Bibliothek wählen…")

        self.settings.setValue("library/path", folder)
        self.current_index = -1
        self._resort_and_populate()

    def _resort_and_populate(self):
        """Bibliothek gemäß der gewählten Gruppierung neu sortieren und die Tabelle neu aufbauen."""
        current_path = (
            self.tracks[self.current_index]["path"]
            if 0 <= self.current_index < len(self.tracks)
            else None
        )

        self.tracks.sort(key=sort_key_for_group(self.group_by))

        if current_path is not None:
            self.current_index = next(
                (i for i, t in enumerate(self.tracks) if t["path"] == current_path), -1
            )

        self._populate_playlist_table(self.group_by)
        self._update_controls()

    def _on_search_changed(self, text: str):
        self.search_query = text.strip()
        self._populate_playlist_table(self.group_by)

    def _populate_playlist_table(self, group_by):
        table = self.playlist_table
        table.setRowCount(0)
        self.row_to_track = []
        last_label = object()  # Platzhalter, damit die erste Gruppe immer eine Überschrift bekommt

        for track_index, track in enumerate(self.tracks):
            if not track_matches_search(track, self.search_query):
                continue
            label = group_label(track, group_by)
            if label is not None and label != last_label:
                self._add_group_header_row(label)
                last_label = label
            self._add_track_row(track, track_index)

        self.track_to_row = {
            track_index: row
            for row, track_index in enumerate(self.row_to_track)
            if track_index is not None
        }

        if 0 <= self.current_index < len(self.tracks):
            table_row = self.track_to_row.get(self.current_index)
            if table_row is not None:
                table.selectRow(table_row)

    def _add_group_header_row(self, label):
        table = self.playlist_table
        row = table.rowCount()
        table.insertRow(row)
        item = QTableWidgetItem(label)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        item.setBackground(QColor(ELEVATED))
        item.setForeground(QColor(TEXT_PRIMARY))
        table.setItem(row, 0, item)
        table.setSpan(row, 0, 1, table.columnCount())
        self.row_to_track.append(None)

    def _add_track_row(self, track, track_index):
        table = self.playlist_table
        row = table.rowCount()
        table.insertRow(row)
        cover_item = QTableWidgetItem()
        icon = self._cover_icon(track["cover_data"])
        if icon is not None:
            cover_item.setIcon(icon)
        table.setItem(row, 0, cover_item)
        table.setItem(row, 1, QTableWidgetItem(track["title"]))
        table.setItem(row, 2, QTableWidgetItem(track["artist"]))
        table.setItem(row, 3, QTableWidgetItem(track["album"]))
        table.setItem(row, 4, QTableWidgetItem(str(track["year"]) if track["year"] else ""))
        self.row_to_track.append(track_index)

    @staticmethod
    def _cover_pixmap(cover_data, size):
        if not cover_data:
            return None
        pixmap = QPixmap()
        if not pixmap.loadFromData(cover_data):
            return None
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    @classmethod
    def _cover_icon(cls, cover_data):
        pixmap = cls._cover_pixmap(cover_data, COVER_SIZE)
        return QIcon(pixmap) if pixmap is not None else None

    def _set_cover_art(self, cover_data):
        pixmap = self._cover_pixmap(cover_data, PLAYER_COVER_SIZE)
        self.cover_art_label.setPixmap(pixmap if pixmap is not None else QPixmap())

    def _set_quality_badge(self, path):
        badge = quality_badge_info(path)
        if badge is None:
            self.quality_badge.setVisible(False)
            self.quality_badge.setGraphicsEffect(None)
            return

        kind, text = badge
        self.quality_badge.setText(text)
        self.quality_badge.setVisible(True)
        self.quality_badge.setProperty("flac", kind == "flac")
        if kind == "flac":
            glow = QGraphicsDropShadowEffect(self.quality_badge)
            glow.setColor(QColor(ACCENT))
            glow.setBlurRadius(18)
            glow.setOffset(0, 0)
            self.quality_badge.setGraphicsEffect(glow)
        else:
            self.quality_badge.setGraphicsEffect(None)
        # Stylesheet mit dem neuen dynamischen "flac"-Property neu anwenden
        self.quality_badge.style().unpolish(self.quality_badge)
        self.quality_badge.style().polish(self.quality_badge)

    # ---------- Aktionen ----------

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Audiodatei öffnen",
            "",
            "Audio (*.flac *.mp3 *.ogg *.wav *.m4a *.aac);;Alle Dateien (*)",
        )
        if not path:
            return

        self.tracks = []
        self.current_index = -1
        self.row_to_track = []
        self.track_to_row = {}
        self.playlist_table.setRowCount(0)
        self._load_and_play(path)

    def _on_table_double_clicked(self, row: int, _column: int = 0):
        if not (0 <= row < len(self.row_to_track)):
            return
        track_index = self.row_to_track[row]
        if track_index is not None:
            self.play_track(track_index)

    def play_track(self, track_index: int):
        if not (0 <= track_index < len(self.tracks)):
            return
        self.current_index = track_index
        self._load_and_play(self.tracks[track_index]["path"])
        table_row = self.track_to_row.get(track_index)
        if table_row is not None:
            self.playlist_table.selectRow(table_row)

    def play_previous(self):
        if self.current_index > 0:
            self.play_track(self.current_index - 1)

    def play_next(self):
        if self.current_index != -1 and self.current_index + 1 < len(self.tracks):
            self.play_track(self.current_index + 1)
        elif self.repeat_mode == "all" and self.tracks:
            self.play_track(0)

    def toggle_repeat_mode(self):
        order = ["off", "all", "one"]
        self.repeat_mode = order[(order.index(self.repeat_mode) + 1) % len(order)]
        self._update_repeat_button()

    def _update_repeat_button(self):
        active = self.repeat_mode != "off"
        color = ACCENT if active else TEXT_SECONDARY
        self.repeat_button.setIcon(QIcon(make_repeat_icon(color, self.repeat_mode)))
        tooltip = {
            "off": "Wiederholen: Aus",
            "all": "Wiederholen: Bibliothek",
            "one": "Wiederholen: Titel",
        }[self.repeat_mode]
        self.repeat_button.setToolTip(tooltip)

    def _load_and_play(self, path: str):
        self.player.setSource(QUrl.fromLocalFile(path))
        if 0 <= self.current_index < len(self.tracks):
            track = self.tracks[self.current_index]
            title = track["title"]
            artist = track["artist"]
            cover_data = track["cover_data"]
        else:
            title = QFileInfo(path).completeBaseName()
            artist = ""
            cover_data = read_track(path)["cover_data"] if path.lower().endswith(".flac") else None
        self.now_playing_title.setText(title)
        self.now_playing_artist.setText(artist)
        self.setWindowTitle(f"{title} – FloPlayer")
        self._set_cover_art(cover_data)
        self._set_quality_badge(path)
        self.player.play()

    def toggle_play(self):
        if self.player.source().isEmpty():
            if self.tracks:
                self.play_track(0)
            else:
                self.open_file()
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        self.player.stop()

    # ---------- Reaktionen auf Player-Signale ----------

    def on_position_changed(self, position: int):
        if not self._seeking:
            self.position_slider.setValue(position)
        self.time_current.setText(format_ms(position))

    def on_duration_changed(self, duration: int):
        self.position_slider.setRange(0, duration)
        self.time_total.setText(format_ms(duration))

    def on_media_status_changed(self, status):
        if status != QMediaPlayer.EndOfMedia:
            return
        if self.repeat_mode == "one":
            self.player.setPosition(0)
            self.player.play()
            return
        self.play_next()

    def on_error(self, error, error_string: str):
        if error_string:
            self.now_playing_title.setText(f"Fehler: {error_string}")
            self.now_playing_artist.setText("")
            self.quality_badge.setVisible(False)
            self.quality_badge.setGraphicsEffect(None)

    def _update_controls(self, *_):
        playing = self.player.playbackState() == QMediaPlayer.PlayingState
        self.play_button.setText("⏸" if playing else "▶")
        has_source = not self.player.source().isEmpty()
        self.stop_button.setEnabled(has_source)
        self.position_slider.setEnabled(has_source)
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(
            self.current_index != -1 and self.current_index + 1 < len(self.tracks)
        )

    # ---------- Seek-Slider ----------

    def _on_slider_pressed(self):
        self._seeking = True

    def _on_slider_moved(self, value: int):
        self.time_current.setText(format_ms(value))

    def _on_slider_released(self):
        self._seeking = False
        self.player.setPosition(self.position_slider.value())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PlayerWindow()
    window.show()
    sys.exit(app.exec())
