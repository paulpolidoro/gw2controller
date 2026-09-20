from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from gw2controller.mapping.engine import PanelView
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

ROW_H = 34
PAD_W = 56
KEYS_W = 110
NAME_W = 160
MARGIN = 16
TITLE_H = 36
FOOTER_H = 28


class PanelOverlay(QWidget):
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
        self._view = PanelView()
        self._theme: OverlayTheme = overlay_theme("dark")
        self._alpha = 0.92
        self.hide()

    def set_view(
        self,
        view: PanelView,
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
        width = MARGIN * 2 + PAD_W + NAME_W + KEYS_W + 24
        height = MARGIN * 2 + TITLE_H + len(view.items) * ROW_H + FOOTER_H
        self.setFixedSize(width, height)
        screen = resolve_screen(screen_index)
        geo = screen.geometry()
        self.move(geo.center().x() - width // 2, geo.center().y() - height // 2)
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
        box = self.rect().adjusted(4, 4, -4, -4)
        painter.setBrush(theme.caption_bg)
        painter.setPen(QPen(theme.radial_ring, 2))
        painter.drawRoundedRect(box, 12, 12)

        painter.setPen(theme.caption_fg)
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.drawText(
            MARGIN,
            MARGIN,
            self.width() - MARGIN * 2,
            TITLE_H,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._view.title,
        )

        y = MARGIN + TITLE_H
        for pad_label, name, keys in self._view.items:
            selected = self._view.pressed == pad_label
            row = box.adjusted(8, 0, -8, 0)
            row.setTop(y)
            row.setHeight(ROW_H - 4)
            painter.setBrush(theme.radial_slice_selected if selected else theme.radial_slice)
            painter.setPen(QPen(theme.glyph_border, 1))
            painter.drawRoundedRect(row, 8, 8)

            painter.setPen(theme.radial_text_selected if selected else theme.radial_text)
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(
                row.left() + 8,
                row.top(),
                PAD_W,
                row.height(),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                pad_label,
            )
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            painter.drawText(
                row.left() + 8 + PAD_W,
                row.top(),
                NAME_W,
                row.height(),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                name,
            )
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(theme.radial_center_text if not selected else theme.radial_text_selected)
            painter.drawText(
                row.right() - KEYS_W - 8,
                row.top(),
                KEYS_W,
                row.height(),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                keys,
            )
            y += ROW_H

        painter.setPen(theme.radial_center_text)
        painter.setFont(QFont("Segoe UI", 8))
        hint = f"Aperte {self._view.owner} de novo para fechar"
        painter.drawText(
            MARGIN,
            self.height() - MARGIN - FOOTER_H + 4,
            self.width() - MARGIN * 2,
            FOOTER_H,
            Qt.AlignmentFlag.AlignCenter,
            hint,
        )
        painter.end()
