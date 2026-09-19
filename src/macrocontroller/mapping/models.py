from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

PressMode = Literal["press", "short_long"]
ActionType = Literal["none", "keys", "modifier", "radial"]
StickMode = Literal["wasd", "arrows", "mouse", "off"]
MAX_RADIAL_ITEMS = 8
MOUSE_KEY_PREFIX = "mouse_"

MODIFIER_KEY_ORDER = ("shift", "ctrl", "alt", "lshift", "rshift", "lctrl", "rctrl", "lalt", "ralt", "win")


def ordered_keys(keys: list[str]) -> list[str]:
    seen: list[str] = []
    for key in keys:
        name = str(key).strip().lower()
        if name and name not in seen:
            seen.append(name)
    mods = [key for key in MODIFIER_KEY_ORDER if key in seen]
    rest = [key for key in seen if key not in MODIFIER_KEY_ORDER]
    return mods + rest


def keys_label(keys: list[str]) -> str:
    from macrocontroller.output.sendinput import key_display_name

    names = [key_display_name(key) for key in ordered_keys(keys)]
    return "+".join(names) if names else "—"


def _clamp_percent(value: Any, default: int = 90, minimum: int = 10, maximum: int = 100) -> int:
    try:
        percent = int(round(float(value)))
    except (TypeError, ValueError):
        percent = default
    return max(minimum, min(maximum, percent))


@dataclass
class RadialItem:
    label: str = ""
    keys: list[str] = field(default_factory=list)

    def is_active(self) -> bool:
        return bool(ordered_keys(self.keys))

    def display_label(self) -> str:
        return self.label.strip() or keys_label(self.keys)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RadialItem:
        data = data or {}
        keys = data.get("keys") or []
        if isinstance(keys, str):
            keys = [keys]
        return cls(label=str(data.get("label") or ""), keys=[str(k) for k in keys])

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "keys": ordered_keys(self.keys)}


@dataclass
class Action:
    type: ActionType = "none"
    keys: list[str] = field(default_factory=list)
    overrides: dict[str, Action] = field(default_factory=dict)
    radial_items: list[RadialItem] = field(default_factory=list)

    def is_active(self) -> bool:
        if self.type == "keys":
            return bool(ordered_keys(self.keys))
        if self.type == "modifier":
            return True
        if self.type == "radial":
            return any(item.is_active() for item in self.radial_items)
        return False

    def chord(self) -> list[str]:
        return ordered_keys(self.keys) if self.type == "keys" else []

    def active_radial_items(self) -> list[RadialItem]:
        return [item for item in self.radial_items[:MAX_RADIAL_ITEMS] if item.is_active()]

    def label(self) -> str:
        if self.type == "keys":
            return keys_label(self.keys)
        if self.type == "modifier":
            count = sum(1 for item in self.overrides.values() if item.is_active())
            return f"Modificador ({count})"
        if self.type == "radial":
            return f"Radial ({len(self.active_radial_items())})"
        return "—"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Action:
        if not data:
            return cls()
        raw = str(data.get("type") or "none")
        action_type: ActionType = raw if raw in ("keys", "modifier", "radial") else "none"  # type: ignore[assignment]
        keys = data.get("keys") or []
        if isinstance(keys, str):
            keys = [keys]
        overrides = {
            str(button): Action.from_dict(payload)
            for button, payload in dict(data.get("overrides") or {}).items()
        }
        items = [RadialItem.from_dict(item) for item in list(data.get("radial_items") or [])[:MAX_RADIAL_ITEMS]]
        while len(items) < MAX_RADIAL_ITEMS and action_type == "radial":
            items.append(RadialItem())
        return cls(type=action_type, keys=[str(k) for k in keys], overrides=overrides, radial_items=items)

    def to_dict(self) -> dict[str, Any]:
        if self.type == "none" or (self.type != "modifier" and not self.is_active()):
            return {"type": "none"}
        payload: dict[str, Any] = {"type": self.type}
        if self.type == "keys":
            payload["keys"] = self.chord()
        elif self.type == "modifier":
            payload["overrides"] = {
                button: action.to_dict()
                for button, action in self.overrides.items()
                if action.is_active()
            }
        elif self.type == "radial":
            payload["radial_items"] = [item.to_dict() for item in self.radial_items[:MAX_RADIAL_ITEMS]]
        return payload


@dataclass
class ButtonMap:
    mode: PressMode = "press"
    press: Action = field(default_factory=Action)
    release: Action = field(default_factory=Action)
    short: Action = field(default_factory=Action)
    long: Action = field(default_factory=Action)

    def slot_action(self, slot: str) -> Action:
        if self.mode == "short_long":
            return self.short if slot == "short" else self.long
        if slot == "release":
            return self.release
        return self.press

    def set_slot_action(self, slot: str, action: Action) -> None:
        if self.mode == "short_long":
            if slot == "short":
                self.short = action
            else:
                self.long = action
            return
        if slot == "release":
            self.release = action
            return
        self.press = action

    def modifier_slots(self) -> list[str]:
        slots: list[str] = []
        if self.mode == "press" and self.press.type == "modifier":
            slots.append("press")
        if self.mode == "short_long":
            if self.short.type == "modifier":
                slots.append("short")
            if self.long.type == "modifier":
                slots.append("long")
        return slots

    def preview_action(self) -> Action:
        if self.mode == "short_long":
            return self.short if self.short.is_active() or self.short.type == "modifier" else self.long
        return self.press

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ButtonMap:
        data = data or {}
        mode = str(data.get("mode") or "press")
        press_mode: PressMode = "short_long" if mode == "short_long" else "press"
        return cls(
            mode=press_mode,
            press=Action.from_dict(data.get("press")),
            release=Action.from_dict(data.get("release")),
            short=Action.from_dict(data.get("short")),
            long=Action.from_dict(data.get("long")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"mode": self.mode}
        if self.mode == "press":
            payload["press"] = self.press.to_dict()
            payload["release"] = self.release.to_dict()
        else:
            payload["short"] = self.short.to_dict()
            payload["long"] = self.long.to_dict()
        return payload


@dataclass
class StickConfig:
    mode: StickMode = "off"
    deadzone: float = 0.2
    sensitivity: float = 8.0
    keys: dict[str, str] = field(
        default_factory=lambda: {"up": "w", "down": "s", "left": "a", "right": "d"}
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, default_mode: StickMode) -> StickConfig:
        data = data or {}
        mode = str(data.get("mode", default_mode))
        valid: tuple[str, ...] = ("wasd", "arrows", "mouse", "off")
        stick_mode: StickMode = mode if mode in valid else default_mode  # type: ignore[assignment]
        keys = {"up": "w", "down": "s", "left": "a", "right": "d"}
        keys.update({k: str(v) for k, v in dict(data.get("keys") or {}).items()})
        if stick_mode == "arrows":
            keys = {
                "up": "up",
                "down": "down",
                "left": "left",
                "right": "right",
                **{k: str(v) for k, v in dict(data.get("keys") or {}).items()},
            }
        return cls(
            mode=stick_mode,
            deadzone=float(data.get("deadzone", 0.2)),
            sensitivity=float(data.get("sensitivity", 8.0)),
            keys=keys,
        )


@dataclass
class OverlaySlot:
    button: str
    x: int
    y: int
    size: int = 44
    id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OverlaySlot:
        return cls(
            button=str(data.get("button", "A")),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            size=int(data.get("size", 44)),
            id=str(data.get("id") or ""),
        )


@dataclass
class OverlayConfig:
    visible: bool = True
    screen_index: int = -1
    theme: str = "dark"
    radial_alpha: int = 90
    slots: list[OverlaySlot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OverlayConfig:
        data = data or {}
        slots = [OverlaySlot.from_dict(item) for item in data.get("slots", [])]
        theme = str(data.get("theme") or "dark").lower()
        if theme not in ("dark", "light"):
            theme = "dark"
        return cls(
            visible=bool(data.get("visible", True)),
            screen_index=int(data.get("screen_index", -1)),
            theme=theme,
            radial_alpha=_clamp_percent(data.get("radial_alpha", 90)),
            slots=slots,
        )


@dataclass
class HotkeysConfig:
    toggle_overlay_edit: str = "F8"
    toggle_overlay_visible: str = "F9"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> HotkeysConfig:
        data = data or {}
        return cls(
            toggle_overlay_edit=str(data.get("toggle_overlay_edit", "F8")),
            toggle_overlay_visible=str(data.get("toggle_overlay_visible", "F9")),
        )


@dataclass
class Profile:
    name: str = "MMORPG Default"
    buttons: dict[str, ButtonMap] = field(default_factory=dict)
    sticks: dict[str, StickConfig] = field(default_factory=dict)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    hotkeys: HotkeysConfig = field(default_factory=HotkeysConfig)
    trigger_threshold: float = 0.5
    long_press_ms: int = 350
    radial_deadzone: float = 0.35

    def button_map(self, button: str) -> ButtonMap:
        return self.buttons.get(button, ButtonMap())

    def set_button_map(self, button: str, mapping: ButtonMap) -> None:
        self.buttons[button] = mapping

    def modifier_sources(self) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for button, mapping in self.buttons.items():
            for slot in mapping.modifier_slots():
                found.append((button, slot))
        return found

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "long_press_ms": self.long_press_ms,
            "radial_deadzone": self.radial_deadzone,
            "trigger_threshold": self.trigger_threshold,
            "hotkeys": asdict(self.hotkeys),
            "buttons": {button: mapping.to_dict() for button, mapping in self.buttons.items()},
            "sticks": {
                name: {
                    "mode": stick.mode,
                    "deadzone": stick.deadzone,
                    "sensitivity": stick.sensitivity,
                    "keys": stick.keys,
                }
                for name, stick in self.sticks.items()
            },
            "overlay": {
                "visible": self.overlay.visible,
                "screen_index": self.overlay.screen_index,
                "theme": self.overlay.theme,
                "radial_alpha": self.overlay.radial_alpha,
                "slots": [asdict(slot) for slot in self.overlay.slots],
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        sticks_data = dict(data.get("sticks") or {})
        sticks = {
            "left": StickConfig.from_dict(sticks_data.get("left"), "wasd"),
            "right": StickConfig.from_dict(sticks_data.get("right"), "mouse"),
        }
        buttons_data = dict(data.get("buttons") or {})
        if buttons_data:
            buttons = {name: ButtonMap.from_dict(payload) for name, payload in buttons_data.items()}
        else:
            buttons = _migrate_legacy_buttons(data)
        return cls(
            name=str(data.get("name") or "Perfil"),
            buttons=buttons,
            sticks=sticks,
            overlay=OverlayConfig.from_dict(data.get("overlay")),
            hotkeys=HotkeysConfig.from_dict(data.get("hotkeys")),
            trigger_threshold=float(data.get("trigger_threshold", 0.5)),
            long_press_ms=int(data.get("long_press_ms", data.get("sticky_ms", 350))),
            radial_deadzone=float(data.get("radial_deadzone", 0.35)),
        )


def _legacy_action(payload: dict[str, Any] | None) -> Action:
    if not payload:
        return Action()
    raw_type = str(payload.get("type") or "none")
    if raw_type == "key" and payload.get("key"):
        return Action(type="keys", keys=[str(payload["key"])])
    if raw_type == "keys":
        return Action.from_dict(payload)
    if raw_type == "mouse":
        button = str(payload.get("button") or payload.get("mouse_button") or "left")
        return Action(type="keys", keys=[f"mouse_{button}"])
    if raw_type == "macro":
        keys: list[str] = []
        for step in payload.get("steps") or []:
            if step.get("key"):
                keys.append(str(step["key"]))
            if step.get("mouse_button"):
                keys.append(f"mouse_{step['mouse_button']}")
        return Action(type="keys", keys=keys)
    if raw_type in ("modifier", "radial"):
        return Action.from_dict(payload)
    return Action()


def _migrate_legacy_buttons(data: dict[str, Any]) -> dict[str, ButtonMap]:
    layers = dict(data.get("layers") or {})
    modifiers = {
        str(button): str(layer)
        for button, layer in dict(data.get("modifiers") or {}).items()
    }
    default_layer = dict(layers.get("default") or {})
    buttons: dict[str, ButtonMap] = {}
    for button, payload in default_layer.items():
        if button in modifiers:
            continue
        buttons[button] = ButtonMap(mode="press", press=_legacy_action(payload))
    for button, layer_name in modifiers.items():
        overrides = {
            other: _legacy_action(payload)
            for other, payload in dict(layers.get(layer_name) or {}).items()
            if other != button
        }
        buttons[button] = ButtonMap(
            mode="press",
            press=Action(type="modifier", overrides=overrides),
        )
    return buttons
