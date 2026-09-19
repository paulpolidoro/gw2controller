from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QGuiApplication, QPainter, QPaintEvent, QScreen
from PySide6.QtWidgets import QLabel, QWidget

from gw2controller.mapping.models import DEFAULT_LAYOUT_KEY, OverlaySlot, Profile
from gw2controller.overlay.slot import OverlaySlotWidget
from gw2controller.overlay.theme import overlay_theme

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.WinDLL("user32", use_last_error=True)
if ctypes.sizeof(ctypes.c_void_p) == 8:
    GetWindowLong = user32.GetWindowLongPtrW
    SetWindowLong = user32.SetWindowLongPtrW
    GetWindowLong.restype = ctypes.c_longlong
    SetWindowLong.restype = ctypes.c_longlong
    GetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int]
    SetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
else:
    GetWindowLong = user32.GetWindowLongW
    SetWindowLong = user32.SetWindowLongW

user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL


def _set_click_through(hwnd: int, enabled: bool) -> None:
    style = GetWindowLong(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    if enabled:
        style |= WS_EX_TRANSPARENT
    else:
        style &= ~WS_EX_TRANSPARENT
    SetWindowLong(hwnd, GWL_EXSTYLE, style)


def screen_choices() -> list[tuple[int, str]]:
    screens = QGuiApplication.screens()
    primary = QGuiApplication.primaryScreen()
    items: list[tuple[int, str]] = [(-1, f"Tela principal ({_screen_label(primary)})")]
    for index, screen in enumerate(screens):
        mark = " - principal" if screen is primary else ""
        items.append((index, f"Tela {index + 1} ({_screen_label(screen)}){mark}"))
    return items


def _screen_label(screen: QScreen | None) -> str:
    if screen is None:
        return "—"
    geo = screen.geometry()
    return f"{geo.width()}x{geo.height()}"


def resolve_screen(screen_index: int) -> QScreen:
    screens = QGuiApplication.screens()
    if 0 <= screen_index < len(screens):
        return screens[screen_index]
    return QGuiApplication.primaryScreen() or screens[0]


class OverlayWindow(QWidget):
    slots_changed = Signal()

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowTitle("GW2Controller Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self._edit_mode = False
        self._layout_key = DEFAULT_LAYOUT_KEY
        self._layout_dirty = False
        self._profile: Profile | None = None
        self._slots: list[OverlaySlotWidget] = []
        self._banner = QLabel("", self)
        self._banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_theme_styles()
        self._banner.hide()
        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(self._on_screens_changed)
            app.screenRemoved.connect(self._on_screens_changed)
            app.primaryScreenChanged.connect(self._on_screens_changed)

    def _target_screen(self) -> QScreen:
        index = -1 if self._profile is None else self._profile.overlay.screen_index
        return resolve_screen(index)

    def _cover_selected_screen(self) -> None:
        screen = self._target_screen()
        geo = screen.geometry()
        self.setScreen(screen)
        self.setGeometry(geo)
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
        self._apply_click_through(not self._edit_mode)
        self._clamp_slots()
        self._place_banner()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._cover_selected_screen()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: ARG002
        if not self._edit_mode:
            return
        painter = QPainter(self)
        theme = overlay_theme(self._profile.overlay.theme if self._profile else "dark")
        painter.fillRect(self.rect(), theme.veil)
        painter.setPen(theme.edit_border)
        font = QFont("Segoe UI", 10)
        painter.setFont(font)
        painter.end()

    def set_profile(self, profile: Profile) -> None:
        self._profile = profile
        self._apply_theme_styles()
        self._rebuild_slots()
        if profile.overlay.visible or self._edit_mode:
            self.show()
            self._cover_selected_screen()
        else:
            self.hide()
        self._apply_click_through(not self._edit_mode)

    def set_runtime(self, badge: str, layout_key: str = DEFAULT_LAYOUT_KEY) -> None:
        if self._edit_mode:
            return
        self.set_layout_key(layout_key or DEFAULT_LAYOUT_KEY)

    def set_layout_key(self, key: str) -> None:
        name = (key or DEFAULT_LAYOUT_KEY).strip() or DEFAULT_LAYOUT_KEY
        if name == self._layout_key:
            return
        if self._layout_dirty:
            self.sync_slots_to_profile()
            self._layout_dirty = False
        self._layout_key = name
        # Em edição, se o layout do modificador ainda não existe, copia o padrão para posicionar.
        if self._edit_mode and self._profile is not None and name != DEFAULT_LAYOUT_KEY:
            self._profile.overlay.ensure_layout(name)
        self._rebuild_slots()
        self._place_banner()

    def current_layout_key(self) -> str:
        return self._layout_key

    def set_edit_mode(self, enabled: bool) -> None:
        if self._edit_mode and not enabled and self._layout_dirty:
            self.sync_slots_to_profile()
            self._layout_dirty = False
        self._edit_mode = enabled
        if enabled and self._profile is not None:
            self._profile.overlay.visible = True
            if self._layout_key != DEFAULT_LAYOUT_KEY:
                self._profile.overlay.ensure_layout(self._layout_key)
            self.show()
            self._rebuild_slots()
        for widget in self._slots:
            widget.set_edit_mode(enabled)
        self._banner.setVisible(enabled)
        self._place_banner()
        if self._profile is None or self._profile.overlay.visible or enabled:
            self.show()
        self._cover_selected_screen()
        self._apply_click_through(not enabled)
        self.update()

    def set_overlay_visible(self, visible: bool) -> None:
        if self._profile is not None:
            self._profile.overlay.visible = visible
        if visible or self._edit_mode:
            self.show()
            self._cover_selected_screen()
        else:
            self.hide()

    def is_edit_mode(self) -> bool:
        return self._edit_mode

    def add_slot(self, button: str) -> None:
        if self._profile is None:
            return
        self.show()
        self._cover_selected_screen()
        size = self._profile.overlay.item_size
        slots = list(self._profile.overlay.slots_for(self._layout_key))
        slot = OverlaySlot(
            button=button,
            x=max(20, (self.width() - size) // 2),
            y=max(20, self.height() - 140),
            size=size,
            id=f"slot{len(slots) + 1}",
        )
        slots.append(slot)
        self._profile.overlay.set_slots_for(self._layout_key, slots)
        self._layout_dirty = False
        self._rebuild_slots()
        self.slots_changed.emit()

    def sync_slots_to_profile(self) -> None:
        if self._profile is None:
            return
        updated: list[OverlaySlot] = []
        item_size = self._profile.overlay.item_size
        for widget in self._slots:
            updated.append(
                OverlaySlot(
                    button=widget.button,
                    x=widget.x(),
                    y=widget.y(),
                    size=item_size,
                    id="",
                )
            )
        self._profile.overlay.set_slots_for(self._layout_key, updated)

    def _rebuild_slots(self) -> None:
        for widget in self._slots:
            widget.deleteLater()
        self._slots.clear()
        if self._profile is None:
            return
        size = self._profile.overlay.item_size
        for slot in self._profile.overlay.slots_for(self._layout_key):
            widget = OverlaySlotWidget(slot.button, size, self)
            widget.move(slot.x, slot.y)
            widget.set_theme(self._overlay_theme())
            widget.set_edit_mode(self._edit_mode)
            widget.moved.connect(self._on_slots_mutated)
            widget.resized.connect(lambda w=widget: self._on_slot_resized(w))
            widget.remove_requested.connect(lambda w=widget: self._remove_slot(w))
            widget.show()
            self._slots.append(widget)
        self._clamp_slots()

    def _on_slot_resized(self, widget: OverlaySlotWidget) -> None:
        size = widget.slot_size
        if self._profile is not None:
            self._profile.overlay.item_size = size
        for other in self._slots:
            if other is widget:
                continue
            if other.slot_size != size:
                other.slot_size = size
                other._apply_size()
        self._on_slots_mutated()

    def _clamp_slots(self) -> None:
        for widget in self._slots:
            max_x = max(0, self.width() - widget.width())
            max_y = max(0, self.height() - widget.height())
            x = min(max(0, widget.x()), max_x)
            y = min(max(0, widget.y()), max_y)
            if widget.pos().x() != x or widget.pos().y() != y:
                widget.move(x, y)

    def _remove_slot(self, widget: OverlaySlotWidget) -> None:
        if widget in self._slots:
            self._slots.remove(widget)
            widget.deleteLater()
            self._on_slots_mutated()

    def _on_slots_mutated(self) -> None:
        self._layout_dirty = True
        self.sync_slots_to_profile()
        self._layout_dirty = False
        self.slots_changed.emit()

    def _overlay_theme(self):
        name = self._profile.overlay.theme if self._profile else "dark"
        return overlay_theme(name)

    def _apply_theme_styles(self) -> None:
        self._banner.setStyleSheet(self._overlay_theme().banner_qss)

    def _apply_click_through(self, enabled: bool) -> None:
        hwnd = int(self.winId())
        if hwnd:
            _set_click_through(hwnd, enabled)

    def _place_banner(self) -> None:
        screen = self._target_screen()
        layout = "Padrão" if self._layout_key == DEFAULT_LAYOUT_KEY else self._layout_key
        self._banner.setText(
            f"Edição [{layout}] — arraste nesta tela ({_screen_label(screen)}) "
            "• scroll no tamanho • botão direito remove • F8 sai"
        )
        self._banner.adjustSize()
        self._banner.move(max(20, (self.width() - self._banner.width()) // 2), 24)

    def _on_screens_changed(self, *args) -> None:  # noqa: ARG002
        if self.isVisible():
            self._cover_selected_screen()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._banner.isVisible():
            self._place_banner()
