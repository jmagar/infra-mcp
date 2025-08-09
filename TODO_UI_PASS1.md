# UI/UX Revamp – Pass 1 (Foundations + Core Components)

Status: Planned
Owner: UI/FE
Scope: TailwindCSS v4, React, Radix UI

## Goals
- Consistent spacing, typography, colors, and motion across core components
- v4-compliant utilities and tokens
- Strong dark mode and focus states

---

## Foundations
- [ ] `apps/frontend/src/index.css`
  - [ ] Validate/adjust `@theme` tokens for contrast in light/dark (OKLCH palette) 
  - [ ] Normalize border radii, shadow scale, spacing rhythm (4px grid)
  - [ ] Unify animation timings to `--ease-smooth`; limit overshoot; add `prefers-reduced-motion`
  - [ ] QA custom utilities: `scrollbar-*`, `glass*`, `gradient-*`, `animate-*` (v4-safe)

- [ ] `apps/frontend/src/lib/design-system.ts`
  - [ ] Align `componentStyles.container/layout` paddings and gaps (xs/sm/md/lg)
  - [ ] Ensure `typography.*` is the single source for headings/body/labels
  - [ ] Review `interactive.button/input` sizes; add coherent `sm/md/lg/xl`
  - [ ] Unify shadow tokens (`sm/md/lg/xl`, `card`, `elevated`) and use consistently

---

## Core UI Components (unify sizes/variants/focus/spacing)
- [ ] `apps/frontend/src/components/ui/button.tsx`
  - [ ] Confirm variants: default, secondary, outline, ghost, destructive, link, gradient, success, warning
  - [ ] Validate sizes (`sm/default/lg/xl`, `icon-*`), icon spacing, loading state, `focus-visible` ring
  - [ ] Active state subtle scale; disabled + loading combinations

- [ ] `apps/frontend/src/components/ui/card.tsx`
  - [ ] Standardize paddings (`p-4`/`p-6`), header/content spacing
  - [ ] Variants: `default`, `elevated`, (optional) `ghost` using design-system shadows

- [ ] Inputs
  - [ ] `apps/frontend/src/components/ui/input.tsx`
  - [ ] `apps/frontend/src/components/ui/textarea.tsx`
  - [ ] `apps/frontend/src/components/ui/select.tsx`
  - [ ] `apps/frontend/src/components/ui/checkbox.tsx`
  - [ ] `apps/frontend/src/components/ui/label.tsx`
  - [ ] Actions:
    - [ ] Heights/padding for `sm/md/lg`
    - [ ] `focus-visible` ring + invalid/error classes
    - [ ] Placeholder opacity and disabled states

- [ ] Data presentation
  - [ ] `apps/frontend/src/components/ui/table.tsx`: row density options, hover states, header/footer spacing, optional zebra rows
  - [ ] `apps/frontend/src/components/ui/tabs.tsx`: active styles (underline or pill), keyboard nav focus states
  - [ ] `apps/frontend/src/components/ui/badge.tsx`: status variants mapped to design-system `status.*`

---

## Common Components polish (light pass during Pass 1)
- [ ] `apps/frontend/src/components/common/MetricCard.tsx`
  - [ ] Normalize paddings, icon sizes (16/20/24), title/metric/subtitle hierarchy
  - [ ] Map `status` -> semantic colors; subtle motion on mount; reduce shadow flicker

---

## Dark mode & A11y
- [ ] Verify contrast ratios for text, borders, and badges in dark theme
- [ ] Ensure all interactives have clear `:focus-visible` outlines
- [ ] Respect `prefers-reduced-motion`

---

## Responsiveness QA
- [ ] XS (≤475px): check header/actions wrapping, tiles/grid density, no horizontal scroll
- [ ] SM/MD/LG/XL: consistent gutters and grid gaps; card heights not jittering

---

## Verification
- [ ] Run: `npm --prefix apps/frontend run lint`
- [ ] Run: `npm --prefix apps/frontend run build` (typecheck via `tsc -b`)
- [ ] Manual smoke test light/dark, keyboard nav, basic pages load

---

## Notes
- Tailwind v4: rely on `@theme` and CSS-first utilities; avoid legacy config-based extension
- Prefer `componentStyles.*` helpers over ad-hoc class strings where possible
