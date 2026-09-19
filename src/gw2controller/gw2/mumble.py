from __future__ import annotations

import ctypes
import json
import mmap
from ctypes import wintypes
from dataclasses import dataclass

UI_MAP_OPEN = 0x1
UI_GAME_FOCUS = 0x8
UI_TEXTBOX_FOCUS = 0x20


class Link(ctypes.Structure):
    _fields_ = [
        ("uiVersion", wintypes.UINT),
        ("uiTick", wintypes.DWORD),
        ("fAvatarPosition", ctypes.c_float * 3),
        ("fAvatarFront", ctypes.c_float * 3),
        ("fAvatarTop", ctypes.c_float * 3),
        ("name", ctypes.c_wchar * 256),
        ("fCameraPosition", ctypes.c_float * 3),
        ("fCameraFront", ctypes.c_float * 3),
        ("fCameraTop", ctypes.c_float * 3),
        ("identity", ctypes.c_wchar * 256),
        ("context_len", wintypes.UINT),
    ]


class Context(ctypes.Structure):
    _fields_ = [
        ("serverAddress", ctypes.c_ubyte * 28),
        ("mapId", wintypes.UINT),
        ("mapType", wintypes.UINT),
        ("shardId", wintypes.UINT),
        ("instance", wintypes.UINT),
        ("buildId", wintypes.UINT),
        ("uiState", wintypes.UINT),
        ("compassWidth", wintypes.USHORT),
        ("compassHeight", wintypes.USHORT),
        ("compassRotation", ctypes.c_float),
        ("playerX", ctypes.c_float),
        ("playerY", ctypes.c_float),
        ("mapCenterX", ctypes.c_float),
        ("mapCenterY", ctypes.c_float),
        ("mapScale", ctypes.c_float),
        ("processId", wintypes.UINT),
        ("mountIndex", ctypes.c_ubyte),
    ]


@dataclass(frozen=True)
class MumbleState:
    available: bool = False
    ui_tick: int = 0
    map_open: bool = False
    game_focused: bool = False
    textbox_focused: bool = False
    mounted: bool = False
    map_id: int = 0
    mount_index: int = 0
    character: str = ""
    identity: dict | None = None

    @property
    def input_blocked(self) -> bool:
        if not self.available:
            return False
        if not self.game_focused:
            return True
        return False

    def status_label(self) -> str:
        if not self.available:
            return "Mumble: off"
        parts = []
        if self.map_open:
            parts.append("Mapa")
        if self.textbox_focused:
            parts.append("Chat")
        if self.mounted:
            parts.append("Montado")
        if not self.game_focused:
            parts.append("Sem foco")
        return "Mumble: " + (" · ".join(parts) if parts else "ok")


class MumbleLinkReader:
    """Lê a shared memory MumbleLink do Guild Wars 2."""

    def __init__(self, tagname: str = "MumbleLink") -> None:
        self._tagname = tagname
        self._mem: mmap.mmap | None = None
        self._last_tick = 0
        self._last_state = MumbleState()
        self._open()

    def _open(self) -> None:
        size_link = ctypes.sizeof(Link)
        size_context = ctypes.sizeof(Context)
        # GW2 exige o bloco completo (context 256 + description 4096).
        length = size_link + 256 + 4096
        try:
            self._mem = mmap.mmap(-1, length, tagname=self._tagname)
        except OSError:
            self._mem = None

    def close(self) -> None:
        if self._mem is not None:
            self._mem.close()
            self._mem = None

    def read(self) -> MumbleState:
        if self._mem is None:
            self._open()
        if self._mem is None:
            self._last_state = MumbleState()
            return self._last_state

        self._mem.seek(0)
        raw_link = self._mem.read(ctypes.sizeof(Link))
        raw_context = self._mem.read(ctypes.sizeof(Context))
        link = Link.from_buffer_copy(raw_link)
        context = Context.from_buffer_copy(raw_context)

        if not link.uiTick:
            self._last_state = MumbleState()
            return self._last_state

        identity: dict | None = None
        character = ""
        try:
            text = (link.identity or "").split("\x00", 1)[0].strip()
            if text:
                identity = json.loads(text)
                character = str(identity.get("name") or "")
        except (json.JSONDecodeError, TypeError, AttributeError):
            identity = None

        ui = int(context.uiState)
        state = MumbleState(
            available=True,
            ui_tick=int(link.uiTick),
            map_open=bool(ui & UI_MAP_OPEN),
            game_focused=bool(ui & UI_GAME_FOCUS),
            textbox_focused=bool(ui & UI_TEXTBOX_FOCUS),
            mounted=int(context.mountIndex) != 0,
            map_id=int(context.mapId),
            mount_index=int(context.mountIndex),
            character=character,
            identity=identity,
        )
        self._last_tick = state.ui_tick
        self._last_state = state
        return state
