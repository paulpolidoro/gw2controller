from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QWheelEvent
from PySide6.QtWidgets import QWidget

from gw2controller.overlay.glyphs import glyph_pixmap
from gw2controller.overlay.theme import OverlayTheme, overlay_theme

MIN_SIZE = 28
MAX_SIZE = 96


class OverlaySlotWidget(QWidget):
    moved = Signal()
    resized = Signal()
    remove_requested = Signal()

    def __init__(self, button: str, size: int = 44, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.button = button
        self.slot_size = size
        self.edit_mode = False
        self.layer_badge: str | None = None
        self.caption = ""
        self.theme: OverlayTheme = overlay_theme("dark")
        self._drag_offset = QPoint()
        self._dragging = False
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._apply_size()

    def set_edit_mode(self, enabled: bool) -> None:
        if not enabled and self._dragging:
            self._dragging = False
            if QWidget.mouseGrabber() is self:
                self.releaseMouse()
        self.edit_mode = enabled
        self.setCursor(Qt.CursorShape.SizeAllCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.update()

    def set_layer_badge(self, badge: str | None) -> None:
        if badge != self.layer_badge:
            self.layer_badge = badge
            self.update()

    def set_theme(self, theme: OverlayTheme | str) -> None:
        resolved = theme if isinstance(theme, OverlayTheme) else overlay_theme(theme)
        if resolved.name != self.theme.name:
            self.theme = resolved
            self.update()

    def set_caption(self, caption: str) -> None:
        if caption != self.caption:
            self.caption = caption
            self.update()

    def set_slot_size(self, size: int) -> None:
        clamped = max(MIN_SIZE, min(MAX_SIZE, int(size)))
        if clamped != self.slot_size:
            self.slot_size = clamped
            self._apply_size()
            self.resized.emit()

    def _apply_size(self) -> None:
        self.setFixedSize(self.slot_size, self.slot_size + 16)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self.edit_mode:
            painter.setPen(QPen(self.theme.edit_border, 1, Qt.PenStyle.DashLine))
            painter.setBrush(self.theme.edit_fill)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        pixmap = glyph_pixmap(self.button, self.slot_size, self.layer_badge, theme=self.theme)
        painter.drawPixmap(0, 0, pixmap)
        if self.caption:
            text_rect = self.rect().adjusted(2, self.slot_size - 2, -2, -1)
            painter.setBrush(self.theme.caption_bg)
            painter.setPen(QPen(self.theme.caption_border, 1))
            painter.drawRoundedRect(text_rect, 4, 4)
            painter.setPen(self.theme.caption_fg)
            font = QFont("Segoe UI", max(7, self.slot_size // 5), QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.caption)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.edit_mode:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.position().toPoint()
            self.grabMouse()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            self.remove_requested.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.edit_mode or not self._dragging:
            return
        parent = self.parentWidget()
        if parent is None:
            return
        cursor = event.globalPosition().toPoint()
        local = parent.mapFromGlobal(cursor) - self._drag_offset
        max_x = max(0, parent.width() - self.width())
        max_y = max(0, parent.height() - self.height())
        local.setX(max(0, min(max_x, local.x())))
        local.setY(max(0, min(max_y, local.y())))
        if local != self.pos():
            self.move(local)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: ARG002
        if not self._dragging:
            return
        self._dragging = False
        if QWidget.mouseGrabber() is self:
            self.releaseMouse()
        self.setCursor(Qt.CursorShape.SizeAllCursor if self.edit_mode else Qt.CursorShape.ArrowCursor)
        self.moved.emit()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.edit_mode:
            return
        delta = 2 if event.angleDelta().y() > 0 else -2
        self.set_slot_size(self.slot_size + delta)
