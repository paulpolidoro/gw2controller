from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class OverlayTheme:
    name: str
    glyph_bg: QColor
    glyph_fg: QColor
    glyph_border: QColor
    stick_inner: QColor
    caption_bg: QColor
    caption_fg: QColor
    caption_border: QColor
    edit_fill: QColor
    edit_border: QColor
    veil: QColor
    banner_qss: str
    radial_slice: QColor
    radial_slice_selected: QColor
    radial_text: QColor
    radial_text_selected: QColor
    radial_center: QColor
    radial_center_text: QColor
    radial_ring: QColor


DARK = OverlayTheme(
    name="dark",
    glyph_bg=QColor(18, 20, 26, 230),
    glyph_fg=QColor("#F4F6FB"),
    glyph_border=QColor(255, 255, 255, 40),
    stick_inner=QColor("#4B5568"),
    caption_bg=QColor(12, 16, 24, 220),
    caption_fg=QColor("#F4F6FB"),
    caption_border=QColor(255, 255, 255, 35),
    edit_fill=QColor(12, 16, 24, 90),
    edit_border=QColor("#60A5FA"),
    veil=QColor(10, 14, 22, 55),
    banner_qss=(
        "QLabel { background: rgba(12, 16, 24, 220); color: #F4F6FB; padding: 10px 18px; "
        "border-radius: 10px; font: 600 13px 'Segoe UI'; border: 1px solid #3A4458; }"
    ),
    radial_slice=QColor(20, 24, 34, 230),
    radial_slice_selected=QColor(37, 99, 235, 230),
    radial_text=QColor("#E8EAED"),
    radial_text_selected=QColor("#FFFFFF"),
    radial_center=QColor(12, 16, 24, 240),
    radial_center_text=QColor("#9AA3B5"),
    radial_ring=QColor("#3D8BFD"),
)

LIGHT = OverlayTheme(
    name="light",
    glyph_bg=QColor(255, 255, 255, 230),
    glyph_fg=QColor("#111827"),
    glyph_border=QColor(17, 24, 39, 50),
    stick_inner=QColor("#9CA3AF"),
    caption_bg=QColor(255, 255, 255, 230),
    caption_fg=QColor("#111827"),
    caption_border=QColor(17, 24, 39, 40),
    edit_fill=QColor(255, 255, 255, 140),
    edit_border=QColor("#2563EB"),
    veil=QColor(255, 255, 255, 40),
    banner_qss=(
        "QLabel { background: rgba(255, 255, 255, 230); color: #111827; padding: 10px 18px; "
        "border-radius: 10px; font: 600 13px 'Segoe UI'; border: 1px solid #C5CEDA; }"
    ),
    radial_slice=QColor(255, 255, 255, 230),
    radial_slice_selected=QColor(37, 99, 235, 230),
    radial_text=QColor("#111827"),
    radial_text_selected=QColor("#FFFFFF"),
    radial_center=QColor("#FFFFFF"),
    radial_center_text=QColor("#4B5563"),
    radial_ring=QColor("#2563EB"),
)


def overlay_theme(name: str | None) -> OverlayTheme:
    return LIGHT if str(name or "").lower() == "light" else DARK
