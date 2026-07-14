# 🎨 BioSecure AI Design System
# BioSecure AI

**Version**: 2.0  
**Last Updated**: 2026-07-14  

> The BioSecure AI design system defines the complete visual language of the application — colors, typography, spacing, components, animations, and accessibility standards.

---

## 1. Brand Identity

**Name**: BioSecure AI  
**Personality**: Professional, precise, futuristic, trustworthy  
**Aesthetic**: Dark glassmorphism — sophisticated, premium, and focused on data clarity

### Brand Description
BioSecure AI evokes security and intelligence. The UI communicates authority through deep navy and zinc backgrounds, with carefully selected accent colors (indigo for primary actions, emerald for success states) to guide attention without overwhelming. Every interface element feels refined and purposeful.

---

## 2. Color Palette

### Core Colors

| Token | Value | Usage |
|---|---|---|
| `--color-bg-base` | `#0b1326` | Page background — deep navy |
| `--color-bg-surface` | `rgba(23, 31, 51, 0.70)` | Glass panels |
| `--color-bg-card` | `rgba(23, 31, 51, 0.45)` | Glass cards (lighter) |
| `--color-bg-input` | `rgba(11, 19, 38, 0.60)` | Form inputs |
| `--color-border` | `rgba(255, 255, 255, 0.08)` | Subtle borders |
| `--color-border-hover` | `rgba(255, 255, 255, 0.15)` | Hover state borders |

### Text Colors

| Token | Value | Usage |
|---|---|---|
| `--color-text-primary` | `#fafafa` | Headings, primary content |
| `--color-text-secondary` | `#dae2fd` | Body text, descriptions |
| `--color-text-muted` | `#a1a1aa` | Placeholders, helper text |
| `--color-text-disabled` | `#52525b` | Disabled state |

### Accent Colors

| Token | Value | Tailwind | Usage |
|---|---|---|---|
| `--color-primary` | `#3b82f6` | `blue-500` | Primary CTA, links, active nav |
| `--color-primary-hover` | `#2563eb` | `blue-600` | Primary button hover |
| `--color-success` | `#10b981` | `emerald-500` | Present status, success alerts |
| `--color-danger` | `#ef4444` | `red-500` | Delete, logout, absent status |
| `--color-danger-muted` | `rgba(239,68,68,0.20)` | — | Danger button background |
| `--color-warning` | `#f59e0b` | `amber-500` | Warnings, "Already Marked" |
| `--color-unknown` | `#a855f7` | `purple-500` | Unknown faces, confidence % |
| `--color-admin` | `#6366f1` | `indigo-500` | Admin badge, admin sections |

### Gradient System

```css
/* Page background gradient */
background-image:
  radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 40%),
  radial-gradient(circle at 90% 80%, rgba(99, 102, 241, 0.05) 0%, transparent 40%);

/* Primary button glow */
box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.30);

/* Success glow */
box-shadow: 0 0 20px rgba(16, 185, 129, 0.15);
```

---

## 3. Typography

### Font Stack

| Role | Font | Weights | Usage |
|---|---|---|---|
| **Display / Headings** | `Geist` | 600, 700, 800 | `h1`–`h3`, logo, stat numbers |
| **Body / UI** | `Inter` | 300, 400, 500, 600 | Body text, labels, inputs, nav |

```css
/* Import */
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* Base */
body { font-family: 'Inter', sans-serif; }
h1, h2, h3, h4, h5, h6, .font-geist { font-family: 'Geist', sans-serif; }
```

### Type Scale

| Size | Tailwind | Usage |
|---|---|---|
| `2xl` / 24px | `text-2xl` | Section headings |
| `xl` / 20px | `text-xl` | Page titles, nav brand |
| `lg` / 18px | `text-lg` | Card headings |
| `sm` / 14px | `text-sm` | Body text, nav links |
| `xs` / 12px | `text-xs` | Labels, badges, captions |

---

## 4. Spacing System

Follows Tailwind's default spacing scale (4px base unit):

| Token | Value | Usage |
|---|---|---|
| `px-6 py-3` | 24px / 12px | Nav bar padding |
| `p-8` | 32px | Main card internal padding |
| `p-6` | 24px | Section padding |
| `gap-4` | 16px | Grid/flex gap (standard) |
| `gap-3` | 12px | Compact grid gap |
| `mt-20` | 80px | Main content top margin (below fixed header) |

---

## 5. Shape System

| Element | Border Radius | Tailwind |
|---|---|---|
| Main cards / panels | 16px | `rounded-2xl` |
| Buttons | 8px | `rounded-lg` |
| Inputs | 8px | `rounded-lg` |
| Image thumbnails | 4px | `rounded` |
| Status pills / badges | 9999px | `rounded-full` |
| Icon containers | 12px | `rounded-xl` |

---

## 6. Glassmorphism System

### Glass Panel (Primary Surface)
```css
.glass-panel {
    background: rgba(23, 31, 51, 0.70);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
}
```

### Glass Card (Secondary Surface)
```css
.glass-card {
    background: rgba(23, 31, 51, 0.45);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
}
```

### Inner Highlight
```css
.inner-glow {
    box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.05);
}
```

---

## 7. Component Library

### Buttons

```css
/* Primary */
.btn-primary-glass {
    background: #3b82f6;
    color: #ffffff;
    box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.30);
    border: 1px solid rgba(255, 255, 255, 0.10);
    transition: all 0.2s ease-in-out;
}
.btn-primary-glass:hover {
    background: #2563eb;
    box-shadow: 0 6px 20px 0 rgba(59, 130, 246, 0.40);
    transform: translateY(-1px);
}

/* Secondary / Ghost */
.btn-secondary-glass {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.10);
    color: #dae2fd;
    transition: all 0.2s ease-in-out;
}
.btn-secondary-glass:hover {
    background: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.20);
}

/* Danger */
.btn-danger-glass {
    background: rgba(239, 68, 68, 0.20);
    border: 1px solid rgba(239, 68, 68, 0.40);
    color: #fca5a5;
    transition: all 0.2s ease-in-out;
}
.btn-danger-glass:hover {
    background: rgba(239, 68, 68, 0.30);
    border-color: rgba(239, 68, 68, 0.60);
}
```

### Form Inputs

```css
.input-dark-glass {
    background: rgba(11, 19, 38, 0.60);
    border: 1px solid rgba(255, 255, 255, 0.10);
    color: #fafafa;
    transition: all 0.2s ease-in-out;
}
.input-dark-glass:focus {
    border-color: #3b82f6;
    outline: none;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.30);
}
```

### Status Badges

| Status | Background | Text | Border |
|---|---|---|---|
| Present | `emerald-500/10` | `emerald-400` | `emerald-500/20` |
| Absent | `red-500/10` | `red-400` | `red-500/20` |
| Already Marked | `amber-500/10` | `amber-400` | `amber-500/20` |
| Unknown | `purple-500/10` | `purple-400` | `purple-500/20` |
| System Live | `emerald-500/10` | `emerald-400` | `emerald-500/20` |
| Admin | `indigo-500/10` | `indigo-400` | `indigo-500/20` |

### Icon System
- **Library**: Lucide (`unpkg.com/lucide@latest`)
- **Standard size**: `w-5 h-5` (20px) for UI icons; `w-8 h-8` (32px) for feature icons
- **Initialisation**: Always call `lucide.createIcons()` after dynamic DOM insertion

---

## 8. Animation Guidelines

### Micro-animations (Standard)

| Type | Duration | Easing | Use |
|---|---|---|---|
| Hover state | `200ms` | `ease-in-out` | All interactive elements |
| Button press | `100ms` | `ease` | `translateY(0)` on active |
| Fade in | `300ms` | `ease-out` | New content appearing |
| Icon scale on hover | `200ms` | `ease` | Feature icons: `scale-110` |

### Signature Animations

```css
/* Scan line — main attendance page camera overlay */
.scan-line {
    height: 2px;
    background: linear-gradient(90deg, transparent, #3b82f6, transparent);
    animation: scan-anim 3s linear infinite;
    box-shadow: 0 0 8px #3b82f6;
}
@keyframes scan-anim {
    0%   { top: 0%; }
    50%  { top: 100%; }
    100% { top: 0%; }
}

/* Pulse dot — "SYSTEM LIVE" indicator */
.animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }

/* Loading spinner */
.animate-spin { animation: spin 1s linear infinite; }
```

### Performance Rules
- All CSS animations use `transform` and `opacity` only (GPU-composited, no layout thrash)
- No JS-driven animation for repeating effects — use CSS `@keyframes`
- `will-change: transform` only on elements that definitely animate (avoid overuse)

---

## 9. Scrollbar Styling

```css
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.20); }
```

---

## 10. Layout System

### Fixed Header
```
height: ~56px (py-3 = 12px × 2 + content)
z-index: 50
backdrop-blur-xl
```

### Fixed Bottom Nav (Mobile only)
```
height: 64px (h-16)
visible: below md breakpoint
z-index: 50
backdrop-blur-lg
```

### Main Content Area
```
padding-top: 80px (mt-20, clears fixed header)
padding-bottom: 96px (pb-24 on mobile, pb-8 on desktop, clears bottom nav)
max-width: varies by page (max-w-4xl for upload, max-w-6xl for tables)
```

---

## 11. Responsive Breakpoints

| Breakpoint | Width | Behaviour |
|---|---|---|
| (default) | 0px+ | Mobile-first; bottom nav visible |
| `sm` | 640px+ | Desktop camera button visible; 2-col grids |
| `md` | 768px+ | Bottom nav hidden; top nav visible |
| `lg` | 1024px+ | Username shown in header |

---

## 12. Accessibility Standards

| Standard | Requirement |
|---|---|
| Color contrast | All text/background combinations meet WCAG AA (4.5:1 ratio) |
| Focus indicators | All interactive elements have visible `:focus` ring (`ring-blue-500`) |
| Semantic HTML | `<main>`, `<nav>`, `<header>`, `<button>` used appropriately |
| Form labels | All inputs have associated `<label>` elements |
| Alt text | All `<img>` elements have descriptive `alt` attributes |
| Motion | Respect `prefers-reduced-motion` for scan-line animation |
