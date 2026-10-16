"""Einstellungen-Dialog (aktuell: Discord Rich Presence an/aus + Client ID)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from discord_presence import DiscordPresenceManager
from theme import STYLE_SHEET


class SettingsDialog(QDialog):
    def __init__(self, parent, discord: DiscordPresenceManager):
        super().__init__(parent)
        self.discord = discord

        self.setWindowTitle("Einstellungen")
        self.setStyleSheet(STYLE_SHEET)
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.checkbox = QCheckBox("Discord Rich Presence aktivieren")
        self.checkbox.setChecked(discord.enabled)
        layout.addWidget(self.checkbox)

        id_row = QHBoxLayout()
        id_row.addWidget(QLabel("Discord Client ID:"))
        self.client_id_edit = QLineEdit(discord.client_id)
        self.client_id_edit.setPlaceholderText("z.B. 123456789012345678")
        id_row.addWidget(self.client_id_edit, stretch=1)
        layout.addLayout(id_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("secondaryLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        hint = QLabel(
            "Eigene Anwendung unter discord.com/developers/applications anlegen "
            "und die Client ID hier eintragen. Discord muss lokal laufen, damit "
            "die Verbindung klappt."
        )
        hint.setObjectName("secondaryLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.checkbox.toggled.connect(lambda _checked: self._apply_state())
        self.client_id_edit.editingFinished.connect(self._apply_state)

        close_button = QPushButton("Schließen")
        close_button.setObjectName("openButton")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

    def _apply_state(self):
        self.discord.set_client_id(self.client_id_edit.text().strip())
        if self.checkbox.isChecked():
            error = self.discord.enable()
            self.status_label.setText(error or "Verbunden.")
        else:
            self.discord.disable()
            self.status_label.setText("Deaktiviert.")
