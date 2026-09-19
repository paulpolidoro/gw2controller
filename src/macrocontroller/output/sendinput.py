from __future__ import annotations

import ctypes
from ctypes import wintypes

ULONG_PTR = ctypes.c_size_t

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

MAPVK_VK_TO_VSC = 0
MAPVK_VK_TO_VSC_EX = 4

VK_CODES: dict[str, int] = {}
for _letter in "abcdefghijklmnopqrstuvwxyz":
    VK_CODES[_letter] = ord(_letter.upper())
for _digit in "0123456789":
    VK_CODES[_digit] = ord(_digit)

VK_CODES.update(
    {
        "space": 0x20,
        "enter": 0x0D,
        "return": 0x0D,
        "tab": 0x09,
        "esc": 0x1B,
        "escape": 0x1B,
        "backspace": 0x08,
        "shift": 0x10,
        "ctrl": 0x11,
        "control": 0x11,
        "alt": 0x12,
        "lshift": 0xA0,
        "rshift": 0xA1,
        "lctrl": 0xA2,
        "rctrl": 0xA3,
        "lalt": 0xA4,
        "ralt": 0xA5,
        "win": 0x5B,
        "caps": 0x14,
        "capslock": 0x14,
        "insert": 0x2D,
        "delete": 0x2E,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
        "up": 0x26,
        "down": 0x28,
        "left": 0x25,
        "right": 0x27,
        "printscreen": 0x2C,
        "scrolllock": 0x91,
        "pause": 0x13,
        "numlock": 0x90,
        "semicolon": 0xBA,
        ";": 0xBA,
        "equals": 0xBB,
        "=": 0xBB,
        "comma": 0xBC,
        ",": 0xBC,
        "minus": 0xBD,
        "-": 0xBD,
        "period": 0xBE,
        ".": 0xBE,
        "slash": 0xBF,
        "/": 0xBF,
        "grave": 0xC0,
        "`": 0xC0,
        "lbracket": 0xDB,
        "[": 0xDB,
        "backslash": 0xDC,
        "\\": 0xDC,
        "rbracket": 0xDD,
        "]": 0xDD,
        "quote": 0xDE,
        "'": 0xDE,
        "numpad0": 0x60,
        "numpad1": 0x61,
        "numpad2": 0x62,
        "numpad3": 0x63,
        "numpad4": 0x64,
        "numpad5": 0x65,
        "numpad6": 0x66,
        "numpad7": 0x67,
        "numpad8": 0x68,
        "numpad9": 0x69,
        "numpad_multiply": 0x6A,
        "numpad_add": 0x6B,
        "numpad_subtract": 0x6D,
        "numpad_decimal": 0x6E,
        "numpad_divide": 0x6F,
        "numpad_enter": 0x0D,
    }
)

NUMPAD_VK_TO_NAME = {
    0x60: "numpad0",
    0x61: "numpad1",
    0x62: "numpad2",
    0x63: "numpad3",
    0x64: "numpad4",
    0x65: "numpad5",
    0x66: "numpad6",
    0x67: "numpad7",
    0x68: "numpad8",
    0x69: "numpad9",
    0x6A: "numpad_multiply",
    0x6B: "numpad_add",
    0x6D: "numpad_subtract",
    0x6E: "numpad_decimal",
    0x6F: "numpad_divide",
}
EXTENDED_KEY_NAMES = {"numpad_enter", "numpad_divide"}
for _i in range(1, 13):
    VK_CODES[f"f{_i}"] = 0x70 + _i - 1

EXTENDED_VKS = {
    0x21,
    0x22,
    0x23,
    0x24,
    0x25,
    0x26,
    0x27,
    0x28,
    0x2D,
    0x2E,
    0x5B,
    0x5C,
    0xA3,
    0xA5,
    0x6F,
}

MOUSE_KEY_NAMES = {
    "mouse_left": "left",
    "mouse_right": "right",
    "mouse_middle": "middle",
    "mouse_x1": "x1",
    "mouse_x2": "x2",
}

MOUSE_BUTTONS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, 0),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, 0),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP, 0),
    "x1": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON1),
    "x2": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON2),
}


def _mouse_from_key(name: str) -> str | None:
    return MOUSE_KEY_NAMES.get(normalize_key_name(name))


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    )


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class INPUTUNION(ctypes.Union):
    _fields_ = (
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    )


class INPUT(ctypes.Structure):
    _fields_ = (
        ("type", wintypes.DWORD),
        ("union", INPUTUNION),
    )


user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
user32.MapVirtualKeyW.restype = wintypes.UINT


def normalize_key_name(name: str) -> str:
    key = name.strip().lower()
    aliases = {
        "return": "enter",
        "esc": "escape",
        "control": "ctrl",
        "windows": "win",
        "numpad_multiply": "numpad_multiply",
        "num*": "numpad_multiply",
        "numpad*": "numpad_multiply",
        "num+": "numpad_add",
        "numpad+": "numpad_add",
        "numpad_plus": "numpad_add",
        "num-": "numpad_subtract",
        "numpad-": "numpad_subtract",
        "numpad_minus": "numpad_subtract",
        "num.": "numpad_decimal",
        "numpad.": "numpad_decimal",
        "numpad_dot": "numpad_decimal",
        "num/": "numpad_divide",
        "numpad/": "numpad_divide",
        "numenter": "numpad_enter",
        "numpadenter": "numpad_enter",
    }
    compact = key.replace(" ", "")
    if compact in aliases:
        return aliases[compact]
    for prefix in ("numpad", "num", "kp"):
        if not compact.startswith(prefix):
            continue
        rest = compact[len(prefix):].lstrip("_")
        if rest.isdigit() and len(rest) == 1:
            return f"numpad{rest}"
    return aliases.get(key, key)


def key_name_from_native_vk(vk: int) -> str | None:
    return NUMPAD_VK_TO_NAME.get(int(vk))


def resolve_vk(name: str) -> int | None:
    key = normalize_key_name(name)
    if key in VK_CODES:
        return VK_CODES[key]
    if len(key) == 1:
        return VK_CODES.get(key)
    return None


def key_display_name(name: str) -> str:
    key = normalize_key_name(name)
    specials = {
        "space": "Espaço",
        "enter": "Enter",
        "escape": "Esc",
        "backspace": "Backspace",
        "shift": "Shift",
        "ctrl": "Ctrl",
        "alt": "Alt",
        "tab": "Tab",
        "pageup": "Page Up",
        "pagedown": "Page Down",
        "mouse_left": "Mouse esquerdo",
        "mouse_right": "Mouse direito",
        "mouse_middle": "Mouse meio",
        "mouse_x1": "Mouse 4",
        "mouse_x2": "Mouse 5",
        "numpad_multiply": "Num *",
        "numpad_add": "Num +",
        "numpad_subtract": "Num -",
        "numpad_decimal": "Num .",
        "numpad_divide": "Num /",
        "numpad_enter": "Num Enter",
    }
    if key in specials:
        return specials[key]
    if key.startswith("numpad") and key[6:].isdigit():
        return f"Num {key[6:]}"
    if key.startswith("f") and key[1:].isdigit():
        return key.upper()
    return key.upper() if len(key) == 1 else key


class InputSender:
    def __init__(self) -> None:
        self._held_keys: set[str] = set()
        self._held_mouse: set[str] = set()

    def key_down(self, name: str) -> None:
        key = normalize_key_name(name)
        mouse = _mouse_from_key(key)
        if mouse:
            self.mouse_down(mouse)
            return
        vk = resolve_vk(key)
        if vk is None:
            return
        self._send_key(vk, up=False, name=key)
        self._held_keys.add(key)

    def key_up(self, name: str) -> None:
        key = normalize_key_name(name)
        mouse = _mouse_from_key(key)
        if mouse:
            self.mouse_up(mouse)
            return
        vk = resolve_vk(key)
        if vk is None:
            return
        self._send_key(vk, up=True, name=key)
        self._held_keys.discard(key)

    def tap_key(self, name: str) -> None:
        self.key_down(name)
        self.key_up(name)

    def mouse_move(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi = MOUSEINPUT(dx, dy, 0, MOUSEEVENTF_MOVE, 0, 0)
        self._send(inp)

    def mouse_down(self, button: str) -> None:
        flags_down, _, data = self._mouse_flags(button)
        self._send_mouse(flags_down, data)
        self._held_mouse.add(button)

    def mouse_up(self, button: str) -> None:
        _, flags_up, data = self._mouse_flags(button)
        self._send_mouse(flags_up, data)
        self._held_mouse.discard(button)

    def tap_mouse(self, button: str) -> None:
        self.mouse_down(button)
        self.mouse_up(button)

    def release_all(self) -> None:
        for key in list(self._held_keys):
            self.key_up(key)
        for button in list(self._held_mouse):
            self.mouse_up(button)

    def _mouse_flags(self, button: str) -> tuple[int, int, int]:
        name = button.strip().lower()
        if name not in MOUSE_BUTTONS:
            raise ValueError(f"Botão de mouse desconhecido: {button}")
        return MOUSE_BUTTONS[name]

    def _send_key(self, vk: int, up: bool, name: str = "") -> None:
        scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC_EX) or user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
        flags = 0
        w_vk = 0
        w_scan = scan
        if scan:
            flags |= KEYEVENTF_SCANCODE
        else:
            w_vk = vk
            w_scan = 0
        if vk in EXTENDED_VKS or name in EXTENDED_KEY_NAMES:
            flags |= KEYEVENTF_EXTENDEDKEY
        if up:
            flags |= KEYEVENTF_KEYUP
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki = KEYBDINPUT(w_vk, w_scan, flags, 0, 0)
        self._send(inp)

    def _send_mouse(self, flags: int, data: int) -> None:
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi = MOUSEINPUT(0, 0, data, flags, 0, 0)
        self._send(inp)

    def _send(self, inp: INPUT) -> None:
        sent = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if sent != 1:
            error = ctypes.get_last_error()
            raise ctypes.WinError(error)
