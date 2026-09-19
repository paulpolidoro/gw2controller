from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from gw2controller.overlay.glyphs import app_icon_pixmap


class TrayIcon(QSystemTrayIcon):
    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        icon = QIcon(app_icon_pixmap(64))
        self.setIcon(icon)
        self.setToolTip("GW2Controller")
        menu = QMenu()
        show_action = QAction("Abrir configuração", menu)
        show_action.triggered.connect(window.showNormal)
        show_action.triggered.connect(window.raise_)
        edit_action = QAction("Posicionar ícones (F8)", menu)
        hide_overlay_action = QAction("Mostrar/ocultar sobreposição (F9)", menu)
        quit_action = QAction("Sair", menu)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(edit_action)
        menu.addAction(hide_overlay_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.show_action = show_action
        self.edit_action = edit_action
        self.hide_overlay_action = hide_overlay_action
        self.quit_action = quit_action
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            window = self.parent()
            if isinstance(window, QWidget):
                window.showNormal()
                window.raise_()
                window.activateWindow()
