"""Farbschema und Qt-Stylesheet für den FloPlayer-Look (Apple Music/Spotify-artig, Hellblau-Akzent)."""

COVER_SIZE = 48
PLAYER_COVER_SIZE = 56

BG = "#1c1c1e"
PANEL_BG = "#222224"
ELEVATED = "#2c2c2e"
BORDER = "#3a3a3c"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#A7A7A7"
ACCENT = "#4FC3F7"
ACCENT_HOVER = "#7AD6FA"

STYLE_SHEET = f"""
QMainWindow, QWidget#centralWidget, QDialog {{
    background-color: {BG};
}}
QLabel {{
    color: {TEXT_PRIMARY};
}}
QLabel#secondaryLabel {{
    color: {TEXT_SECONDARY};
    font-size: 9pt;
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}
QLineEdit {{
    background-color: {ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 10px;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
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
QTableView {{
    background-color: {BG};
    alternate-background-color: #242426;
    gridline-color: transparent;
    border: none;
    color: {TEXT_PRIMARY};
}}
QTableView::item {{
    padding: 4px;
    border: none;
}}
QTableView::item:selected {{
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
