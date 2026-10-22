# EduTutor Pro — Design System Specification

## Visual Direction: Modern Academy SaaS
EduTutor Pro adopts a distinctive, refined SaaS aesthetic built for focus, trust, and velocity. It eschews superficial AI-generated decorations (loud multi-color gradients, neon glow halos, gratuitous glassmorphism, noisy eyebrows) in favor of high-craft typographical balance, structured data density, intentional whitespace, and layered depth.

## Design Tokens

### 1. Typography
- **Headings & Brand**: `Plus Jakarta Sans`, sans-serif (weights: 600, 700, 800).
- **Body & Controls**: `Inter`, -apple-system, BlinkMacSystemFont, sans-serif (weights: 400, 500, 600).
- **Tabular Figures**: `font-variant-numeric: tabular-nums;` on all statistics, currencies, ratings, and time stamps.
- **Letter Spacing**: Display headings (`-0.025em`), labels/subtitles (`0.01em`), badges (`0.04em`).

### 2. Color Palette
- **Light Theme**:
  - Canvas / Background: `#f8fafc` (Slate 50)
  - Surface Card: `#ffffff`
  - Surface Subdued: `#f1f5f9` (Slate 100)
  - Surface Hover: `#e2e8f0` (Slate 200)
  - Text Primary: `#0f172a` (Slate 900)
  - Text Secondary: `#475569` (Slate 600)
  - Text Muted: `#64748b` (Slate 500)
  - Border: `#e2e8f0` (Slate 200)
  - Border Strong: `#cbd5e1` (Slate 300)
- **Dark Theme (Educational Slate)**:
  - Canvas / Background: `#0b1120` (Deep Slate)
  - Surface Card: `#131d33`
  - Surface Subdued: `#1a2642`
  - Surface Hover: `#223154`
  - Text Primary: `#f8fafc` (Slate 50)
  - Text Secondary: `#cbd5e1` (Slate 300)
  - Text Muted: `#94a3b8` (Slate 400)
  - Border: `#1e2d4d`
  - Border Strong: `#2d3f66`
- **Brand & Semantic Accents**:
  - Primary: `#2563eb` (Royal Blue) / Hover `#1d4ed8` / Light Tint `rgba(37, 99, 235, 0.08)`
  - Secondary: `#0f766e` (Deep Teal) / `#0d9488`
  - Accent / Star: `#f59e0b` (Amber)
  - Success: `#059669` (Emerald) / Light `rgba(5, 150, 105, 0.08)`
  - Warning: `#d97706` (Amber 600) / Light `rgba(217, 119, 6, 0.08)`
  - Danger: `#dc2626` (Red 600) / Light `rgba(220, 38, 38, 0.08)`

### 3. Layered Shadows
- `var(--shadow-xs)`: `0 1px 2px rgba(15, 23, 42, 0.04)`
- `var(--shadow-sm)`: `0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)`
- `var(--shadow-md)`: `0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.04)`
- `var(--shadow-lg)`: `0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04)`
- `var(--shadow-xl)`: `0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.04)`

### 4. Craft Floor Guidelines
- High text contrast (body >= 4.5:1, large >= 3:1).
- Accessible focus rings: `outline: 2px solid var(--primary); outline-offset: 2px;`.
- No kicker / eyebrow above headings.
- Clean vector SVG icons via Lucide (consistent 16px/18px stroke weight).
- No pseudo-glass decorations or blurry glow halos.
- Clear empty states with dedicated icons, descriptive headers, and unambiguous primary action buttons.
- Fully responsive across mobile (<640px), tablet (640-1024px), and desktop (>1024px).
