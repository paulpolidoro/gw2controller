from __future__ import annotations

import sys
import time

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from gw2controller.controller.xinput import XInputReader
from gw2controller.gw2.mumble import MumbleLinkReader
from gw2controller.hotkeys import GlobalHotkeys, user32, vk_from_name
from gw2controller.mapping.engine import InputEvent, MappingEngine
from gw2controller.mapping.profiles import load_or_create_default, save_profile
from gw2controller.output.sendinput import InputSender
from gw2controller.overlay.current_buttons import CurrentButtonsOverlay
from gw2controller.overlay.glyphs import app_icon_pixmap
from gw2controller.overlay.radial import RadialOverlay
from gw2controller.overlay.window import OverlayWindow
from gw2controller.ui.main_window import MainWindow
from gw2controller.ui.styles import APP_QSS
from gw2controller.ui.tray import TrayIcon

HOTKEY_EDIT = 1
HOTKEY_VISIBLE = 2
TICK_MS = 8


class GW2ControllerApp:
    def __init__(self) -> None:
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("GW2Controller")
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setStyleSheet(APP_QSS)
        self.app.setWindowIcon(QIcon(app_icon_pixmap(32)))

        self.profile, self.profile_path = load_or_create_default()
        self.reader = XInputReader(trigger_threshold=self.profile.trigger_threshold)
        self.mumble = MumbleLinkReader()
        self.engine = MappingEngine(self.profile)
        self.sender = InputSender()
        self.overlay = OverlayWindow()
        self.radial = RadialOverlay()
        self.current_buttons = CurrentButtonsOverlay()
        self.window = MainWindow(self.profile, self.profile_path)
        self.tray = TrayIcon(self.window)

        self._last_tick = time.perf_counter()
        self._last_layer = "default"
        self._hotkeys: GlobalHotkeys | None = None
        self._hotkey_ok = False
        self._hotkey_prev = {HOTKEY_EDIT: False, HOTKEY_VISIBLE: False}
        self._mouse_accum_x = 0.0
        self._mouse_accum_y = 0.0

        self.window.profile_changed.connect(self._on_profile_changed)
        self.window.profile_persisted.connect(self._sync_path)
        self.window.overlay_edit_toggled.connect(self.toggle_edit_mode)
        self.window.overlay_visibility_toggled.connect(self.toggle_overlay_visible)
        self.window.overlay_add_slot.connect(self.overlay.add_slot)
        self.window.overlay_layout_selected.connect(self.overlay.set_layout_key)
        self.overlay.slots_changed.connect(self._on_overlay_slots_changed)
        self.current_buttons.moved.connect(self._on_current_buttons_moved)
        self.tray.edit_action.triggered.connect(self.toggle_edit_mode)
        self.tray.hide_overlay_action.triggered.connect(self.toggle_overlay_visible)
        self.app.aboutToQuit.connect(self.shutdown)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.information(
                self.window,
                "Bandeja",
                "A bandeja do sistema não está disponível. Feche pela janela principal.",
            )

        self.overlay.set_profile(self.profile)
        self._apply_current_buttons_config()
        self.window.show()
        self.app.screenAdded.connect(self.window._refresh_screen_choices)
        self.app.screenRemoved.connect(self.window._refresh_screen_choices)

        QTimer.singleShot(0, self._setup_hotkeys)

        self._overlay_save_timer = QTimer()
        self._overlay_save_timer.setSingleShot(True)
        self._overlay_save_timer.setInterval(400)
        self._overlay_save_timer.timeout.connect(self._persist_profile)
        self._timer = QTimer()
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _setup_hotkeys(self) -> None:
        hwnd = int(self.window.winId())
        self._hotkeys = GlobalHotkeys(hwnd)
        QCoreApplication.instance().installNativeEventFilter(self._hotkeys.filter)
        self._hotkeys.hotkey_pressed.connect(self._on_hotkey)
        self._register_hotkeys()

    def _register_hotkeys(self) -> None:
        if self._hotkeys is None:
            return
        edit = self.profile.hotkeys.toggle_overlay_edit
        visible = self.profile.hotkeys.toggle_overlay_visible
        ok_edit = self._hotkeys.register(HOTKEY_EDIT, edit)
        ok_visible = self._hotkeys.register(HOTKEY_VISIBLE, visible)
        self._hotkey_ok = ok_edit and ok_visible

    def _on_hotkey(self, hotkey_id: int) -> None:
        if hotkey_id == HOTKEY_EDIT:
            self.toggle_edit_mode()
        elif hotkey_id == HOTKEY_VISIBLE:
            self.toggle_overlay_visible()

    def _on_profile_changed(self) -> None:
        self.profile = self.window.profile
        self.profile_path = self.window.profile_path
        events = self.engine.set_profile(self.profile)
        self._dispatch(events)
        self.reader.trigger_threshold = self.profile.trigger_threshold
        self.overlay.set_profile(self.profile)
        self._apply_current_buttons_config()
        self._register_hotkeys()

    def _apply_current_buttons_config(self) -> None:
        overlay = self.profile.overlay
        self.current_buttons.set_config(
            enabled=overlay.current_buttons_enabled,
            movable=overlay.current_buttons_movable,
            x=overlay.current_buttons_x,
            y=overlay.current_buttons_y,
            screen_index=overlay.screen_index,
            theme=overlay.theme,
        )

    def _on_current_buttons_moved(self, x: int, y: int) -> None:
        self.profile.overlay.current_buttons_x = int(x)
        self.profile.overlay.current_buttons_y = int(y)
        self._overlay_save_timer.start()

    def _sync_path(self) -> None:
        self.profile_path = self.window.profile_path
        self.profile = self.window.profile

    def _on_overlay_slots_changed(self) -> None:
        self.profile = self.window.profile
        self._overlay_save_timer.start()

    def _persist_profile(self) -> None:
        save_profile(self.profile, self.profile_path)

    def toggle_edit_mode(self) -> None:
        enabled = not self.overlay.is_edit_mode()
        self.overlay.set_edit_mode(enabled)
        if not enabled:
            self.overlay.sync_slots_to_profile()
            save_profile(self.profile, self.profile_path)
        self.window.statusBar().showMessage(
            "Posicionando ícones na tela" if enabled else "Pronto — cliques passam pela sobreposição",
            2500,
        )

    def toggle_overlay_visible(self) -> None:
        if self.overlay.is_edit_mode():
            self.overlay.set_edit_mode(False)
        visible = not self.profile.overlay.visible
        self.profile.overlay.visible = visible
        self.overlay.set_overlay_visible(visible)
        self.window.reload_from_profile()
        save_profile(self.profile, self.profile_path)

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = max(0.001, min(0.05, now - self._last_tick))
        self._last_tick = now
        mumble_state = self.mumble.read()
        blocked_events = self.engine.set_mumble(mumble_state)
        if blocked_events:
            self._dispatch(blocked_events)
            self.sender.release_all()
        pad = self.reader.read()
        result = self.engine.tick(pad, now, dt)
        if result.release_all:
            self.sender.release_all()
        self._dispatch(result.events)
        try:
            self._mouse_accum_x += result.mouse_dx
            self._mouse_accum_y += result.mouse_dy
            dx, dy = int(self._mouse_accum_x), int(self._mouse_accum_y)
            self._mouse_accum_x -= dx
            self._mouse_accum_y -= dy
            if dx or dy:
                self.sender.mouse_move(dx, dy)
        except OSError:
            pass
        if not self._hotkey_ok:
            self._poll_fallback_hotkeys()
        self.overlay.set_runtime(result.runtime_label, result.layout_key)
        self.radial.set_view(
            result.radial,
            self.profile.overlay.screen_index,
            self.profile.overlay.theme,
            self.profile.overlay.radial_alpha,
        )
        if self.profile.overlay.current_buttons_enabled:
            self.current_buttons.set_frames(result.pressed_frames)
        if result.long_triggered and self.profile.long_press_rumble:
            self.reader.pulse()
        self._last_layer = result.runtime_label
        self.window.set_pad_state(pad, result.runtime_label, result.mumble)

    def _poll_fallback_hotkeys(self) -> None:
        mapping = {
            HOTKEY_EDIT: vk_from_name(self.profile.hotkeys.toggle_overlay_edit),
            HOTKEY_VISIBLE: vk_from_name(self.profile.hotkeys.toggle_overlay_visible),
        }
        for hotkey_id, vk in mapping.items():
            if vk is None:
                continue
            down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            was_down = self._hotkey_prev.get(hotkey_id, False)
            if down and not was_down:
                self._on_hotkey(hotkey_id)
            self._hotkey_prev[hotkey_id] = down

    def _dispatch(self, events: list[InputEvent]) -> None:
        try:
            for event in events:
                if event.kind == "key_down":
                    self.sender.key_down(event.key)
                elif event.kind == "key_up":
                    self.sender.key_up(event.key)
                elif event.kind == "tap_key":
                    self.sender.tap_key(event.key)
                elif event.kind == "mouse_down":
                    self.sender.mouse_down(event.mouse_button)
                elif event.kind == "mouse_up":
                    self.sender.mouse_up(event.mouse_button)
                elif event.kind == "tap_mouse":
                    self.sender.tap_mouse(event.mouse_button)
        except OSError:
            pass

    def shutdown(self) -> None:
        self._timer.stop()
        self.reader.stop_vibration()
        self.sender.release_all()
        self.mumble.close()
        if self._hotkeys is not None:
            self._hotkeys.unregister_all()
        save_profile(self.profile, self.profile_path)

    def run(self) -> int:
        return self.app.exec()


def main() -> int:
    if sys.platform != "win32":
        print("GW2Controller roda apenas no Windows.")
        return 1
    controller = GW2ControllerApp()
    return controller.run()
