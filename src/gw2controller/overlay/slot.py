from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPainter, QPaintEvent, QPen, QWheelEvent
from PySide6.QtWidgets import QWidget

from gw2controller.overlay.theme import OverlayTheme, overlay_theme

MIN_SIZE = 20
MAX_SIZE = 96

OVERLAY_LABELS: dict[str, str] = {
    "A": "A",
    "B": "B",
    "X": "X",
    "Y": "Y",
    "LB": "LB",
    "RB": "RB",
    "LT": "LT",
    "RT": "RT",
    "LS": "LS",
    "RS": "RS",
    "DPAD_UP": "↑",
    "DPAD_DOWN": "↓",
    "DPAD_LEFT": "←",
    "DPAD_RIGHT": "→",
    "VIEW": "View",
    "MENU": "Menu",
}


def overlay_button_label(button: str) -> str:
    return OVERLAY_LABELS.get(button, button)


class OverlaySlotWidget(QWidget):
    moved = Signal()
    resized = Signal()
    remove_requested = Signal()

    def __init__(self, button: str, size: int = 44, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.button = button
        self.slot_size = size
        self.edit_mode = False
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

    def set_theme(self, theme: OverlayTheme | str) -> None:
        resolved = theme if isinstance(theme, OverlayTheme) else overlay_theme(theme)
        if resolved.name != self.theme.name:
            self.theme = resolved
            self.update()

    def set_slot_size(self, size: int) -> None:
        clamped = max(MIN_SIZE, min(MAX_SIZE, int(size)))
        if clamped != self.slot_size:
            self.slot_size = clamped
            self._apply_size()
            self.resized.emit()

    def _apply_size(self) -> None:
        label = overlay_button_label(self.button)
        # Largura mínima maior para textos como View/Menu não ficarem cortados.
        width = max(self.slot_size + 8, 12 + len(label) * max(7, self.slot_size // 3))
        self.setFixedSize(width, self.slot_size + 4)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        label = overlay_button_label(self.button)
        box = self.rect().adjusted(1, 1, -1, -1)

        if self.edit_mode:
            painter.setPen(QPen(self.theme.edit_border, 1, Qt.PenStyle.DashLine))
            painter.setBrush(self.theme.edit_fill)
            painter.drawRoundedRect(box, 8, 8)

        painter.setBrush(self.theme.glyph_bg)
        painter.setPen(QPen(self.theme.glyph_border, 1))
        painter.drawRoundedRect(box, 8, 8)

        painter.setPen(self.theme.glyph_fg)
        font_size = max(9, int(self.slot_size * 0.42))
        if len(label) > 2:
            font_size = max(8, int(self.slot_size * 0.32))
        painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, label)
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
