from __future__ import annotations

import json
from pathlib import Path

from macrocontroller.mapping.models import Action, ButtonMap, OverlayConfig, OverlaySlot, Profile, StickConfig
from macrocontroller.paths import PROFILES_DIR


def _keys(*names: str) -> Action:
    return Action(type="keys", keys=list(names))


def default_profile() -> Profile:
    buttons: dict[str, ButtonMap] = {
        "A": ButtonMap(mode="press", press=_keys("1")),
        "B": ButtonMap(mode="press", press=_keys("2")),
        "X": ButtonMap(mode="press", press=_keys("3")),
        "Y": ButtonMap(mode="press", press=_keys("4")),
        "LT": ButtonMap(mode="press", press=_keys("mouse_left")),
        "RT": ButtonMap(mode="press", press=_keys("mouse_right")),
        "LS": ButtonMap(mode="press", press=_keys("shift")),
        "RS": ButtonMap(mode="press", press=_keys("ctrl")),
        "DPAD_UP": ButtonMap(mode="press", press=_keys("f1")),
        "DPAD_DOWN": ButtonMap(mode="press", press=_keys("f2")),
        "DPAD_LEFT": ButtonMap(mode="press", press=_keys("f3")),
        "DPAD_RIGHT": ButtonMap(mode="press", press=_keys("f4")),
        "VIEW": ButtonMap(mode="press", press=_keys("tab")),
        "MENU": ButtonMap(mode="press", press=_keys("escape")),
        "LB": ButtonMap(
            mode="press",
            press=Action(
                type="modifier",
                overrides={
                    "A": _keys("5"),
                    "B": _keys("6"),
                    "X": _keys("7"),
                    "Y": _keys("8"),
                    "LT": _keys("q"),
                    "RT": _keys("e"),
                    "DPAD_UP": _keys("f5"),
                    "DPAD_DOWN": _keys("f6"),
                    "DPAD_LEFT": _keys("f7"),
                    "DPAD_RIGHT": _keys("f8"),
                },
            ),
        ),
        "RB": ButtonMap(
            mode="press",
            press=Action(
                type="modifier",
                overrides={
                    "A": _keys("9"),
                    "B": _keys("0"),
                    "X": _keys("r"),
                    "Y": _keys("f"),
                    "LT": _keys("t"),
                    "RT": _keys("g"),
                    "LS": _keys("space"),
                    "DPAD_UP": _keys("z"),
                    "DPAD_DOWN": _keys("x"),
                    "DPAD_LEFT": _keys("c"),
                    "DPAD_RIGHT": _keys("v"),
                },
            ),
        ),
    }
    return Profile(
        name="MMORPG Default",
        buttons=buttons,
        sticks={
            "left": StickConfig(mode="wasd", deadzone=0.2, sensitivity=1.0),
            "right": StickConfig(mode="mouse", deadzone=0.12, sensitivity=12.0),
        },
        overlay=__default_overlay(),
        trigger_threshold=0.5,
        long_press_ms=350,
        radial_deadzone=0.35,
    )


def __default_overlay() -> OverlayConfig:
    buttons = ["A", "B", "X", "Y", "LT", "RT", "DPAD_LEFT", "DPAD_RIGHT"]
    slots = []
    start_x = 720
    y = 980
    for index, button in enumerate(buttons):
        slots.append(
            OverlaySlot(
                id=f"slot{index + 1}",
                button=button,
                x=start_x + index * 56,
                y=y,
                size=44,
            )
        )
    return OverlayConfig(visible=True, slots=slots)


def ensure_profiles_dir() -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR


def default_profile_path() -> Path:
    return ensure_profiles_dir() / "mmorpg_default.json"


def load_profile(path: Path) -> Profile:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Profile.from_dict(data)


def save_profile(profile: Profile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def list_profiles(directory: Path | None = None) -> list[Path]:
    folder = directory or ensure_profiles_dir()
    if not folder.exists():
        return []
    return sorted(folder.glob("*.json"))


def load_or_create_default() -> tuple[Profile, Path]:
    path = default_profile_path()
    if path.exists():
        return load_profile(path), path
    profile = default_profile()
    save_profile(profile, path)
    return profile, path
