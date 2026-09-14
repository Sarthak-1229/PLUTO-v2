---
name: Celestial Glass Workspace
colors:
  surface: '#faf9f7'
  surface-dim: '#dbdad8'
  surface-bright: '#faf9f7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3f1'
  surface-container: '#efeeec'
  surface-container-high: '#e9e8e6'
  surface-container-highest: '#e3e2e0'
  on-surface: '#1a1c1b'
  on-surface-variant: '#55433d'
  inverse-surface: '#2f3130'
  inverse-on-surface: '#f1f1ef'
  outline: '#88726c'
  outline-variant: '#dbc1b9'
  surface-tint: '#99462a'
  primary: '#99462a'
  on-primary: '#ffffff'
  primary-container: '#d97757'
  on-primary-container: '#541400'
  inverse-primary: '#ffb59e'
  secondary: '#535f6f'
  on-secondary: '#ffffff'
  secondary-container: '#d4e1f4'
  on-secondary-container: '#576474'
  tertiary: '#3d608a'
  on-tertiary: '#ffffff'
  tertiary-container: '#7194c0'
  on-tertiary-container: '#002c50'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59e'
  on-primary-fixed: '#390b00'
  on-primary-fixed-variant: '#7a2f15'
  secondary-fixed: '#d7e3f6'
  secondary-fixed-dim: '#bbc7da'
  on-secondary-fixed: '#101c2a'
  on-secondary-fixed-variant: '#3c4857'
  tertiary-fixed: '#d2e4ff'
  tertiary-fixed-dim: '#a6c9f8'
  on-tertiary-fixed: '#001c37'
  on-tertiary-fixed-variant: '#234970'
  background: '#faf9f7'
  on-background: '#1a1c1b'
  surface-variant: '#e3e2e0'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 44px
    fontWeight: '700'
    lineHeight: 52px
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 14px
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  gutter: 1.25rem
  margin: 1.75rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.25rem
---

## Brand & Style

This design system establishes an intelligent, tranquil, and tactile workspace for human-agent collaboration. It merges Apple-caliber clarity and Human Interface ergonomics with Stitch-inspired translucent glass materials, tempered by an organic celestial warmth. 

The aesthetic sits at the intersection of **Glassmorphism**, **Modern Minimalism**, and **Tactile Precision**:
- **Frosted Translucency:** Floating glass planes, layered depth, and dynamic backdrop filters convey weightless digital organization without visual clutter.
- **Planetary Warmth:** Subtle terracotta-peach highlights bring approachability and life to quiet slate-gray surfaces, steering the agent experience away from clinical detachment toward thoughtful companionship.
- **Precision Micro-Surfaces:** Silky pill navigation, ultra-fine boundary borders, and soft fluid transitions yield a tactile, responsive digital tool tailored for power users, researchers, and creators.

## Colors

The palette balances planetary warmth with deep cosmic slates, framed against airy, luminous canvas tones:

- **Primary (`#D97757` — Terracotta Peach):** Represents human warmth, agency, active execution, and primary user-driven intentions.
- **Secondary (`#1E2A38` — Cosmic Slate):** Provides high-contrast anchor weights, structured chrome elements, and primary typography.
- **Tertiary (`#5E81AC` — Atmospheric Frost Blue):** Accents ambient status, assistant feedback loops, telemetry, and secondary data visualizations.
- **Neutral (`#F7F6F4` — Lunar Mist Base):** A soft, low-glare foundation that allows frosted card overlays (`rgba(255, 255, 255, 0.72)`) and light ambient diffusion to shine through.

### Functional Color Applications
- **Translucent Glass Surface:** `rgba(255, 255, 255, 0.68)` backed by `backdrop-filter: blur(24px) saturate(160%)`.
- **Card Edge & Rim Glow:** `rgba(255, 255, 255, 0.85)` at top/left, fading to `rgba(220, 225, 230, 0.35)` on bottom/right.
- **Subtle Cosmic Border:** `rgba(30, 42, 56, 0.06)` for gentle division on non-blurred layers.
- **Agent Focus Ring:** `rgba(217, 119, 87, 0.28)` layered over a 1px solid terracotta stroke.

## Typography

The typography leverages **Plus Jakarta Sans** uniformly across display, body, and label roles. Its geometric architecture, generous x-height, and subtly rounded terminals strike the exact balance between Apple-like systematic order and inviting, friendly clarity.

### Usage Rules
- **Display & Headlines:** Set tight line heights with negative letter-tracking (`-0.02em` on sizes $\ge 22\text{px}$) to present a crisp, editorial finish on floating translucent surfaces.
- **Body & Dialogue:** Maintain open tracking and consistent vertical rhythms to guarantee high legibility when rendering AI agent reasoning strings, code blocks, and conversation streams.
- **Labels & Micro-Tags:** Render timestamps, agent status indicators, and pill tags in `label-sm` or `label-md` with semi-bold weights (`600` or `500`) and slight positive letter spacing (`+0.01em`) for immediate scannability.

## Layout & Spacing

The workspace uses a composite **Fluid Modular Grid** configured around adaptive screen real estate:

- **Desktop & Wide Displays:** 12-column grid with `1.25rem` (20px) gutters and a flexible page margin constrained between `1.75rem` and `3.5rem`. Side-panels (e.g., persistent agent stream or active canvas) lock to 3 or 4 columns, while dynamic workspace canvases span the remainder.
- **Tablet (768px – 1024px):** 8-column layout; auxiliary panels collapse into sliding frosted drawers or bottom sheets.
- **Mobile (< 768px):** 4-column fluid structure with strict `1rem` margins and `0.75rem` gutters. Primary views emphasize full-width floating cards with a floating bottom pill navigation dock.

### Spatial Rhythm
Internal component padding adheres strictly to a harmonious 4px/8px incremental scale:
- Inner card padding: `space-lg` (24px) for desktop; `space-md` (16px) for compact views.
- Grouping intervals between related input fields or list elements: `space-sm` (8px).
- Section breaks across multi-agent workflows: `space-xl` (36px).

## Elevation & Depth

Visual hierarchy is articulated through stacked frosted glass surfaces, inner specular rim highlights, and ambient cosmic-tinted shadows:

- **Base Canvas (Level 0):** Flat `#F7F6F4` neutral surface, occasionally infused with extremely soft, low-saturation radial glows of Terracotta Peach and Celestial Frost Blue.
- **Floated Container Glass (Level 1):** Semi-opaque background (`rgba(255, 255, 255, 0.68)`) with `backdrop-filter: blur(20px)`, framed by a 1px composite outline (`rgba(255, 255, 255, 0.8)` top border and `rgba(30, 42, 56, 0.05)` base border). Shadow: `0 8px 32px -4px rgba(30, 42, 56, 0.06), 0 2px 6px -1px rgba(30, 42, 56, 0.03)`.
- **Interactive Glass & Hovered Cards (Level 2):** Elevated opacity (`rgba(255, 255, 255, 0.85)`), blur raised to `28px`, shadow expanding to `0 16px 40px -6px rgba(30, 42, 56, 0.09)`.
- **Modals, Floating Toolbars & Agent Pockets (Level 3):** Crisp, dense glass (`rgba(255, 255, 255, 0.92)`), intense rim highlight, accompanied by a layered shadow: `0 24px 48px -12px rgba(30, 42, 56, 0.14)`.

## Shapes

The design system employs a **Pill-shaped (Level 3)** form factor across controls and dynamic interfaces, infusing the software with physical smoothness:

- **Primary Actions & Navigational Docks:** Fully pill-shaped (`border-radius: 9999px`) to create effortless visual anchoring and comfortable gesture hit targets.
- **Content Cards & Agent Blocks:** Large organic radiuses (`rounded-xl` / 24px to 32px) evoking modern iOS hardware and floating glass panels.
- **Form Elements & Secondary Inputs:** Generous corner geometry (`rounded-lg` / 16px) that feels tactile, smooth, and friendly to direct manipulation.

## Components

### Buttons
- **Primary:** Filled Cosmic Slate (`#1E2A38`) or Terracotta Peach (`#D97757`) with pure white typography, full pill radius (`9999px`), 12px 24px padding, and an ultra-subtle inset top highlight (`inset 0 1px 0 rgba(255, 255, 255, 0.25)`). Transitions scale subtly (`transform: scale(0.98)`) on active tap.
- **Glass / Secondary:** Semi-translucent white (`rgba(255, 255, 255, 0.7)`), 1px border (`rgba(255, 255, 255, 0.9)`), Cosmic Slate text. Hover yields gentle terracotta text transitions.
- **Ghost:** Pure background with hover state revealing `rgba(217, 119, 87, 0.08)`.

### Floating Navigation Pill
- Autonomous bottom dock or pinned top rail with `backdrop-filter: blur(24px)`.
- Active segment marked by a smooth, spring-animated dark slate capsule with white icon/text, surrounded by soft inactive frosted icons that elevate on cursor proximity.

### Cards & Agent Workspace Panels
- Crisp white frosted background (`rgba(255, 255, 255, 0.7)`) with dual-tone directional borders to emulate light hitting genuine frosted glassware.
- Header zones integrate status badges (e.g., "Agent Thinking", "Synced") styled as soft micro-pills with glowing status dots.

### Chips & Filters
- Compact pill silhouettes (`border-radius: 9999px`), `0.25rem 0.75rem` padding.
- Unselected: White glass tint with subtle slate outline.
- Selected: Gentle terracotta wash (`rgba(217, 119, 87, 0.12)`) with deep terracotta text and crisp border.

### Input Fields & Search Bars
- Recessed pill or 16px rounded enclosures with interior translucency (`rgba(255, 255, 255, 0.5)`).
- On focus: Background deepens to crisp white, border illuminates with a 1px Terracotta Peach rim accompanied by a diffused outer ring (`0 0 0 3px rgba(217, 119, 87, 0.15)`).

### Selection Controls (Checkboxes & Radios)
- Smooth rounded squares (8px radius) and concentric circles.
- Checked state fills with Terracotta Peach displaying a smooth spring checkmark animation.

### Agent Prompt Bar
- Multi-state pill input featuring a voice waveform trigger, inline attachment chip preview, and a circular send/pause action button with cosmic glow feedback.