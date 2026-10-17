"""Hauptfenster: Bibliotheksansicht, Playerleiste und Wiedergabesteuerung."""

import os

from PySide6.QtCore import Qt, QUrl, QFileInfo, QSize, QSettings, QStandardPaths, QTimer
from PySide6.QtGui import QIcon, QPixmap, QColor, QAction, QActionGroup
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QTableView,
    QHeaderView, QAbstractItemView, QLineEdit,
    QGraphicsDropShadowEffect, QToolButton, QMenu,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from discord_presence import DiscordPresenceManager
from icons import (
    make_file_icon, make_folder_icon, make_gear_icon,
    make_repeat_icon, make_sort_icon, make_volume_icon,
)
from library import (
    GROUP_OPTIONS, group_label, quality_badge_info, read_track,
    sort_key_for_group, track_matches_search,
)
from library_model import LibraryTableModel
from library_scanner import LibraryScanner
from settings_dialog import SettingsDialog
from theme import ACCENT, COVER_SIZE, ELEVATED, PLAYER_COVER_SIZE, STYLE_SHEET, TEXT_PRIMARY, TEXT_SECONDARY
from utils import format_ms


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
        # Cover-ID -> JPEG-Vorschaubild; daraus erzeugte Pixmaps/Icons werden gecacht
        self.covers = {}
        self._cover_pixmaps = {}
        self._cover_icons = {}
        self.current_index = -1
        # Zuordnung Track-Index -> Tabellenzeile (nur für aktuell sichtbare Tracks)
        self.track_to_row = {}
        self.search_query = ""
        self.group_by = GROUP_OPTIONS[0][1]
        self.repeat_mode = "off"  # "off", "all" (Bibliothek) oder "one" (aktueller Titel)
        self._scanner = None
        self._last_position_s = -1

        # Suche erst filtern, wenn kurz nicht mehr getippt wurde
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)

        self.settings = QSettings("FloPlayer", "FloPlayer")
        self.discord = DiscordPresenceManager(self.settings)

        self._build_ui()
        self._connect_signals()
        self._update_controls()
        self._update_repeat_button()
        self._restore_last_library()
        self.discord.restore()

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

        self.settings_button = QToolButton()
        self.settings_button.setObjectName("iconButton")
        self.settings_button.setIcon(QIcon(make_gear_icon(TEXT_PRIMARY)))
        self.settings_button.setIconSize(QSize(18, 18))
        self.settings_button.setToolTip("Einstellungen")
        toolbar.addWidget(self.settings_button)

        content_layout.addLayout(toolbar)

        self.playlist_model = LibraryTableModel(self._cover_icon, self)
        self.playlist_table = QTableView()
        self.playlist_table.setModel(self.playlist_model)
        self.playlist_table.setIconSize(QSize(COVER_SIZE, COVER_SIZE))
        self.playlist_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.playlist_table.verticalHeader().setDefaultSectionSize(COVER_SIZE + 4)
        self.playlist_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.playlist_table.setColumnWidth(0, COVER_SIZE + 8)
        self.playlist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.playlist_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.playlist_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        # Feste Breite statt ResizeToContents, das bei jedem Neuaufbau alle Zeilen vermessen würde
        self.playlist_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.playlist_table.setColumnWidth(
            4, self.playlist_table.fontMetrics().horizontalAdvance("00000") + 24
        )
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

    # ---------- Einstellungen ----------

    def _open_settings_dialog(self):
        dialog = SettingsDialog(self, self.discord)
        dialog.exec()

    def closeEvent(self, event):
        if self._scanner is not None:
            self._scanner.requestInterruption()
            self._scanner.wait()
        self.discord.disconnect()
        super().closeEvent(event)

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
        self.settings_button.clicked.connect(self._open_settings_dialog)
        self.search_edit.textChanged.connect(lambda _text: self._search_timer.start())
        self._search_timer.timeout.connect(self._on_search_changed)
        self.playlist_table.doubleClicked.connect(self._on_table_double_clicked)

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
        self.player.playbackStateChanged.connect(lambda _state: self._update_discord_presence())
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
        if self._scanner is not None:
            return
        self.library_button.setEnabled(False)
        self.library_button.setToolTip("Lese Bibliothek…")
        self.search_edit.setPlaceholderText("Lese Bibliothek…")

        cache_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        os.makedirs(cache_dir, exist_ok=True)
        self._scanner = LibraryScanner(folder, os.path.join(cache_dir, "library.sqlite3"), self)
        self._scanner.progress.connect(self._on_scan_progress)
        self._scanner.scanned.connect(
            lambda tracks, covers: self._on_library_scanned(folder, tracks, covers)
        )
        self._scanner.finished.connect(self._on_scanner_finished)
        self._scanner.start()

    def _on_scan_progress(self, done: int, total: int):
        self.search_edit.setPlaceholderText(f"Lese Bibliothek… {done}/{total}")

    def _on_library_scanned(self, folder: str, tracks: list, covers: dict):
        self.search_query = ""
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)
        self._search_timer.stop()

        self.tracks = tracks
        self.covers = covers
        self._cover_pixmaps.clear()
        self._cover_icons.clear()
        self.settings.setValue("library/path", folder)
        self.current_index = -1
        self._resort_and_populate()

    def _on_scanner_finished(self):
        self._scanner.deleteLater()
        self._scanner = None
        self.library_button.setEnabled(True)
        self.library_button.setToolTip("Bibliothek wählen…")
        self.search_edit.setPlaceholderText("Suchen…")

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

    def _on_search_changed(self):
        self.search_query = self.search_edit.text().strip().lower()
        self._populate_playlist_table(self.group_by)

    def _populate_playlist_table(self, group_by):
        rows = []
        last_label = object()  # Platzhalter, damit die erste Gruppe immer eine Überschrift bekommt
        for track_index, track in enumerate(self.tracks):
            if not track_matches_search(track, self.search_query):
                continue
            label = group_label(track, group_by)
            if label is not None and label != last_label:
                rows.append(label)
                last_label = label
            rows.append(track_index)

        table = self.playlist_table
        table.setUpdatesEnabled(False)
        try:
            self.playlist_model.set_rows(self.tracks, rows)
            table.clearSpans()
            column_count = self.playlist_model.columnCount()
            for row in self.playlist_model.header_rows():
                table.setSpan(row, 0, 1, column_count)
        finally:
            table.setUpdatesEnabled(True)

        self.track_to_row = {
            entry: row for row, entry in enumerate(rows) if isinstance(entry, int)
        }

        if 0 <= self.current_index < len(self.tracks):
            table_row = self.track_to_row.get(self.current_index)
            if table_row is not None:
                table.selectRow(table_row)

    def _cover_pixmap(self, cover_id, size):
        """Skalierte Pixmap eines Covers (pro Cover und Größe nur einmal dekodiert)."""
        if cover_id is None:
            return None
        key = (cover_id, size)
        if key in self._cover_pixmaps:
            return self._cover_pixmaps[key]
        pixmap = None
        data = self.covers.get(cover_id)
        if data:
            source = QPixmap()
            if source.loadFromData(data):
                ratio = self.devicePixelRatioF()
                pixel_size = round(size * ratio)
                pixmap = source.scaled(
                    pixel_size, pixel_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                pixmap.setDevicePixelRatio(ratio)
        self._cover_pixmaps[key] = pixmap
        return pixmap

    def _cover_icon(self, cover_id):
        if cover_id not in self._cover_icons:
            pixmap = self._cover_pixmap(cover_id, COVER_SIZE)
            self._cover_icons[cover_id] = QIcon(pixmap) if pixmap is not None else None
        return self._cover_icons[cover_id]

    def _set_cover_art(self, cover_id):
        pixmap = self._cover_pixmap(cover_id, PLAYER_COVER_SIZE)
        self.cover_art_label.setPixmap(pixmap if pixmap is not None else QPixmap())

    def _set_quality_badge(self, badge):
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
        self.track_to_row = {}
        self.playlist_model.set_rows(self.tracks, [])
        self.playlist_table.clearSpans()
        self._load_and_play(path)

    def _on_table_double_clicked(self, index):
        track_index = self.playlist_model.track_index_at(index.row())
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
            cover_id = track["cover_id"]
            badge = track["badge"]
        else:
            title = QFileInfo(path).completeBaseName()
            artist = ""
            cover_id = read_track(path, self.covers)["cover_id"] if path.lower().endswith(".flac") else None
            badge = quality_badge_info(path)
        self.now_playing_title.setText(title)
        self.now_playing_artist.setText(artist)
        self.setWindowTitle(f"{title} – FloPlayer")
        self._set_cover_art(cover_id)
        self._set_quality_badge(badge)
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
            # Label nur neu setzen, wenn sich die angezeigte Sekunde ändert
            position_s = position // 1000
            if position_s != self._last_position_s:
                self._last_position_s = position_s
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

    def _update_discord_presence(self):
        if self.player.source().isEmpty():
            self.discord.clear_now_playing()
            return
        title = self.now_playing_title.text()
        artist = self.now_playing_artist.text()
        playing = self.player.playbackState() == QMediaPlayer.PlayingState
        self.discord.update_now_playing(title, artist, playing, self.player.position())

    # ---------- Seek-Slider ----------

    def _on_slider_pressed(self):
        self._seeking = True

    def _on_slider_moved(self, value: int):
        self._last_position_s = -1
        self.time_current.setText(format_ms(value))

    def _on_slider_released(self):
        self._seeking = False
        self.player.setPosition(self.position_slider.value())
