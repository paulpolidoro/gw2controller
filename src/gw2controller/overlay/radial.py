from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from gw2controller.mapping.engine import RadialView
from gw2controller.overlay.theme import OverlayTheme, overlay_theme
from gw2controller.overlay.window import (
    SWP_NOACTIVATE,
    SWP_NOMOVE,
    SWP_NOSIZE,
    SWP_SHOWWINDOW,
    HWND_TOPMOST,
    _set_click_through,
    resolve_screen,
    user32,
)


class RadialOverlay(QWidget):
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
        self.setFixedSize(340, 340)
        self._view = RadialView()
        self._theme: OverlayTheme = overlay_theme("dark")
        self._alpha = 0.9
        self.hide()

    def set_view(
        self,
        view: RadialView,
        screen_index: int,
        theme: str | OverlayTheme = "dark",
        alpha: int = 90,
    ) -> None:
        self._view = view
        self._theme = theme if isinstance(theme, OverlayTheme) else overlay_theme(theme)
        self._alpha = max(10, min(100, int(alpha))) / 100.0
        if not view.active or not view.items:
            self.hide()
            return
        screen = resolve_screen(screen_index)
        geo = screen.geometry()
        self.move(geo.center().x() - self.width() // 2, geo.center().y() - self.height() // 2)
        self.show()
        hwnd = int(self.winId())
        if hwnd:
            _set_click_through(hwnd, True)
            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        if not self._view.active or not self._view.items:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setOpacity(self._alpha)
        theme = self._theme
        count = len(self._view.items)
        rect = QRectF(20, 20, 300, 300)
        slice_span = 360.0 / count
        start = 90.0 + slice_span / 2
        for index, (label, keys) in enumerate(self._view.items):
            selected = self._view.selected == index
            painter.setBrush(theme.radial_slice_selected if selected else theme.radial_slice)
            painter.setPen(QPen(theme.radial_ring, 1))
            painter.drawPie(rect, int((start - (index + 1) * slice_span) * 16), int(slice_span * 16))
            angle = (start - slice_span * (index + 0.5)) % 360
            from math import cos, radians, sin

            rad = radians(angle)
            cx = rect.center().x() + cos(rad) * 92
            cy = rect.center().y() - sin(rad) * 92
            painter.setPen(theme.radial_text_selected if selected else theme.radial_text)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            text = label if label else keys
            painter.drawText(int(cx - 48), int(cy - 12), 96, 24, Qt.AlignmentFlag.AlignCenter, text)
        painter.setBrush(theme.radial_center)
        painter.setPen(QPen(theme.radial_ring, 2))
        painter.drawEllipse(rect.center(), 36, 36)
        painter.setPen(theme.radial_center_text)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "RS")
        painter.end()
