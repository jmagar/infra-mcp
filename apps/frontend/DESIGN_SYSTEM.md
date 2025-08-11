# Infrastructor Visual Design System

A comprehensive modern design system built for dark-first infrastructure management interfaces.

## 🎨 Design Philosophy

### Core Principles
- **Dark-First Design**: Optimized for long monitoring sessions and low-light environments
- **Glass Morphism**: Modern depth and layering with backdrop blur effects
- **High Contrast**: Ensuring accessibility and readability in all lighting conditions
- **Semantic Color System**: Meaningful colors that convey system status at a glance
- **Responsive & Scalable**: Works seamlessly across all device sizes

### Visual Language
- Clean, minimal interfaces with purposeful whitespace
- Subtle gradients and shadows for depth perception
- Consistent typography scale for clear information hierarchy
- Motion design that feels natural and purposeful

## 🎯 Color System

### Primary Palette
Our color system is built around infrastructure status and semantic meaning:

```typescript
// Primary Brand Colors
--brand-blue: #3b82f6      // Primary actions, links
--brand-purple: #8b5cf6    // Secondary actions, gradients
--brand-cyan: #06b6d4      // Data visualization, accents

// Semantic Status Colors
--status-online: #10b981   // Systems running, healthy state
--status-offline: #ef4444  // Errors, critical issues
--status-warning: #f59e0b  // Warnings, attention needed
--status-pending: #8b5cf6  // Processing, in-progress
--status-stopped: #64748b  // Disabled, inactive
```

### Surface Colors (Dark Mode)
```typescript
// Background Layers
--surface-base: rgb(2 6 23)           // Body background
--surface-elevated-1: rgb(15 23 42)   // Cards, panels
--surface-elevated-2: rgb(30 41 59)   // Modals, overlays
--surface-elevated-3: rgb(51 65 85)   // Highest elevation

// Interactive Surfaces
--surface-hover: rgba(255 255 255 0.1)    // Hover states
--surface-active: rgba(255 255 255 0.15)  // Active/pressed states
--surface-selected: rgba(59 130 246 0.2)  // Selected items
```

### Text Colors
```typescript
// Text Hierarchy
--text-primary: rgb(248 250 252)      // Main headings, primary text
--text-secondary: rgb(203 213 225)    // Secondary text, labels
--text-tertiary: rgb(148 163 184)     // Captions, metadata
--text-inverse: rgb(15 23 42)         // Text on light backgrounds

// Semantic Text
--text-success: rgb(34 197 94)        // Success messages
--text-error: rgb(239 68 68)          // Error messages
--text-warning: rgb(245 158 11)       // Warning text
--text-info: rgb(59 130 246)          // Information text
```

## 🏗️ Glass Morphism System

Our glass morphism system provides four distinct levels of visual hierarchy:

### Card (`glassStyles.card`)
Standard glass effect for most UI components:
- **Background**: `bg-slate-800/60` (60% opacity slate-800)
- **Border**: `border-slate-600/40` (40% opacity slate-600)
- **Backdrop**: `backdrop-blur-xl` (24px blur)
- **Shadow**: Deep shadow with 40% opacity for depth

```tsx
<div className={glassStyles.card}>
  Standard content card
</div>
```

### Elevated (`glassStyles.elevated`)
Enhanced glass for important components like modals and navigation:
- **Background**: `bg-slate-800/80` (80% opacity slate-800)
- **Border**: `border-slate-600/60` (60% opacity slate-600)  
- **Backdrop**: `backdrop-blur-2xl` (40px blur)
- **Shadow**: Stronger shadow with 50% opacity

```tsx
<div className={glassStyles.elevated}>
  Modal or navigation content
</div>
```

### Subtle (`glassStyles.subtle`)
Minimal glass for background elements:
- **Background**: `bg-slate-800/40` (40% opacity slate-800)
- **Border**: `border-slate-600/30` (30% opacity slate-600)
- **Backdrop**: `backdrop-blur-lg` (16px blur)
- **Shadow**: Light shadow with 30% opacity

```tsx
<div className={glassStyles.subtle}>
  Background or decorative element
</div>
```

### Interactive (`glassStyles.interactive`)
Glass with hover states for clickable elements:
- **Base**: Same as card style
- **Hover**: Darker background (`bg-slate-700/80`)
- **Hover Border**: More defined (`border-slate-500/60`)
- **Scale**: Subtle scale transform on hover (`hover:scale-[1.02]`)

```tsx
<button className={glassStyles.interactive}>
  Interactive button
</button>
```

## 📝 Typography System

### Font Stack
```css
/* Primary font family */
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;

/* Monospace for code/data */
font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Consolas, monospace;
```

### Type Scale

#### Display Text (Hero headings)
```typescript
display: {
  xl: "text-5xl font-bold tracking-tight leading-none",    // 48px
  lg: "text-4xl font-bold tracking-tight leading-tight",   // 36px  
  md: "text-3xl font-bold tracking-tight leading-tight",   // 30px
  sm: "text-2xl font-bold tracking-tight leading-tight",   // 24px
}
```

#### Headings (Section headings)
```typescript
heading: {
  xl: "text-2xl font-semibold tracking-tight leading-tight", // 24px
  lg: "text-xl font-semibold tracking-tight leading-tight",  // 20px
  md: "text-lg font-semibold tracking-tight leading-tight",  // 18px
  sm: "text-base font-semibold tracking-tight leading-tight", // 16px
}
```

#### Body Text (Content)
```typescript
body: {
  lg: "text-base font-medium leading-relaxed",  // 16px
  md: "text-sm font-medium leading-relaxed",    // 14px
  sm: "text-xs font-medium leading-relaxed",    // 12px
}
```

#### Captions (Metadata, labels)
```typescript
caption: {
  lg: "text-sm font-normal leading-normal text-muted-foreground",  // 14px
  md: "text-xs font-normal leading-normal text-muted-foreground", // 12px
  sm: "text-xs font-normal leading-tight text-muted-foreground",  // 12px
}
```

### Usage Examples
```tsx
// Main page heading
<h1 className={typography.display.lg}>
  Infrastructure Dashboard
</h1>

// Section heading
<h2 className={typography.heading.lg}>
  System Metrics
</h2>

// Body text
<p className={typography.body.md}>
  System status information
</p>

// Metadata/labels
<span className={typography.caption.md}>
  Last updated: 2 minutes ago
</span>
```

## 📏 Spacing System

Consistent spacing scale based on 4px base unit:

### Container Padding
```typescript
container: {
  sm: "p-4",   // 16px all sides
  md: "p-6",   // 24px all sides
  lg: "p-8",   // 32px all sides
  xl: "p-12",  // 48px all sides
}
```

### Stack Spacing (Vertical)
```typescript
stack: {
  xs: "space-y-2",   // 8px between elements
  sm: "space-y-3",   // 12px between elements
  md: "space-y-4",   // 16px between elements
  lg: "space-y-6",   // 24px between elements
  xl: "space-y-8",   // 32px between elements
  "2xl": "space-y-12", // 48px between elements
}
```

### Grid/Flex Gaps
```typescript
gap: {
  xs: "gap-2",   // 8px gap
  sm: "gap-3",   // 12px gap
  md: "gap-4",   // 16px gap
  lg: "gap-6",   // 24px gap
  xl: "gap-8",   // 32px gap
  "2xl": "gap-12", // 48px gap
}
```

## 🎭 Status Indicator System

Semantic colors that immediately convey system state:

### Online/Healthy (Green)
```typescript
online: {
  bg: "bg-emerald-500/10 dark:bg-emerald-400/20",
  border: "border-emerald-500/20 dark:border-emerald-400/40",
  text: "text-emerald-700 dark:text-emerald-200",
  indicator: "bg-emerald-500 dark:bg-emerald-400",
}
```

### Offline/Error (Red)
```typescript
offline: {
  bg: "bg-red-500/10 dark:bg-red-400/20",
  border: "border-red-500/20 dark:border-red-400/40", 
  text: "text-red-700 dark:text-red-200",
  indicator: "bg-red-500 dark:bg-red-400",
}
```

### Warning/Attention (Amber)
```typescript
warning: {
  bg: "bg-amber-500/10 dark:bg-amber-400/20",
  border: "border-amber-500/20 dark:border-amber-400/40",
  text: "text-amber-700 dark:text-amber-200", 
  indicator: "bg-amber-500 dark:bg-amber-400",
}
```

### Usage Example
```tsx
<StatusIndicator 
  status="online"
  label="System Healthy"
  size="md"
  pulse={true}
/>
```

## 🎬 Animation System

Subtle, purposeful animations that enhance UX:

### Entrance Animations
```typescript
fadeIn: "animate-in fade-in-0 duration-500 ease-out"
slideInFromBottom: "animate-in slide-in-from-bottom-4 fade-in-0 duration-500 ease-out"
slideInFromTop: "animate-in slide-in-from-top-4 fade-in-0 duration-500 ease-out"
scaleIn: "animate-in zoom-in-95 fade-in-0 duration-500 ease-out"
```

### Hover Effects
```typescript
hover: "transition-all duration-200 ease-out hover:scale-105 hover:-translate-y-1"
hoverSubtle: "transition-all duration-200 ease-out hover:scale-[1.02]"
hoverCard: "transition-all duration-300 ease-out hover:scale-[1.02] hover:shadow-2xl"
```

### Micro-interactions
```typescript
buttonPress: "active:scale-95 transition-transform duration-100"
iconBounce: "hover:scale-110 hover:-translate-y-0.5 transition-all duration-200"
iconSpin: "hover:rotate-180 transition-transform duration-300"
```

## 🧩 Component Patterns

### Modern Card
Primary container component with glass morphism:

```tsx
<ModernCard variant="elevated" size="lg" animation="scale">
  <ModernCardHeader 
    title="System Metrics"
    description="Real-time performance data"
    status="online"
  />
  <ModernCardContent>
    {/* Card content */}
  </ModernCardContent>
  <ModernCardFooter>
    {/* Optional footer actions */}
  </ModernCardFooter>
</ModernCard>
```

### Metric Display
Specialized component for showing numerical data:

```tsx
<Metric
  label="CPU Usage"
  value={72}
  unit="%"
  trend="up"
  trendValue="+5%"
  status="warning"
  size="lg"
/>
```

### Progress Indicators
Visual representation of completion/usage:

```tsx
<ProgressBar
  value={72}
  max={100}
  label="Disk Usage"
  status="warning"
  size="lg"
  showValue={true}
/>
```

### Status Indicators
Visual system state communication:

```tsx
<StatusIndicator
  status="online"
  label="Live Data"
  size="md"
  pulse={true}
/>
```

## 📱 Responsive Breakpoints

Tailwind CSS breakpoint system:

```typescript
breakpoints: {
  sm: "640px",   // Mobile landscape, small tablets
  md: "768px",   // Tablets
  lg: "1024px",  // Small desktops, large tablets
  xl: "1280px",  // Desktops
  "2xl": "1536px" // Large desktops, 4K displays
}
```

### Responsive Patterns
```tsx
// Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">

// Responsive text
<h1 className="text-2xl md:text-3xl lg:text-4xl xl:text-5xl">

// Responsive spacing
<div className="p-4 md:p-6 lg:p-8">
```

## 🎯 Best Practices

### Do's
- ✅ Use semantic status colors consistently
- ✅ Apply appropriate glass morphism levels based on content importance
- ✅ Maintain consistent spacing using the spacing scale
- ✅ Use animation purposefully to guide user attention
- ✅ Test color contrast for accessibility
- ✅ Follow the typography hierarchy

### Don'ts
- ❌ Mix different glass morphism styles arbitrarily
- ❌ Use colors outside the defined palette
- ❌ Apply excessive animations that distract
- ❌ Break the typography hierarchy
- ❌ Use fixed pixel values instead of the spacing system
- ❌ Ignore dark mode considerations

### Performance Considerations
- Use `backdrop-blur` sparingly on mobile devices
- Implement animation `prefers-reduced-motion` respect
- Optimize glass morphism for lower-end devices
- Use CSS custom properties for theme switching

## 🔧 Implementation

### Using the Design System
```tsx
import { 
  cn, 
  glassStyles, 
  typography, 
  spacing, 
  statusColors, 
  animations 
} from '@/lib/modern-design-system'

// Combining classes
<div className={cn(
  glassStyles.card,
  spacing.container.lg,
  animations.fadeIn,
  "custom-class"
)}>
```

### Extending the System
```tsx
// Adding new variants
const customGlass = {
  ...glassStyles,
  premium: "backdrop-blur-3xl bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/30"
}

// Adding new status colors
const customStatus = {
  ...statusColors,
  maintenance: {
    bg: "bg-orange-500/10 dark:bg-orange-400/20",
    text: "text-orange-700 dark:text-orange-200",
    indicator: "bg-orange-500 dark:bg-orange-400",
  }
}
```

This design system ensures consistent, accessible, and beautiful interfaces across the entire infrastructure management platform while maintaining excellent performance and user experience.