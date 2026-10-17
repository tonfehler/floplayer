"""Tabellenmodell für die Bibliotheksansicht (Gruppen-Überschriften + Tracks).

Statt für jede Zelle ein QTableWidgetItem anzulegen, liefert das Modell die Daten erst,
wenn die Ansicht sie braucht – Cover werden so nur für sichtbare Zeilen dekodiert.
"""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont

from theme import ELEVATED, TEXT_PRIMARY

HEADERS = ["", "Titel", "Interpret", "Album", "Jahr"]
_TRACK_FIELDS = (None, "title", "artist", "album", "year")


class LibraryTableModel(QAbstractTableModel):
    def __init__(self, cover_icon, parent=None):
        """`cover_icon(cover_id)` liefert das (gecachte) QIcon für ein Cover oder None."""
        super().__init__(parent)
        self._cover_icon = cover_icon
        self._tracks = []
        # Pro Tabellenzeile: Track-Index (int) oder Überschrift (str)
        self._rows = []
        self._header_font = QFont()
        self._header_font.setBold(True)
        self._header_background = QColor(ELEVATED)
        self._header_foreground = QColor(TEXT_PRIMARY)

    def set_rows(self, tracks, rows):
        self.beginResetModel()
        self._tracks = tracks
        self._rows = rows
        self.endResetModel()

    def track_index_at(self, row: int):
        """Track-Index der Zeile, oder None für Überschriften/ungültige Zeilen."""
        if 0 <= row < len(self._rows):
            entry = self._rows[row]
            if isinstance(entry, int):
                return entry
        return None

    def header_rows(self):
        return [row for row, entry in enumerate(self._rows) if isinstance(entry, str)]

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return HEADERS[section]
        return None

    def flags(self, index):
        if isinstance(self._rows[index.row()], str):
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role=Qt.DisplayRole):
        entry = self._rows[index.row()]
        column = index.column()

        if isinstance(entry, str):
            if role == Qt.DisplayRole and column == 0:
                return entry
            if role == Qt.FontRole:
                return self._header_font
            if role == Qt.BackgroundRole:
                return self._header_background
            if role == Qt.ForegroundRole:
                return self._header_foreground
            return None

        track = self._tracks[entry]
        if role == Qt.DisplayRole:
            field = _TRACK_FIELDS[column]
            if field == "year":
                return str(track["year"]) if track["year"] else ""
            return track[field] if field else None
        if role == Qt.DecorationRole and column == 0:
            return self._cover_icon(track["cover_id"])
        return None
