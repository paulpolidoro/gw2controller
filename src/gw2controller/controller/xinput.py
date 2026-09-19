from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Any

XINPUT_GAMEPAD_DPAD_UP = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT = 0x0008
XINPUT_GAMEPAD_START = 0x0010
XINPUT_GAMEPAD_BACK = 0x0020
XINPUT_GAMEPAD_LEFT_THUMB = 0x0040
XINPUT_GAMEPAD_RIGHT_THUMB = 0x0080
XINPUT_GAMEPAD_LEFT_SHOULDER = 0x0100
XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200
XINPUT_GAMEPAD_A = 0x1000
XINPUT_GAMEPAD_B = 0x2000
XINPUT_GAMEPAD_X = 0x4000
XINPUT_GAMEPAD_Y = 0x8000

ERROR_SUCCESS = 0
ERROR_DEVICE_NOT_CONNECTED = 1167

BUTTON_MASKS: dict[str, int] = {
    "DPAD_UP": XINPUT_GAMEPAD_DPAD_UP,
    "DPAD_DOWN": XINPUT_GAMEPAD_DPAD_DOWN,
    "DPAD_LEFT": XINPUT_GAMEPAD_DPAD_LEFT,
    "DPAD_RIGHT": XINPUT_GAMEPAD_DPAD_RIGHT,
    "MENU": XINPUT_GAMEPAD_START,
    "VIEW": XINPUT_GAMEPAD_BACK,
    "LS": XINPUT_GAMEPAD_LEFT_THUMB,
    "RS": XINPUT_GAMEPAD_RIGHT_THUMB,
    "LB": XINPUT_GAMEPAD_LEFT_SHOULDER,
    "RB": XINPUT_GAMEPAD_RIGHT_SHOULDER,
    "A": XINPUT_GAMEPAD_A,
    "B": XINPUT_GAMEPAD_B,
    "X": XINPUT_GAMEPAD_X,
    "Y": XINPUT_GAMEPAD_Y,
}

DIGITAL_BUTTONS = list(BUTTON_MASKS.keys())
TRIGGER_BUTTONS = ["LT", "RT"]
ALL_BUTTONS = DIGITAL_BUTTONS + TRIGGER_BUTTONS

FACE_BUTTONS = ["A", "B", "X", "Y"]
BUMPER_BUTTONS = ["LB", "RB"]
STICK_CLICKS = ["LS", "RS"]
DPAD_BUTTONS = ["DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT"]
SYSTEM_BUTTONS = ["VIEW", "MENU"]

BUTTON_LABELS: dict[str, str] = {
    "A": "A",
    "B": "B",
    "X": "X",
    "Y": "Y",
    "LB": "LB",
    "RB": "RB",
    "LT": "LT",
    "RT": "RT",
    "LS": "LS (click)",
    "RS": "RS (click)",
    "DPAD_UP": "D-pad cima",
    "DPAD_DOWN": "D-pad baixo",
    "DPAD_LEFT": "D-pad esquerda",
    "DPAD_RIGHT": "D-pad direita",
    "VIEW": "View",
    "MENU": "Menu",
}


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", wintypes.SHORT),
        ("sThumbLY", wintypes.SHORT),
        ("sThumbRX", wintypes.SHORT),
        ("sThumbRY", wintypes.SHORT),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


def _load_xinput() -> Any:
    for name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
        try:
            return ctypes.WinDLL(name)
        except OSError:
            continue
    raise OSError("Nenhuma DLL XInput encontrada (xinput1_4/1_3/9_1_0).")


def _normalize_stick(value: int) -> float:
    if value < 0:
        return max(-1.0, value / 32768.0)
    return min(1.0, value / 32767.0)


def _normalize_trigger(value: int) -> float:
    return max(0.0, min(1.0, value / 255.0))


@dataclass
class PadState:
    connected: bool = False
    index: int = 0
    packet: int = 0
    buttons: dict[str, bool] = field(default_factory=dict)
    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    lt: float = 0.0
    rt: float = 0.0

    def pressed(self) -> list[str]:
        return [name for name, down in self.buttons.items() if down]


class XInputReader:
    def __init__(self, index: int = 0, trigger_threshold: float = 0.5) -> None:
        self.index = index
        self.trigger_threshold = trigger_threshold
        self._dll: Any | None = None
        self._get_state: Any | None = None
        self._load_error: str | None = None
        try:
            self._dll = _load_xinput()
            self._get_state = self._dll.XInputGetState
            self._get_state.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
            self._get_state.restype = wintypes.DWORD
        except OSError as exc:
            self._load_error = str(exc)

    @property
    def available(self) -> bool:
        return self._get_state is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def read(self) -> PadState:
        empty = {name: False for name in ALL_BUTTONS}
        if self._get_state is None:
            return PadState(connected=False, index=self.index, buttons=empty)

        state = XINPUT_STATE()
        result = self._get_state(self.index, ctypes.byref(state))
        if result != ERROR_SUCCESS:
            return PadState(connected=False, index=self.index, buttons=empty)

        pad = state.Gamepad
        buttons = {
            name: bool(pad.wButtons & mask) for name, mask in BUTTON_MASKS.items()
        }
        lt = _normalize_trigger(pad.bLeftTrigger)
        rt = _normalize_trigger(pad.bRightTrigger)
        buttons["LT"] = lt >= self.trigger_threshold
        buttons["RT"] = rt >= self.trigger_threshold
        return PadState(
            connected=True,
            index=self.index,
            packet=state.dwPacketNumber,
            buttons=buttons,
            lx=_normalize_stick(pad.sThumbLX),
            ly=_normalize_stick(pad.sThumbLY),
            rx=_normalize_stick(pad.sThumbRX),
            ry=_normalize_stick(pad.sThumbRY),
            lt=lt,
            rt=rt,
        )
