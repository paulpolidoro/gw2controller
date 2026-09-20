from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from gw2controller.mapping.models import NotesRow
from gw2controller.overlay.theme import OverlayTheme, overlay_theme
from gw2controller.overlay.window import (
    HWND_TOPMOST,
    SWP_NOACTIVATE,
    SWP_NOMOVE,
    SWP_NOSIZE,
    SWP_SHOWWINDOW,
    _set_click_through,
    resolve_screen,
    user32,
)

PAD = 10
ROW_H = 22
HEAD_H = 24
TITLE_MIN = 72
VALUE_MIN = 56


class NotesOverlay(QWidget):
    """Tabelinha compacta de lembretes (título / valor), arrastável."""

    moved = Signal(int, int)

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._enabled = False
        self._movable = False
        self._pos_x = 40
        self._pos_y = 120
        self._screen_index = -1
        self._heading = ""
        self._rows: list[NotesRow] = []
        self._theme: OverlayTheme = overlay_theme("dark")
        self._alpha = 0.88
        self._title_w = TITLE_MIN
        self._value_w = VALUE_MIN
        self._dragging = False
        self._drag_offset = QPoint()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.hide()

    def set_config(
        self,
        *,
        enabled: bool,
        movable: bool,
        x: int,
        y: int,
        screen_index: int,
        heading: str,
        rows: list[NotesRow],
        theme: str | OverlayTheme = "dark",
        alpha: int = 88,
    ) -> None:
        self._enabled = enabled
        self._movable = movable
        self._pos_x = int(x)
        self._pos_y = int(y)
        self._screen_index = int(screen_index)
        self._heading = (heading or "").strip()
        self._rows = [row for row in rows if row.is_active()]
        self._theme = theme if isinstance(theme, OverlayTheme) else overlay_theme(theme)
        self._alpha = max(10, min(100, int(alpha))) / 100.0
        self.setCursor(Qt.CursorShape.SizeAllCursor if movable else Qt.CursorShape.ArrowCursor)
        if not enabled or not self._rows:
            self.hide()
            return
        self._resize_to_content()
        self._place()
        self.show()
        self._apply_click_through(not movable)
        self.update()

    def _resize_to_content(self) -> None:
        title_font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        value_font = QFont("Segoe UI", 9)
        head_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        tm = QFontMetrics(title_font)
        vm = QFontMetrics(value_font)
        hm = QFontMetrics(head_font)
        title_w = TITLE_MIN
        value_w = VALUE_MIN
        for row in self._rows:
            title_w = max(title_w, tm.horizontalAdvance(row.title.strip() or "—") + 4)
            value_w = max(value_w, vm.horizontalAdvance(row.value.strip() or "—") + 4)
        title_w = min(160, title_w)
        value_w = min(140, value_w)
        if self._heading:
            title_w = max(title_w, hm.horizontalAdvance(self._heading) - value_w)
        self._title_w = title_w
        self._value_w = value_w
        width = PAD * 2 + title_w + 10 + value_w
        height = PAD * 2 + len(self._rows) * ROW_H
        if self._heading:
            height += HEAD_H
        self.setFixedSize(width, height)

    def _place(self) -> None:
        screen = resolve_screen(self._screen_index)
        geo = screen.geometry()
        x = geo.x() + max(0, min(self._pos_x, geo.width() - self.width()))
        y = geo.y() + max(0, min(self._pos_y, geo.height() - self.height()))
        self.move(x, y)
        hwnd = int(self.winId())
        if hwnd:
            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )

    def _apply_click_through(self, enabled: bool) -> None:
        hwnd = int(self.winId())
        if hwnd:
            _set_click_through(hwnd, enabled)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        if not self._rows:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setOpacity(self._alpha)
        theme = self._theme
        box = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(theme.caption_bg)
        painter.setPen(QPen(theme.glyph_border, 1))
        painter.drawRoundedRect(box, 8, 8)

        y = PAD
        if self._heading:
            painter.setPen(theme.caption_fg)
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                PAD,
                y,
                self.width() - PAD * 2,
                HEAD_H - 4,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self._heading,
            )
            y += HEAD_H

        for row in self._rows:
            painter.setPen(theme.caption_fg)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(
                QRect(PAD, y, self._title_w, ROW_H),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                row.title.strip() or "—",
            )
            painter.setPen(theme.radial_center_text)
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(
                QRect(PAD + self._title_w + 10, y, self._value_w, ROW_H),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                row.value.strip() or "—",
            )
            y += ROW_H

        if self._movable:
            painter.setOpacity(1.0)
            painter.setPen(QPen(theme.edit_border, 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(box, 8, 8)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._movable or event.button() != Qt.MouseButton.LeftButton:
            return
        self._dragging = True
        self._drag_offset = event.position().toPoint()
        self.grabMouse()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._dragging:
            return
        screen = resolve_screen(self._screen_index)
        geo = screen.geometry()
        global_pos = event.globalPosition().toPoint() - self._drag_offset
        x = max(geo.x(), min(geo.x() + geo.width() - self.width(), global_pos.x()))
        y = max(geo.y(), min(geo.y() + geo.height() - self.height(), global_pos.y()))
        self.move(x, y)
        self._pos_x = x - geo.x()
        self._pos_y = y - geo.y()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: ARG002
        if not self._dragging:
            return
        self._dragging = False
        if QWidget.mouseGrabber() is self:
            self.releaseMouse()
        self.moved.emit(self._pos_x, self._pos_y)
