# MCP Anywhere Design System

A single source of truth for the MCP Anywhere landing page and documentation. Use this for future tasks, redesigns, or new pages.

---

## 1. Overview

- **Theme**: Light, premium SaaS
- **Vibe**: Clean, conversion-focused, generous spacing, modern typography
- **Primary accent**: Lime green (`#74D14C`)
- **Stack**: React + TypeScript, CSS variables, utility classes (no Tailwind—custom in `globals.css`)

---

## 2. Color Palette

### Neutral (grays)
| Token | Hex | Usage |
|-------|-----|--------|
| `--color-neutral-0` | `#FFFFFF` | Pure white |
| `--color-neutral-50` | `#F8FAFC` | Lightest gray |
| `--color-neutral-100` | `#F1F5F9` | Light gray |
| `--color-neutral-200` | `#E2E8F0` | Borders, dividers |
| `--color-neutral-400` | `#94A3B8` | Muted text |
| `--color-neutral-500` | `#64748B` | Secondary text |
| `--color-neutral-600` | `#475569` | Body text (secondary) |
| `--color-neutral-900` | `#0F172A` | Headings, primary text |
| `--color-neutral-950` | `#020617` | Darkest |

### Brand (lime green)
| Token | Hex | Usage |
|-------|-----|--------|
| `--color-brand-50` | `#F1FDF0` | Light tint backgrounds |
| `--color-brand-100` | `#DCFCE7` | Badge, hover backgrounds |
| `--color-brand-200` | `#BBF7D0` | Borders, glows |
| `--color-brand-500` | `#74D14C` | **Primary** (buttons, links, highlights) |
| `--color-brand-600` | `#16A34A` | Hover state |
| `--color-brand-700` | `#15803D` | Active / pressed |
| `--color-brand-800` | `#166534` | Badge text |

### Semantic (use these in components)
| Token | Maps to | Usage |
|-------|---------|--------|
| `--bg-canvas` | `#FFFFFF` | Page background |
| `--bg-surface` | `#F8F9FA` | Section backgrounds (alternating) |
| `--bg-surface-hover` | `#F1F3F5` | Hover states |
| `--bg-card` | `#FFFFFF` | Card background |
| `--text-primary` | `#1A1A1A` | Headings, primary text |
| `--text-secondary` | `#4B5563` | Body, descriptions |
| `--text-muted` | `#9CA3AF` | Captions, labels |
| `--border-default` | `#E5E7EB` | Default borders |
| `--border-highlight` | `#D1D5DB` | Hover borders |
| `--brand-primary` | `--color-brand-500` | CTAs, links |
| `--brand-hover` | `--color-brand-600` | Link/button hover |

---

## 3. Typography

| Token | Value | Usage |
|-------|--------|--------|
| `--font-sans` | `'Inter', system-ui, -apple-system, sans-serif` | Body, UI |
| `--font-mono` | `'JetBrains Mono', 'Fira Code', monospace` | Code |

### Scale (use CSS classes or tokens)
- **xs**: 0.75rem (12px) — labels, badges
- **sm**: 0.875rem (14px) — captions, small copy
- **base**: 1rem (16px) — body
- **lg**: 1.125rem (18px) — lead, subheads
- **xl**: 1.25rem (20px) — section intros
- **2xl**: 1.5rem (24px) — H3
- **3xl**: 1.875rem (30px) — H2
- **4xl**: 2.25rem (36px) — H1 section
- **5xl**: 3rem (48px) — Hero H1
- **6xl**: 3.75rem (60px) — Hero large

### Weights
- **400** — body
- **500** — medium (links, labels)
- **600** — semibold (buttons, subheads)
- **700** — bold (headings)

### Conventions
- Headings: `letter-spacing: -0.02em`, `line-height: 1.1`
- Body: `line-height: 1.6`
- Section titles: bold, clear hierarchy (H1 → H2 → H3)

---

## 4. Spacing

Base unit: **4px**. Scale in `tokens.css`:

| Token | Value | Usage |
|-------|--------|--------|
| `--space-1` | 4px | Tight gaps |
| `--space-2` | 8px | Icon–text gap |
| `--space-4` | 16px | Inline padding |
| `--space-6` | 24px | Card padding, container padding |
| `--space-8` | 32px | Between elements |
| `--space-12` | 48px | Section internal gap |
| `--space-16` | 64px | Large gap |
| `--space-20` | 80px | **Section vertical padding** (py) |
| `--space-24` | 96px | Extra-large sections |

**Guideline**: Use generous vertical rhythm (e.g. `py-20` or `py-24` for sections).

---

## 5. Radius & Shadows

### Radius
| Token | Value | Usage |
|-------|--------|--------|
| `--radius-sm` | 0.25rem | Code, small elements |
| `--radius-md` | 0.5rem | Inputs |
| `--radius-lg` | 0.75rem | Code blocks |
| `--radius-xl` | 1rem | Cards |
| `--radius-2xl` | 1.5rem | Large cards |
| `--radius-3xl` | 2rem | Hero visual |
| `--radius-full` | 9999px | Buttons, badges, pills |

### Shadows
| Token | Usage |
|-------|--------|
| `--shadow-sm` | Subtle elevation |
| `--shadow-md` | Buttons |
| `--shadow-lg` | Cards hover |
| `--shadow-xl` | Modals, raised cards |
| `--shadow-card` | Default card |
| `--shadow-glow` | Brand glow (optional) |

---

## 6. Motion

| Token | Value | Usage |
|-------|--------|--------|
| `--duration-fast` | 150ms | Micro-interactions |
| `--duration-normal` | 250ms | Hover, focus |
| `--duration-slow` | 400ms | Accordion, modals |
| `--easing-ease-out` | cubic-bezier(0, 0, 0.2, 1) | Default transition |
| `--easing-ease-in-out` | cubic-bezier(0.4, 0, 0.2, 1) | Expand/collapse |

**Guideline**: Prefer CSS transitions; avoid heavy animation libraries. Respect `prefers-reduced-motion` where applicable.

---

## 7. Layout Primitives

### Container
- **Class**: `.container` (from `components.css`)
- **Max width**: 1280px
- **Padding**: `0 var(--space-6)` (24px horizontal)
- **Usage**: Wrap all main content; center on page.

### Section
- **Class**: `.section` (from `components.css`)
- **Padding**: `var(--space-20) 0` (80px vertical)
- **Alt**: `.section-alt` for `--bg-surface` (alternating background)

---

## 8. Components

### Button (`src/components/Button.tsx`)
- **Variants**: `primary` (green solid), `secondary` (surface), `outline` (border only)
- **Sizes**: `sm`, `md`, `lg`
- **Classes**: `btn btn-primary btn-lg` (etc.) — see `components.css`
- **Primary button**: Green background, **black text** for contrast on lime.
- **Hover**: Slight lift (`translateY(-2px)`), stronger shadow.

### Card (`src/components/Card.tsx`)
- **Class**: `card` (+ optional utility classes)
- **Style**: White background, `--border-default`, `--radius-xl`, padding `--space-6`
- **Hover**: `translateY(-4px)`, `--shadow-xl`, border highlight

### Badge (`src/components/Badge.tsx`)
- **Variants**: `badge-brand` (green tint), `badge-neutral` (gray)
- **Style**: Pill (`--radius-full`), small uppercase text, padding 4px 12px

### CodeBlock (`src/components/CodeBlock.tsx`)
- **Style**: Dark background (`#1a1a1a`), mono font, rounded-lg, copy button in header
- **Usage**: Code snippets on docs/landing (e.g. QuickStart, Getting Started, Deployment)

### Section (`src/components/Section.tsx`)
- Wrapper for page sections; applies `.section` and optional `className` / `id`.

### Container (`src/components/Container.tsx`)
- Wrapper for `.container`; use for consistent max-width and padding.

---

## 9. Utility Classes (`globals.css`)

The project uses **custom utility classes** (no Tailwind). Key groups:

- **Layout**: `.flex`, `.grid`, `.flex-col`, `.items-center`, `.justify-between`, `.gap-4`, `.gap-8`, etc.
- **Spacing**: `.p-4`, `.py-6`, `.mb-6`, `.mt-8`, `.mx-auto`, etc.
- **Sizing**: `.w-full`, `.max-w-2xl`, `.max-w-4xl`, `.h-8`, etc.
- **Typography**: `.text-sm`, `.text-lg`, `.font-bold`, `.text-neutral-600`, `.text-brand-500`, etc.
- **Colors**: `.bg-white`, `.bg-neutral-50`, `.bg-brand-500`, `.text-neutral-900`, `.border-neutral-200`, etc.
- **Effects**: `.rounded-xl`, `.shadow-lg`, `.transition-all`, `.duration-300`
- **Responsive**: `.md:flex`, `.md:grid-cols-2`, `.md:text-left`, `.lg:grid-cols-3`, etc. (768px, 1024px breakpoints)

**Important**: When adding new UI, use existing utility class names from `globals.css`. If you need a new one, add it there so the design stays consistent.

---

## 10. Page Structure & Patterns

### Landing page sections (order)
1. Hero (value prop + primary CTA)
2. Social proof (trust strip)
3. How it works (3 steps)
4. Features (grid of cards)
5. Security (trust copy + visual)
6. Integrations (logos / tools)
7. Quick start (code snippet, dark strip)
8. FAQ (accordion)
9. Final CTA

### Content pages (Getting Started, Deployment)
- **Top**: Page title + short description in a light strip (`bg-neutral-50`, `border-b`)
- **Body**: `Container` + `max-w-4xl` prose-style content; use `CodeBlock` for snippets and `Section` for major blocks.
- **Headings**: H1 page title, H2 for main sections, H3 for subsections; maintain hierarchy.

### Header
- **Sticky**, transparent until scroll then `bg-white-90` + backdrop blur.
- **Nav**: Mix of in-page anchors (Features, How it works, Security) and routes (Getting Started, Deployment).
- **CTA**: “Get Started” scrolls to `#get-started` or navigates home then scrolls.

### Footer
- **Background**: `--bg-surface` or `neutral-50`
- **Content**: Logo, short description, Quick links, Resources, copyright, GitHub link.
- **Style**: Neutral text, brand color on hover for links.

---

## 11. Accessibility & SEO

- **Headings**: Single H1 per page; logical order (H1 → H2 → H3).
- **Focus**: Visible focus states on interactive elements (buttons, links, accordions).
- **Contrast**: Primary button uses black text on lime green for readability.
- **Links**: Descriptive text; external links `rel="noopener noreferrer"`.
- **Meta**: Unique title and description per route (e.g. in `index.html` or via React Helmet if added).

---

## 12. Files Reference

| Purpose | File(s) |
|--------|---------|
| Tokens (colors, spacing, radius, motion) | `src/styles/tokens.css` |
| Component base styles (buttons, cards, badges, code) | `src/styles/components.css` |
| Global reset, utilities, animations | `src/styles/globals.css` |
| Design system JSON (source of truth for tooling) | `design-system/design-system.json` |
| Primitives | `src/components/Button.tsx`, `Card.tsx`, `Badge.tsx`, `CodeBlock.tsx`, `Container.tsx`, `Section.tsx` |
| Layout / pages | `src/sections/*`, `src/pages/*` |

---

## 13. Redesign or New Feature Checklist

- [ ] Use semantic tokens (`--text-primary`, `--bg-surface`, `--brand-primary`) instead of raw hex where possible.
- [ ] Reuse `Container`, `Section`, `Button`, `Card`, `CodeBlock` for consistency.
- [ ] Stick to the spacing scale (`--space-*`) and section padding (`section`, `section-alt`).
- [ ] Use existing utility classes from `globals.css`; add new ones there if needed.
- [ ] Keep primary CTA green with black text; outline/secondary for secondary actions.
- [ ] Test responsive at 768px and 1024px; use `md:` and `lg:` utilities.
- [ ] Check heading order and focus visibility for a11y.
- [ ] Update this doc or `design-system.json` if you introduce new tokens or components.
