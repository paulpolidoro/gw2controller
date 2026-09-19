from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from gw2controller.mapping.engine import PressedFrame
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

CELL_W = 72
CELL_H = 40
CELL_GAP = 6
PAD = 8


class CurrentButtonsOverlay(QWidget):
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
        self._frames: list[PressedFrame] = [PressedFrame("-")]
        self._theme: OverlayTheme = overlay_theme("dark")
        self._enabled = False
        self._movable = False
        self._pos_x = 40
        self._pos_y = 40
        self._screen_index = -1
        self._dragging = False
        self._drag_offset = QPoint()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._resize_to_frames()
        self.hide()

    def set_config(
        self,
        *,
        enabled: bool,
        movable: bool,
        x: int,
        y: int,
        screen_index: int,
        theme: str | OverlayTheme = "dark",
    ) -> None:
        self._enabled = enabled
        self._movable = movable
        self._pos_x = int(x)
        self._pos_y = int(y)
        self._screen_index = int(screen_index)
        self._theme = theme if isinstance(theme, OverlayTheme) else overlay_theme(theme)
        self.setCursor(Qt.CursorShape.SizeAllCursor if movable else Qt.CursorShape.ArrowCursor)
        if not enabled:
            self.hide()
            return
        self._place()
        self.show()
        self._apply_click_through(not movable)
        self.update()

    def set_frames(self, frames: list[PressedFrame]) -> None:
        self._frames = frames or [PressedFrame("-")]
        self._resize_to_frames()
        if self._enabled:
            self._place()
            self.show()
            self._apply_click_through(not self._movable)
        self.update()

    def _resize_to_frames(self) -> None:
        count = max(1, len(self._frames))
        width = PAD * 2 + count * CELL_W + (count - 1) * CELL_GAP
        height = PAD * 2 + CELL_H
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        theme = self._theme
        idle = QColor(theme.glyph_bg)
        fill = QColor(theme.radial_slice_selected)
        border = QColor(theme.glyph_border)
        text = QColor(theme.glyph_fg)
        for index, frame in enumerate(self._frames):
            x = PAD + index * (CELL_W + CELL_GAP)
            y = PAD
            rect = QRect(x, y, CELL_W, CELL_H)
            painter.setBrush(idle)
            painter.setPen(QPen(border, 1))
            painter.drawRoundedRect(rect, 8, 8)
            if frame.label != "-" and frame.progress > 0:
                fill_h = max(2, int(CELL_H * frame.progress))
                fill_rect = QRect(x, y + CELL_H - fill_h, CELL_W, fill_h)
                color = QColor(fill)
                if frame.long_pending and frame.progress < 1.0:
                    color.setAlpha(160)
                else:
                    color.setAlpha(210)
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(fill_rect.adjusted(1, 1, -1, -1), 6, 6)
            painter.setPen(text)
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, frame.label)
        if self._movable:
            painter.setPen(QPen(theme.edit_border, 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
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
