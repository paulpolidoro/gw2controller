from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, hypot, tau
from typing import Literal

from gw2controller.controller.xinput import ALL_BUTTONS, PadState
from gw2controller.gw2.mumble import MumbleState
from gw2controller.mapping.models import Action, Profile, RadialItem, ordered_keys

EventKind = Literal["key_down", "key_up", "mouse_down", "mouse_up", "tap_key", "tap_mouse"]


@dataclass
class InputEvent:
    kind: EventKind
    key: str = ""
    mouse_button: str = ""


@dataclass
class RadialView:
    active: bool = False
    items: list[tuple[str, str]] = field(default_factory=list)
    selected: int | None = None


@dataclass
class TickResult:
    runtime_label: str
    captions: dict[str, str]
    mouse_dx: float
    mouse_dy: float
    events: list[InputEvent] = field(default_factory=list)
    pad: PadState = field(default_factory=PadState)
    release_all: bool = False
    radial: RadialView = field(default_factory=RadialView)
    mumble: MumbleState = field(default_factory=MumbleState)


def apply_radial_deadzone(x: float, y: float, deadzone: float) -> tuple[float, float]:
    magnitude = hypot(x, y)
    if magnitude <= deadzone or magnitude == 0:
        return 0.0, 0.0
    scale = (magnitude - deadzone) / (1.0 - deadzone)
    scale = min(1.0, max(0.0, scale))
    return (x / magnitude) * scale, (y / magnitude) * scale


def _angle_index(x: float, y: float, count: int) -> int:
    angle = atan2(x, y) % tau
    slice_size = tau / count
    return int((angle + slice_size / 2) % tau / slice_size) % count


class MappingEngine:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self._prev_buttons: dict[str, bool] = {name: False for name in ALL_BUTTONS}
        self._down_since: dict[str, float] = {}
        self._long_armed: set[str] = set()
        self._active: dict[str, Action] = {}
        self._mod_order: list[str] = []
        self._chords: dict[str, list[str]] = {}
        self._move_held: set[str] = set()
        self._scheduled: list[tuple[float, InputEvent]] = []
        self._radial_button: str | None = None
        self._radial_items: list[RadialItem] = []
        self._radial_selected: int | None = None
        self._was_connected = False
        self._mumble = MumbleState()
        self._input_blocked = False

    def set_profile(self, profile: Profile) -> list[InputEvent]:
        events = self.release_held()
        self.profile = profile
        self._down_since.clear()
        self._long_armed.clear()
        self._scheduled.clear()
        self._close_radial()
        return events

    def set_mumble(self, state: MumbleState) -> list[InputEvent]:
        was_blocked = self._input_blocked
        self._mumble = state
        self._input_blocked = state.input_blocked
        if self._input_blocked and not was_blocked:
            events = self.release_held()
            self._scheduled.clear()
            self._close_radial()
            return events
        return []

    def release_held(self) -> list[InputEvent]:
        events: list[InputEvent] = []
        for button in list(self._active):
            events.extend(self._deactivate(button, fire_radial=False))
        for key in list(self._move_held):
            events.append(InputEvent("key_up", key=key))
        self._move_held.clear()
        self._chords.clear()
        return events

    def tick(self, pad: PadState, now_s: float, dt_s: float) -> TickResult:
        events: list[InputEvent] = []
        if self._was_connected and not pad.connected:
            events.extend(self.release_held())
            self._scheduled.clear()
            self._prev_buttons = {name: False for name in ALL_BUTTONS}
            self._was_connected = False
            return TickResult(
                "Padrão",
                {},
                0.0,
                0.0,
                events,
                pad,
                release_all=True,
                mumble=self._mumble,
            )
        self._was_connected = pad.connected
        if not pad.connected:
            return TickResult("Padrão", {}, 0.0, 0.0, [], pad, mumble=self._mumble)

        if self._input_blocked:
            # Solta o que ainda estiver apertado e ignora novos inputs.
            if any(self._active) or self._move_held or self._scheduled:
                events.extend(self.release_held())
                self._scheduled.clear()
                self._close_radial()
            self._prev_buttons = {name: bool(pad.buttons.get(name)) for name in ALL_BUTTONS}
            return TickResult(
                runtime_label=self._runtime_label(),
                captions=self._captions(),
                mouse_dx=0.0,
                mouse_dy=0.0,
                events=events,
                pad=pad,
                release_all=bool(events),
                mumble=self._mumble,
            )

        threshold = max(0.08, self.profile.long_press_ms / 1000.0)

        for button in ALL_BUTTONS:
            down = bool(pad.buttons.get(button))
            was_down = self._prev_buttons.get(button, False)
            if down and not was_down:
                self._down_since[button] = now_s
                self._long_armed.discard(button)
                events.extend(self._on_press(button, now_s))
            elif down and was_down:
                events.extend(self._on_hold(button, now_s, threshold))
            elif not down and was_down:
                events.extend(self._on_release(button, now_s, threshold))

        self._prev_buttons = {name: bool(pad.buttons.get(name)) for name in ALL_BUTTONS}
        events.extend(self._resync_held(pad))
        events.extend(self._due_events(now_s))
        events.extend(self._update_radial(pad))

        move_events, mouse_dx, mouse_dy = self._process_sticks(pad, dt_s)
        events.extend(move_events)
        if self._radial_button:
            mouse_dx, mouse_dy = 0.0, 0.0

        return TickResult(
            runtime_label=self._runtime_label(),
            captions=self._captions(),
            mouse_dx=mouse_dx,
            mouse_dy=mouse_dy,
            events=events,
            pad=pad,
            radial=self._radial_view(),
            mumble=self._mumble,
        )

    def _on_press(self, button: str, now_s: float) -> list[InputEvent]:
        override = self._override_for(button)
        if override is not None:
            return self._activate(button, override)
        mapping = self.profile.button_map(button)
        if mapping.mode == "press":
            return self._activate(button, mapping.press)
        if mapping.short.type in ("modifier", "radial"):
            return self._activate(button, mapping.short)
        return []

    def _on_hold(self, button: str, now_s: float, threshold: float) -> list[InputEvent]:
        mapping = self.profile.button_map(button)
        if mapping.mode != "short_long" or button in self._long_armed:
            return []
        if self._override_for(button) is not None:
            return []
        started = self._down_since.get(button, now_s)
        if now_s - started < threshold:
            return []
        self._long_armed.add(button)
        events: list[InputEvent] = []
        current = self._active.get(button)
        if current is not None:
            events.extend(self._deactivate(button, fire_radial=False))
        events.extend(self._activate(button, mapping.long))
        return events

    def _on_release(self, button: str, now_s: float, threshold: float) -> list[InputEvent]:
        mapping = self.profile.button_map(button)
        started = self._down_since.pop(button, now_s)
        long_armed = button in self._long_armed
        self._long_armed.discard(button)
        override = self._override_for(button)
        events: list[InputEvent] = []
        if button in self._active:
            events.extend(self._deactivate(button, fire_radial=True, now_s=now_s))
        elif (
            override is None
            and mapping.mode == "short_long"
            and not long_armed
            and now_s - started < threshold
            and mapping.short.type == "keys"
            and mapping.short.is_active()
        ):
            events.extend(self._tap_keys(mapping.short.chord(), now_s))
        if (
            override is None
            and mapping.mode == "press"
            and mapping.release.type == "keys"
            and mapping.release.is_active()
        ):
            events.extend(self._tap_keys(mapping.release.chord(), now_s))
        return events

    def _activate(self, button: str, action: Action) -> list[InputEvent]:
        if action.type == "none" or (action.type != "modifier" and not action.is_active()):
            return []
        self._active[button] = action
        events: list[InputEvent] = []
        if action.type == "keys":
            events.extend(self._set_chord(button, action.chord()))
        elif action.type == "modifier":
            if button in self._mod_order:
                self._mod_order.remove(button)
            self._mod_order.append(button)
        elif action.type == "radial":
            self._open_radial(button, action.active_radial_items())
        return events

    def _deactivate(self, button: str, fire_radial: bool, now_s: float = 0.0) -> list[InputEvent]:
        action = self._active.pop(button, None)
        events: list[InputEvent] = []
        if action is None:
            return events
        if action.type == "keys":
            events.extend(self._set_chord(button, []))
        elif action.type == "modifier":
            if button in self._mod_order:
                self._mod_order.remove(button)
        elif action.type == "radial" and self._radial_button == button:
            if fire_radial:
                events.extend(self._fire_radial(now_s))
            self._close_radial()
        return events

    def _resync_held(self, pad: PadState) -> list[InputEvent]:
        events: list[InputEvent] = []
        for button in ALL_BUTTONS:
            if not pad.buttons.get(button):
                continue
            if button in self._mod_order:
                continue
            desired = self._intended_action(button, pad)
            current = self._active.get(button)
            if _same_action(current, desired):
                continue
            if current is not None:
                events.extend(self._deactivate(button, fire_radial=False))
            events.extend(self._activate(button, desired))
        return events

    def _intended_action(self, button: str, pad: PadState) -> Action:
        override = self._override_for(button)
        if override is not None:
            return override
        mapping = self.profile.button_map(button)
        if mapping.mode == "press":
            return mapping.press
        if button in self._long_armed:
            return mapping.long
        if mapping.short.type in ("modifier", "radial"):
            return mapping.short
        return Action()

    def _override_for(self, button: str) -> Action | None:
        for mod in reversed(self._mod_order):
            if mod == button:
                continue
            action = self._active.get(mod)
            if action is None or action.type != "modifier":
                continue
            override = action.overrides.get(button)
            if override is not None and override.is_active():
                return override
        layers = self.profile.context_layers
        if self._mumble.map_open:
            override = layers.map_open.get(button)
            if override is not None and override.is_active():
                return override
        if self._mumble.textbox_focused:
            override = layers.chat.get(button)
            if override is not None and override.is_active():
                return override
        if self._mumble.mounted:
            override = layers.mounted.get(button)
            if override is not None and override.is_active():
                return override
        return None

    def _set_chord(self, button: str, keys: list[str]) -> list[InputEvent]:
        old = self._chords.get(button, [])
        new = ordered_keys(keys)
        if old == new:
            return []
        events: list[InputEvent] = []
        for key in reversed(old):
            events.append(_up_event(key))
        for key in new:
            events.append(_down_event(key))
        if new:
            self._chords[button] = new
        else:
            self._chords.pop(button, None)
        return events

    def _tap_keys(self, keys: list[str], now_s: float) -> list[InputEvent]:
        chord = ordered_keys(keys)
        events = [_down_event(key) for key in chord]
        for key in reversed(chord):
            self._scheduled.append((now_s + 0.03, _up_event(key)))
        return events

    def _open_radial(self, button: str, items: list[RadialItem]) -> None:
        self._radial_button = button
        self._radial_items = items
        self._radial_selected = None

    def _close_radial(self) -> None:
        self._radial_button = None
        self._radial_items = []
        self._radial_selected = None

    def _update_radial(self, pad: PadState) -> list[InputEvent]:
        if not self._radial_button or not self._radial_items:
            return []
        deadzone = self.profile.radial_deadzone
        mag = hypot(pad.rx, pad.ry)
        if mag >= deadzone:
            self._radial_selected = _angle_index(pad.rx, pad.ry, len(self._radial_items))
        return []

    def _fire_radial(self, now_s: float) -> list[InputEvent]:
        if self._radial_selected is None:
            return []
        if not (0 <= self._radial_selected < len(self._radial_items)):
            return []
        item = self._radial_items[self._radial_selected]
        return self._tap_keys(item.keys, now_s)

    def _radial_view(self) -> RadialView:
        if not self._radial_button:
            return RadialView()
        items = [(item.display_label(), keys_label_safe(item.keys)) for item in self._radial_items]
        return RadialView(True, items, self._radial_selected)

    def _runtime_label(self) -> str:
        parts: list[str] = []
        if self._mod_order:
            parts.append("+".join(self._mod_order))
        if self._mumble.map_open:
            parts.append("Mapa")
        if self._mumble.textbox_focused:
            parts.append("Chat")
        if self._mumble.mounted:
            parts.append("Montado")
        if self._input_blocked:
            parts.append("Bloqueado")
        return " · ".join(parts) if parts else "Padrão"

    def _captions(self) -> dict[str, str]:
        captions: dict[str, str] = {}
        for button in ALL_BUTTONS:
            override = self._override_for(button)
            if override is not None:
                captions[button] = override.label()
                continue
            mapping = self.profile.button_map(button)
            captions[button] = mapping.preview_action().label()
        return captions

    def _due_events(self, now_s: float) -> list[InputEvent]:
        due: list[tuple[float, InputEvent]] = []
        pending: list[tuple[float, InputEvent]] = []
        for when, event in self._scheduled:
            if when <= now_s:
                due.append((when, event))
            else:
                pending.append((when, event))
        self._scheduled = pending
        due.sort(key=lambda item: item[0])
        return [event for _, event in due]

    def _process_sticks(self, pad: PadState, dt_s: float) -> tuple[list[InputEvent], float, float]:
        events: list[InputEvent] = []
        desired_move: set[str] = set()
        mouse_dx = 0.0
        mouse_dy = 0.0
        left = self.profile.sticks.get("left")
        if left and left.mode in ("wasd", "arrows"):
            x, y = apply_radial_deadzone(pad.lx, pad.ly, left.deadzone)
            if y > 0.25:
                desired_move.add(left.keys.get("up", "w"))
            if y < -0.25:
                desired_move.add(left.keys.get("down", "s"))
            if x < -0.25:
                desired_move.add(left.keys.get("left", "a"))
            if x > 0.25:
                desired_move.add(left.keys.get("right", "d"))
        right = self.profile.sticks.get("right")
        if right and right.mode == "mouse" and not self._radial_button:
            x, y = apply_radial_deadzone(pad.rx, pad.ry, right.deadzone)
            scale = right.sensitivity * (dt_s / 0.008)
            mouse_dx = x * scale
            mouse_dy = -y * scale
        left_mouse = self.profile.sticks.get("left")
        if left_mouse and left_mouse.mode == "mouse":
            x, y = apply_radial_deadzone(pad.lx, pad.ly, left_mouse.deadzone)
            scale = left_mouse.sensitivity * (dt_s / 0.008)
            mouse_dx += x * scale
            mouse_dy += -y * scale
        for key in desired_move - self._move_held:
            events.append(InputEvent("key_down", key=key))
        for key in self._move_held - desired_move:
            events.append(InputEvent("key_up", key=key))
        self._move_held = desired_move
        return events, mouse_dx, mouse_dy


def keys_label_safe(keys: list[str]) -> str:
    from gw2controller.mapping.models import keys_label

    return keys_label(keys)


def _same_action(current: Action | None, desired: Action) -> bool:
    if current is None:
        return not desired.is_active() and desired.type != "modifier"
    if current.type != desired.type:
        return False
    if current.type == "keys":
        return current.chord() == desired.chord()
    if current.type == "modifier":
        return current is desired or current.overrides == desired.overrides
    if current.type == "radial":
        return current.active_radial_items() == desired.active_radial_items()
    return True


def _down_event(key: str) -> InputEvent:
    if key.startswith("mouse_"):
        return InputEvent("mouse_down", mouse_button=key.removeprefix("mouse_"))
    return InputEvent("key_down", key=key)


def _up_event(key: str) -> InputEvent:
    if key.startswith("mouse_"):
        return InputEvent("mouse_up", mouse_button=key.removeprefix("mouse_"))
    return InputEvent("key_up", key=key)
