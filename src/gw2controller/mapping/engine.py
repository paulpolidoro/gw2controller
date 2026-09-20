from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, hypot, tau
from typing import Literal

from gw2controller.controller.xinput import ALL_BUTTONS, BUTTON_LABELS, PadState
from gw2controller.gw2.mumble import MumbleState
from gw2controller.mapping.models import (
    PANEL_BIND_ORDER,
    Action,
    Profile,
    RadialItem,
    ordered_keys,
)

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
class PanelView:
    active: bool = False
    title: str = ""
    items: list[tuple[str, str, str]] = field(default_factory=list)  # botão, nome, teclas
    owner: str = ""
    pressed: str | None = None


@dataclass
class PressedFrame:
    label: str
    progress: float = 0.0
    long_pending: bool = False


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
    layout_key: str = "default"
    pressed_frames: list[PressedFrame] = field(default_factory=list)
    long_triggered: bool = False
    panel: PanelView = field(default_factory=PanelView)


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
        self._panel_button: str | None = None
        self._panel_title: str = ""
        self._panel_items: list[RadialItem] = []
        self._panel_binds: dict[str, RadialItem] = {}
        self._panel_pressed: str | None = None
        self._panel_consume_release: set[str] = set()
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
        self._close_panel()
        return events

    def set_mumble(self, state: MumbleState) -> list[InputEvent]:
        was_blocked = self._input_blocked
        self._mumble = state
        self._input_blocked = state.input_blocked
        if self._input_blocked and not was_blocked:
            events = self.release_held()
            self._scheduled.clear()
            self._close_radial()
            self._close_panel()
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
        self._close_panel()
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
                layout_key=self._layout_key(),
                pressed_frames=[PressedFrame("-")],
            )
        self._was_connected = pad.connected
        if not pad.connected:
            return TickResult(
                "Padrão",
                {},
                0.0,
                0.0,
                [],
                pad,
                mumble=self._mumble,
                layout_key=self._layout_key(),
                pressed_frames=[PressedFrame("-")],
            )

        if self._input_blocked:
            # Solta o que ainda estiver apertado e ignora novos inputs.
            if any(self._active) or self._move_held or self._scheduled:
                events.extend(self.release_held())
                self._scheduled.clear()
                self._close_radial()
                self._close_panel()
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
                layout_key=self._layout_key(),
                pressed_frames=self._pressed_frames(pad, now_s),
                panel=self._panel_view(),
            )

        threshold = max(0.08, self.profile.long_press_ms / 1000.0)
        long_triggered = False

        for button in ALL_BUTTONS:
            down = bool(pad.buttons.get(button))
            was_down = self._prev_buttons.get(button, False)
            if down and not was_down:
                self._down_since[button] = now_s
                self._long_armed.discard(button)
                events.extend(self._on_press(button, now_s))
            elif down and was_down:
                hold_events, fired_long = self._on_hold(button, now_s, threshold)
                events.extend(hold_events)
                long_triggered = long_triggered or fired_long
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
            layout_key=self._layout_key(),
            pressed_frames=self._pressed_frames(pad, now_s),
            long_triggered=long_triggered,
            panel=self._panel_view(pad),
        )

    def _on_press(self, button: str, now_s: float) -> list[InputEvent]:
        if self._panel_button == button:
            self._close_panel()
            self._panel_consume_release.add(button)
            return []
        if self._panel_button and button in self._panel_binds:
            self._panel_pressed = button
            return self._tap_keys(self._panel_binds[button].keys, now_s)

        override = self._override_for(button)
        if override is not None:
            return self._activate(button, override)
        mapping = self.profile.button_map(button)
        if mapping.mode == "press":
            return self._activate(button, mapping.press)
        if mapping.short.type in ("modifier", "radial", "panel"):
            return self._activate(button, mapping.short)
        return []

    def _on_hold(self, button: str, now_s: float, threshold: float) -> tuple[list[InputEvent], bool]:
        if self._panel_button and button in self._panel_binds:
            return [], False
        if self._panel_button == button:
            return [], False
        mapping = self.profile.button_map(button)
        if mapping.mode != "short_long" or button in self._long_armed:
            return [], False
        if self._override_for(button) is not None:
            return [], False
        started = self._down_since.get(button, now_s)
        if now_s - started < threshold:
            return [], False
        self._long_armed.add(button)
        events: list[InputEvent] = []
        current = self._active.get(button)
        if current is not None:
            events.extend(self._deactivate(button, fire_radial=False))
        events.extend(self._activate(button, mapping.long))
        return events, True

    def _on_release(self, button: str, now_s: float, threshold: float) -> list[InputEvent]:
        if self._panel_pressed == button:
            self._panel_pressed = None
        mapping = self.profile.button_map(button)
        started = self._down_since.pop(button, now_s)
        long_armed = button in self._long_armed
        self._long_armed.discard(button)
        override = self._override_for(button)
        events: list[InputEvent] = []
        if button in self._panel_consume_release:
            self._panel_consume_release.discard(button)
            if button in self._active:
                events.extend(self._deactivate(button, fire_radial=False, now_s=now_s))
            return events
        if button in self._active:
            events.extend(self._deactivate(button, fire_radial=True, now_s=now_s))
        elif (
            override is None
            and mapping.mode == "short_long"
            and not long_armed
            and now_s - started < threshold
            and mapping.short.type == "keys"
            and mapping.short.is_active()
            and not (self._panel_button and button in self._panel_binds)
        ):
            events.extend(self._tap_keys(mapping.short.chord(), now_s))
        if (
            override is None
            and mapping.mode == "press"
            and mapping.release.type == "keys"
            and mapping.release.is_active()
            and not (self._panel_button and button in self._panel_binds)
        ):
            events.extend(self._tap_keys(mapping.release.chord(), now_s))
        return events

    def _activate(self, button: str, action: Action) -> list[InputEvent]:
        if action.type == "none" or (action.type != "modifier" and not action.is_active()):
            return []
        if action.type == "panel":
            if self._panel_button == button:
                self._close_panel()
                self._panel_consume_release.add(button)
                return []
            self._open_panel(button, action)
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
            if self._panel_button and button in self._panel_binds:
                continue
            if self._panel_button == button:
                continue
            if button in self._mod_order:
                continue
            desired = self._intended_action(button, pad)
            if desired.type == "panel":
                # Painel é sticky (abre/fecha só no edge), não no resync.
                continue
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
        if mapping.short.type in ("modifier", "radial", "panel"):
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

    def _open_panel(self, button: str, action: Action) -> None:
        items = action.active_panel_items()
        if not items:
            return
        if self._panel_button and self._panel_button != button:
            self._close_panel()
        binds: dict[str, RadialItem] = {}
        for pad_button, item in zip(
            (name for name in PANEL_BIND_ORDER if name != button),
            items,
            strict=False,
        ):
            binds[pad_button] = item
        self._panel_button = button
        self._panel_title = action.title.strip() or "Painel"
        self._panel_items = items
        self._panel_binds = binds
        self._panel_pressed = None

    def _close_panel(self) -> None:
        self._panel_button = None
        self._panel_title = ""
        self._panel_items = []
        self._panel_binds = {}
        self._panel_pressed = None

    def _panel_view(self, pad: PadState | None = None) -> PanelView:
        if not self._panel_button:
            return PanelView()
        from gw2controller.overlay.slot import overlay_button_label

        items: list[tuple[str, str, str]] = []
        for pad_button, item in self._panel_binds.items():
            items.append(
                (
                    overlay_button_label(pad_button),
                    item.display_label(),
                    keys_label_safe(item.keys),
                )
            )
        pressed = self._panel_pressed
        if pad is not None and pressed and not pad.buttons.get(pressed):
            pressed = None
        return PanelView(
            active=True,
            title=self._panel_title,
            items=items,
            owner=BUTTON_LABELS.get(self._panel_button, self._panel_button),
            pressed=overlay_button_label(pressed) if pressed else None,
        )

    def _layout_key(self) -> str:
        if not self._mod_order:
            return "default"
        # Usa só o modificador mais recente (evita chaves tipo LB+LT sem layout).
        return self._mod_order[-1]

    def _pressed_frames(self, pad: PadState, now_s: float) -> list[PressedFrame]:
        from gw2controller.overlay.slot import overlay_button_label

        pressed = [name for name in ALL_BUTTONS if pad.buttons.get(name)]
        if not pressed:
            return [PressedFrame("-")]

        threshold = max(0.08, self.profile.long_press_ms / 1000.0)
        mod_set = set(self._mod_order)
        non_mods = [name for name in pressed if name not in mod_set]
        frames: list[PressedFrame] = []
        used_mods: set[str] = set()

        for button in non_mods:
            mod = self._modifier_for_display(button)
            if mod:
                label = f"{overlay_button_label(mod)} + {overlay_button_label(button)}"
                used_mods.add(mod)
            else:
                label = overlay_button_label(button)
            progress, pending = self._long_progress(button, now_s, threshold)
            frames.append(PressedFrame(label, progress, pending))

        # Modificador sozinho (sem outro botão): mostra o mod.
        # Se há botão sem override, o mod não aparece — só o botão base.
        if not non_mods:
            for mod in self._mod_order:
                if mod in pressed:
                    frames.append(PressedFrame(overlay_button_label(mod), 1.0, False))

        return frames or [PressedFrame("-")]

    def _modifier_for_display(self, button: str) -> str | None:
        for mod in reversed(self._mod_order):
            if mod == button:
                continue
            action = self._active.get(mod)
            if action is None or action.type != "modifier":
                continue
            override = action.overrides.get(button)
            if override is not None and override.is_active():
                return mod
        return None

    def _long_progress(self, button: str, now_s: float, threshold: float) -> tuple[float, bool]:
        mapping = self.profile.button_map(button)
        if mapping.mode != "short_long":
            return 1.0, False
        if self._override_for(button) is not None:
            return 1.0, False
        if button in self._long_armed:
            return 1.0, False
        if mapping.short.type in ("modifier", "radial", "panel"):
            return 1.0, False
        started = self._down_since.get(button, now_s)
        progress = min(1.0, max(0.0, (now_s - started) / threshold))
        return progress, True

    def _runtime_label(self) -> str:
        from gw2controller.controller.xinput import BUTTON_LABELS as labels

        parts: list[str] = []
        if self._panel_button:
            parts.append(f"Painel {labels.get(self._panel_button, self._panel_button)}")
        if self._mod_order:
            parts.append("+".join(labels.get(name, name) for name in self._mod_order))
        if self._mumble.map_open:
            parts.append("Mapa")
        if self._mumble.textbox_focused:
            parts.append("Chat")
        if self._mumble.mounted:
            parts.append("Montaria")
        if self._input_blocked:
            parts.append("Bloqueado")
        return " · ".join(parts) if parts else "Padrão"

    def _captions(self) -> dict[str, str]:
        captions: dict[str, str] = {}
        for button in ALL_BUTTONS:
            if self._panel_button and button in self._panel_binds:
                captions[button] = self._panel_binds[button].display_label()
                continue
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
    if current.type == "panel":
        return (
            current.title.strip() == desired.title.strip()
            and current.active_panel_items() == desired.active_panel_items()
        )
    return True


def _down_event(key: str) -> InputEvent:
    if key.startswith("mouse_"):
        return InputEvent("mouse_down", mouse_button=key.removeprefix("mouse_"))
    return InputEvent("key_down", key=key)


def _up_event(key: str) -> InputEvent:
    if key.startswith("mouse_"):
        return InputEvent("mouse_up", mouse_button=key.removeprefix("mouse_"))
    return InputEvent("key_up", key=key)
