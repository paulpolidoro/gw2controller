from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from macrocontroller.controller.xinput import PadState
from macrocontroller.overlay.glyphs import FACE_COLORS


class GamepadView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pad = PadState()
        self._layer = "default"
        self.setFixedSize(392, 236)

    def sizeHint(self) -> QSize:
        return QSize(392, 236)

    def set_pad(self, pad: PadState) -> None:
        self._pad = pad
        self.update()

    def set_layer(self, layer: str) -> None:
        self._layer = layer
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#F4F6F8"))
        w, h = self.width(), self.height()
        body = QRectF(18, h * 0.22, w - 36, h * 0.58)
        painter.setBrush(QColor("#E5EAF1"))
        painter.setPen(QPen(QColor("#C5CEDA"), 2))
        path = QPainterPath()
        path.addRoundedRect(body, 36, 36)
        painter.drawPath(path)

        self._dpad(painter, QPoint(int(w * 0.22), int(h * 0.42)))
        self._stick(painter, QPoint(int(w * 0.38), int(h * 0.70)), "LS", self._pad.lx, self._pad.ly)
        self._face(painter, QPoint(int(w * 0.78), int(h * 0.42)))
        self._stick(painter, QPoint(int(w * 0.62), int(h * 0.70)), "RS", self._pad.rx, self._pad.ry)
        self._shoulder(painter, QRect(int(w * 0.12), int(h * 0.11), 68, 22), "LB")
        self._shoulder(painter, QRect(int(w * 0.70), int(h * 0.11), 68, 22), "RB")
        self._trigger(painter, QRect(int(w * 0.12), int(h * 0.02), 68, 18), "LT", self._pad.lt)
        self._trigger(painter, QRect(int(w * 0.70), int(h * 0.02), 68, 18), "RT", self._pad.rt)
        self._small(painter, QPoint(int(w * 0.44), int(h * 0.40)), "VIEW")
        self._small(painter, QPoint(int(w * 0.56), int(h * 0.40)), "MENU")

        painter.setPen(QColor("#4B5563"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        status = "Conectado" if self._pad.connected else "Sem controle"
        painter.drawText(self.rect().adjusted(10, h - 22, -10, -4), Qt.AlignmentFlag.AlignLeft, status)
        painter.drawText(self.rect().adjusted(10, h - 22, -10, -4), Qt.AlignmentFlag.AlignRight, str(self._layer))
        painter.end()

    def _down(self, name: str) -> bool:
        return bool(self._pad.buttons.get(name))

    def _stick(self, painter: QPainter, center: QPoint, name: str, x: float, y: float) -> None:
        r = 18
        color = QColor("#2563EB") if self._down(name) else QColor("#D5DCE6")
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#9CA3AF"), 1))
        painter.drawEllipse(center, r, r)
        knob = QPoint(center.x() + int(x * 8), center.y() - int(y * 8))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(knob, 6, 6)

    def _dpad(self, painter: QPainter, center: QPoint) -> None:
        mapping = {
            "DPAD_UP": QRect(center.x() - 6, center.y() - 22, 12, 16),
            "DPAD_DOWN": QRect(center.x() - 6, center.y() + 6, 12, 16),
            "DPAD_LEFT": QRect(center.x() - 22, center.y() - 6, 16, 12),
            "DPAD_RIGHT": QRect(center.x() + 6, center.y() - 6, 16, 12),
        }
        for name, rect in mapping.items():
            painter.setBrush(QColor("#2563EB") if self._down(name) else QColor("#D5DCE6"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 3, 3)

    def _face(self, painter: QPainter, center: QPoint) -> None:
        positions = {
            "Y": QPoint(center.x(), center.y() - 18),
            "A": QPoint(center.x(), center.y() + 18),
            "X": QPoint(center.x() - 18, center.y()),
            "B": QPoint(center.x() + 18, center.y()),
        }
        for name, point in positions.items():
            color = QColor(FACE_COLORS[name])
            if not self._down(name):
                color = color.lighter(135)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(point, 8, 8)

    def _shoulder(self, painter: QPainter, rect: QRect, name: str) -> None:
        painter.setBrush(QColor("#2563EB") if self._down(name) else QColor("#D5DCE6"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor("#111827") if not self._down(name) else QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)

    def _trigger(self, painter: QPainter, rect: QRect, name: str, value: float) -> None:
        painter.setBrush(QColor("#EEF2F7"))
        painter.setPen(QPen(QColor("#C5CEDA"), 1))
        painter.drawRoundedRect(rect, 4, 4)
        fill = QRect(rect)
        fill.setWidth(max(2, int(rect.width() * value)))
        painter.setBrush(QColor("#2563EB") if self._down(name) else QColor("#BFDBFE"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(fill, 4, 4)
        painter.setPen(QColor("#111827"))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)

    def _small(self, painter: QPainter, center: QPoint, name: str) -> None:
        painter.setBrush(QColor("#2563EB") if self._down(name) else QColor("#D5DCE6"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 6, 6)
