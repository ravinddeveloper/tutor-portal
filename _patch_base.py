"""
One-off migration: replace hard-coded brand hex colours with design tokens.

Completes the rgba() migration in the same vein — the product previously
mixed raw brand hexes with the token palette, so a Theme Customizer change
never reached every surface.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {"venv", ".git", "staticfiles", "media", "__pycache__"}
# Email templates are rendered by mail clients that do not support CSS
# custom properties, so they keep literal hex values.
SKIP_FILES = {
    os.path.join("templates", "emails", "welcome_email.html"),
    os.path.join("templates", "emails", "payment_receipt_email.html"),
    os.path.join("static", "css", "design-system.css"),
}

HEX_MAP = {
    # Success / emerald
    "#10b981": "var(--success)",
    "#059669": "var(--success)",
    "#34d399": "var(--success)",
    # Accent / amber + orange
    "#f59e0b": "var(--accent)",
    "#d97706": "var(--accent-hover)",
    "#ea580c": "var(--accent-hover)",
    "#c2410c": "var(--accent-active)",
    # Secondary / cyan
    "#06b6d4": "var(--secondary)",
    "#0891b2": "var(--secondary-hover)",
    "#0e7490": "var(--secondary-active)",
    # Primary / indigo + blue
    "#4f46e5": "var(--primary)",
    "#4338ca": "var(--primary-active)",
    "#3730a3": "var(--primary-active)",
    "#6366f1": "var(--primary)",
    "#1e40af": "var(--primary)",
    "#1e3a8a": "var(--primary-active)",
    # Danger / red
    "#ef4444": "var(--danger)",
    "#dc2626": "var(--danger)",
    "#b91c1c": "var(--danger)",
    # Deep ink used as a gradient terminus
    "#1e1b4b": "var(--primary-active)",
}

HEX_RE = re.compile(
    r"#(?:10b981|059669|34d399|f59e0b|d97706|ea580c|c2410c|06b6d4|0891b2|"
    r"0e7490|4f46e5|4338ca|3730a3|6366f1|1e40af|1e3a8a|ef4444|dc2626|"
    r"dc2626|b91c1c|1e1b4b)\b",
    re.IGNORECASE,
)


def convert(match):
    return HEX_MAP[match.group(0).lower()]


def main():
    changed_files = 0
    changed_values = 0

    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith((".html", ".css")):
                continue
            path = os.path.join(base, name)
            relative = os.path.relpath(path, ROOT)
            if relative in SKIP_FILES:
                continue

            with io.open(path, encoding="utf-8") as handle:
                original = handle.read()
            if "#" not in original:
                continue

            updated, count = HEX_RE.subn(convert, original)
            if count and updated != original:
                with io.open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(updated)
                changed_files += 1
                changed_values += count
                print("%-52s %d" % (relative, count))

    print("\n%d files updated, %d hex literals tokenised." % (changed_files, changed_values))


if __name__ == "__main__":
    main()
