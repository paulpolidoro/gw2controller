from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QObject, Signal

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000

VK_BY_NAME = {f"F{i}": 0x6F + i for i in range(1, 13)}
VK_BY_NAME.update(
    {
        "ESC": 0x1B,
        "ESCAPE": 0x1B,
        "TAB": 0x09,
        "HOME": 0x24,
        "END": 0x23,
        "INSERT": 0x2D,
        "DELETE": 0x2E,
    }
)

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


def vk_from_name(name: str) -> int | None:
    key = name.strip().upper().replace(" ", "")
    if key in VK_BY_NAME:
        return VK_BY_NAME[key]
    if len(key) == 1:
        return ord(key)
    return None


class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, manager: "GlobalHotkeys") -> None:
        super().__init__()
        self._manager = manager

    def nativeEventFilter(self, event_type: QByteArray | bytes | str, message: int) -> tuple[bool, int]:
        try:
            event_name = bytes(event_type) if not isinstance(event_type, (bytes, str)) else event_type
            if event_name in (b"windows_generic_MSG", b"windows_dispatcher_MSG", "windows_generic_MSG"):
                msg = MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    self._manager.hotkey_pressed.emit(int(msg.wParam))
                    return True, 0
        except (ValueError, TypeError, OSError):
            return False, 0
        return False, 0


class GlobalHotkeys(QObject):
    hotkey_pressed = Signal(int)

    def __init__(self, hwnd: int) -> None:
        super().__init__()
        self._hwnd = hwnd
        self._ids: dict[int, str] = {}
        self._filter = HotkeyFilter(self)

    @property
    def filter(self) -> HotkeyFilter:
        return self._filter

    def register(self, hotkey_id: int, key_name: str) -> bool:
        vk = vk_from_name(key_name)
        if vk is None:
            return False
        user32.UnregisterHotKey(self._hwnd, hotkey_id)
        ok = bool(user32.RegisterHotKey(self._hwnd, hotkey_id, MOD_NOREPEAT, vk))
        if ok:
            self._ids[hotkey_id] = key_name
        return ok

    def unregister_all(self) -> None:
        for hotkey_id in list(self._ids):
            user32.UnregisterHotKey(self._hwnd, hotkey_id)
        self._ids.clear()
