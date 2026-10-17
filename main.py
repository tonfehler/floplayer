import sys

from PySide6.QtWidgets import QApplication

from player_window import PlayerWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Bestimmt u.a. den Ordner für den Bibliotheks-Cache (QStandardPaths.AppDataLocation)
    app.setApplicationName("FloPlayer")
    window = PlayerWindow()
    window.show()
    sys.exit(app.exec())
