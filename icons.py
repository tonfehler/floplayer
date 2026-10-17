"""Selbst gezeichnete, minimalistische Icons (statt Emojis) für die Toolbar- und Transport-Buttons."""

import math

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF


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


def make_gear_icon(color: str, size: int = 18) -> QPixmap:
    """Minimalistisches Zahnrad-Icon für den Einstellungen-Button."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.4)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    center = QPointF(size / 2, size / 2)
    radius = 3.6
    painter.drawEllipse(center, radius, radius)

    for i in range(8):
        angle = math.radians(i * 45)
        x1 = center.x() + math.cos(angle) * (radius + 0.8)
        y1 = center.y() + math.sin(angle) * (radius + 0.8)
        x2 = center.x() + math.cos(angle) * (radius + 2.8)
        y2 = center.y() + math.sin(angle) * (radius + 2.8)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

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
