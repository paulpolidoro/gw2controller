from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap

from gw2controller.controller.xinput import FACE_BUTTONS
from gw2controller.overlay.theme import OverlayTheme, overlay_theme

FACE_COLORS = {
    "A": QColor("#2ECC71"),
    "B": QColor("#E74C3C"),
    "X": QColor("#3498DB"),
    "Y": QColor("#F1C40F"),
}


def glyph_pixmap(
    button: str,
    size: int,
    badge: str | None = None,
    pressed: bool = False,
    theme: OverlayTheme | str | None = None,
) -> QPixmap:
    style = theme if isinstance(theme, OverlayTheme) else overlay_theme(theme)
    pixel = max(24, int(size))
    pixmap = QPixmap(pixel, pixel)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    margin = 2
    rect = QRect(margin, margin, pixel - margin * 2, pixel - margin * 2)
    _draw_glyph(painter, button.upper(), rect, pressed, style)
    if badge:
        _draw_badge(painter, badge, QRect(0, 0, pixel, pixel))
    painter.end()
    return pixmap


def _draw_glyph(painter: QPainter, button: str, rect: QRect, pressed: bool, theme: OverlayTheme) -> None:
    if button in FACE_BUTTONS:
        color = QColor(FACE_COLORS[button])
        if pressed:
            color = color.lighter(120)
        painter.setBrush(color)
        painter.setPen(QPen(QColor(0, 0, 0, 90), 1))
        painter.drawEllipse(rect)
        painter.setPen(QColor("#101114"))
        font = QFont("Segoe UI", max(8, rect.height() // 2), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, button)
        return

    painter.setBrush(QColor(theme.glyph_bg).darker(108) if pressed else theme.glyph_bg)
    painter.setPen(QPen(theme.glyph_border, 1))

    if button in ("LB", "RB"):
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 8, 8)
        painter.drawPath(path)
        painter.setPen(theme.glyph_fg)
        font = QFont("Segoe UI", max(7, rect.height() // 3), QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, button)
        return

    if button in ("LT", "RT"):
        path = QPainterPath()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        path.moveTo(x + w * 0.18, y + h)
        path.lineTo(x + w * 0.30, y)
        path.lineTo(x + w * 0.70, y)
        path.lineTo(x + w * 0.82, y + h)
        path.closeSubpath()
        painter.drawPath(path)
        painter.setPen(theme.glyph_fg)
        font = QFont("Segoe UI", max(7, rect.height() // 3), QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(rect.adjusted(0, 4, 0, 0), Qt.AlignmentFlag.AlignCenter, button)
        return

    if button in ("LS", "RS"):
        painter.drawEllipse(rect)
        inner = rect.adjusted(rect.width() // 4, rect.height() // 4, -rect.width() // 4, -rect.height() // 4)
        painter.setBrush(theme.stick_inner)
        painter.drawEllipse(inner)
        painter.setPen(theme.glyph_fg)
        font = QFont("Segoe UI", max(6, rect.height() // 4), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, button[:2])
        return

    if button.startswith("DPAD"):
        painter.drawRoundedRect(rect, 6, 6)
        cx, cy = rect.center().x(), rect.center().y()
        painter.setPen(QPen(theme.glyph_fg, max(2, rect.width() // 10), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if button.endswith("UP"):
            painter.drawLine(cx, cy + rect.height() // 6, cx, cy - rect.height() // 4)
        elif button.endswith("DOWN"):
            painter.drawLine(cx, cy - rect.height() // 6, cx, cy + rect.height() // 4)
        elif button.endswith("LEFT"):
            painter.drawLine(cx + rect.width() // 6, cy, cx - rect.width() // 4, cy)
        else:
            painter.drawLine(cx - rect.width() // 6, cy, cx + rect.width() // 4, cy)
        return

    if button in ("VIEW", "MENU"):
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(theme.glyph_fg)
        font = QFont("Segoe UI", max(6, rect.height() // 4), QFont.Weight.Bold)
        painter.setFont(font)
        label = "⧉" if button == "VIEW" else "☰"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        return

    painter.drawRoundedRect(rect, 8, 8)
    painter.setPen(theme.glyph_fg)
    font = QFont("Segoe UI", max(6, rect.height() // 3), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, button[:3])


def _draw_badge(painter: QPainter, text: str, bounds: QRect) -> None:
    badge_w = max(14, bounds.width() // 2)
    badge_h = max(12, bounds.height() // 3)
    rect = QRect(bounds.right() - badge_w + 1, bounds.top() - 1, badge_w, badge_h)
    painter.setBrush(QColor("#3D8BFD"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(rect, 4, 4)
    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Segoe UI", max(6, badge_h // 2), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text[:3])


def app_icon_pixmap(size: int = 64) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor("#F8FAFC"))
    painter.setPen(QPen(QColor("#2563EB"), 2))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 14, 14)
    painter.setBrush(QColor("#E5EAF1"))
    painter.setPen(Qt.PenStyle.NoPen)
    body = QRectF(size * 0.16, size * 0.32, size * 0.68, size * 0.38)
    painter.drawRoundedRect(body, 12, 12)
    painter.setBrush(QColor("#2ECC71"))
    painter.drawEllipse(QPoint(int(size * 0.32), int(size * 0.52)), size // 12, size // 12)
    painter.setBrush(QColor("#E74C3C"))
    painter.drawEllipse(QPoint(int(size * 0.70), int(size * 0.46)), size // 14, size // 14)
    painter.setBrush(QColor("#3498DB"))
    painter.drawEllipse(QPoint(int(size * 0.62), int(size * 0.58)), size // 16, size // 16)
    painter.end()
    return pixmap
