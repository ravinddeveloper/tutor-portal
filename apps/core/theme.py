"""
Runtime theme derivation for EduTutor Pro.

``ThemeSettings`` stores the raw hex values an administrator picked in the
Theme Customizer.  Hard-coding shades around those values (the pattern this
codebase used before) guarantees visual drift: the moment an admin picks a
different preset, hover states, focus rings, tinted backgrounds and shadows
keep pointing at the old brand colour.

This module derives a complete palette from the configured colours so every
surface stays coherent and contrast-safe regardless of the active preset.
All colour maths is done in sRGB with WCAG 2.x relative luminance.
"""

from __future__ import annotations

import re
from typing import Dict

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# Fallbacks mirror the "Modern Indigo" preset shipped with the product.
DEFAULT_PRIMARY = "#4f46e5"
DEFAULT_SECONDARY = "#06b6d4"
DEFAULT_ACCENT = "#f59e0b"
DEFAULT_BACKGROUND = "#f8fafc"
DEFAULT_SURFACE = "#ffffff"
DEFAULT_TEXT = "#0f172a"
DEFAULT_BORDER = "#e2e8f0"
DEFAULT_RADIUS = "0.75rem"

# Fixed semantic colours (WCAG AA compliant on white / slate surfaces).
SUCCESS = "#059669"
WARNING = "#d97706"
DANGER = "#dc2626"
INFO = "#2563eb"

INK_DARK = "#0f172a"      # slate-900
INK_LIGHT = "#ffffff"


# ── Colour primitives ──────────────────────────────────────────────────────

def normalize_hex(value: str, fallback: str) -> str:
    """Return a lowercase ``#rrggbb`` string, or *fallback* when unparseable."""
    if not value:
        return fallback
    match = _HEX_RE.match(str(value).strip())
    if not match:
        return fallback
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(char * 2 for char in digits)
    return "#" + digits.lower()


def hex_to_rgb(color: str) -> tuple:
    digits = color.lstrip("#")
    return tuple(int(digits[index:index + 2], 16) for index in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(
        max(0, min(255, int(round(channel)))) for channel in rgb
    )


def mix(color_a: str, color_b: str, weight: float) -> str:
    """Blend *color_a* toward *color_b*; ``weight`` 0 keeps A, 1 yields B."""
    rgb_a, rgb_b = hex_to_rgb(color_a), hex_to_rgb(color_b)
    return rgb_to_hex(
        rgb_a[index] + (rgb_b[index] - rgb_a[index]) * weight
        for index in range(3)
    )


def lighten(color: str, weight: float) -> str:
    return mix(color, INK_LIGHT, weight)


def darken(color: str, weight: float) -> str:
    return mix(color, "#000000", weight)


def rgba(color: str, alpha: float) -> str:
    red, green, blue = hex_to_rgb(color)
    return f"rgba({red}, {green}, {blue}, {round(alpha, 4)})"


def _channel_luminance(channel: int) -> float:
    value = channel / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    red, green, blue = hex_to_rgb(color)
    return (
        0.2126 * _channel_luminance(red)
        + 0.7152 * _channel_luminance(green)
        + 0.0722 * _channel_luminance(blue)
    )


def contrast_ratio(color_a: str, color_b: str) -> float:
    luminance_a = relative_luminance(color_a)
    luminance_b = relative_luminance(color_b)
    if luminance_a < luminance_b:
        luminance_a, luminance_b = luminance_b, luminance_a
    return (luminance_a + 0.05) / (luminance_b + 0.05)


def readable_on(background: str) -> str:
    """Return the foreground colour with the best contrast on *background*."""
    return (
        INK_LIGHT
        if contrast_ratio(background, INK_LIGHT) >= contrast_ratio(background, INK_DARK)
        else INK_DARK
    )


# ── Palette assembly ───────────────────────────────────────────────────────

def _brand_scale(color: str) -> Dict[str, str]:
    """Derive the full shade ramp for one brand colour."""
    return {
        "base": color,
        "hover": darken(color, 0.10),
        "active": darken(color, 0.18),
        "soft": rgba(color, 0.10),
        "softer": rgba(color, 0.06),
        "border": rgba(color, 0.25),
        "ring": rgba(color, 0.38),
        "on": readable_on(color),
    }


def build_theme_tokens(theme) -> Dict[str, str]:
    """
    Build the full CSS custom-property map for a :root block.

    Every value is derived, never hard-coded, so switching the Theme
    Customizer preset re-skins the whole product coherently.
    """
    primary = normalize_hex(getattr(theme, "primary_color", ""), DEFAULT_PRIMARY)
    secondary = normalize_hex(getattr(theme, "secondary_color", ""), DEFAULT_SECONDARY)
    accent = normalize_hex(getattr(theme, "accent_color", ""), DEFAULT_ACCENT)
    background = normalize_hex(getattr(theme, "background_color", ""), DEFAULT_BACKGROUND)
    surface = normalize_hex(getattr(theme, "surface_color", ""), DEFAULT_SURFACE)
    text = normalize_hex(getattr(theme, "text_color", ""), DEFAULT_TEXT)
    radius = (getattr(theme, "border_radius", "") or DEFAULT_RADIUS).strip()

    primary_scale = _brand_scale(primary)
    secondary_scale = _brand_scale(secondary)
    accent_scale = _brand_scale(accent)

    # Surfaces derived from the configured canvas colour.
    surface_hover = mix(background, "#0f172a", 0.05)
    surface_subtle = mix(background, "#0f172a", 0.03)
    border = mix(background, "#0f172a", 0.11)
    border_strong = mix(background, "#0f172a", 0.20)

    # Muted text must clear 4.5:1 against the canvas.
    text_muted = mix(text, background, 0.42)
    while contrast_ratio(text_muted, background) < 4.5:
        text_muted = mix(text_muted, text, 0.12)

    text_subtle = mix(text, background, 0.22)
    while contrast_ratio(text_subtle, background) < 3.0:
        text_subtle = mix(text_subtle, text, 0.15)

    return {
        # Brand ramps
        "primary": primary_scale["base"],
        "primary-hover": primary_scale["hover"],
        "primary-active": primary_scale["active"],
        "primary-soft": primary_scale["soft"],
        "primary-softer": primary_scale["softer"],
        "primary-border": primary_scale["border"],
        "primary-ring": primary_scale["ring"],
        "on-primary": primary_scale["on"],
        "secondary": secondary_scale["base"],
        "secondary-hover": secondary_scale["hover"],
        "secondary-active": secondary_scale["active"],
        "secondary-soft": secondary_scale["soft"],
        "secondary-softer": secondary_scale["softer"],
        "secondary-border": secondary_scale["border"],
        "secondary-ring": secondary_scale["ring"],
        "on-secondary": secondary_scale["on"],
        "accent": accent_scale["base"],
        "accent-hover": accent_scale["hover"],
        "accent-active": accent_scale["active"],
        "accent-soft": accent_scale["soft"],
        "accent-softer": accent_scale["softer"],
        "accent-border": accent_scale["border"],
        "on-accent": accent_scale["on"],
        # Canvas & surfaces
        "background": background,
        "surface": surface,
        "surface-hover": surface_hover,
        "surface-subtle": surface_subtle,
        "surface-raised": surface,
        # Ink
        "text": text,
        "text-muted": text_muted,
        "text-subtle": text_subtle,
        # Lines
        "border": border,
        "border-strong": border_strong,
        # Semantics
        "success": SUCCESS,
        "success-soft": rgba(SUCCESS, 0.10),
        "on-success": readable_on(SUCCESS),
        "warning": WARNING,
        "warning-soft": rgba(WARNING, 0.10),
        "on-warning": readable_on(WARNING),
        "danger": DANGER,
        "danger-soft": rgba(DANGER, 0.10),
        "on-danger": readable_on(DANGER),
        "info": INFO,
        "info-soft": rgba(INFO, 0.10),
        "on-info": readable_on(INFO),
        # Geometry
        "border-radius": radius,
    }


def theme_css(theme) -> str:
    """Render the derived palette as an inline ``:root { ... }`` block."""
    tokens = build_theme_tokens(theme)
    lines = [f"  --{name}: {value};" for name, value in tokens.items()]
    return ":root {\n" + "\n".join(lines) + "\n}"
