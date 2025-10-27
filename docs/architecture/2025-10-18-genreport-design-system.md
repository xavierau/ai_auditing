# GenReport Design System Specification

**Date:** 2025-10-18
**Version:** 1.0
**Created by:** UI/UX Designer Agent
**Status:** Approved for Implementation

---

## Executive Summary

This design system provides comprehensive specifications for building GenReport's frontend using **shadcn/ui** components with **Tailwind CSS**. The system prioritizes:

1. **Task Efficiency:** Minimize clicks and cognitive load for audit professionals
2. **Security Visibility:** Clear indicators for encryption, PII detection, tenant context
3. **Market Awareness:** Jurisdiction-specific formatting (HKD/SGD/AUD, dates)
4. **Accessibility:** WCAG 2.1 AA compliance for inclusive teams

---

## Color Palette

### Primary Colors
```typescript
// tailwind.config.ts
primary: {
  50: '#eff6ff',   // Light blue backgrounds
  100: '#dbeafe',
  500: '#3b82f6',  // Primary buttons, links
  600: '#2563eb',  // Primary hover state
  700: '#1d4ed8',
}
```

### Semantic Colors
```typescript
success: {
  50: '#f0fdf4',
  500: '#22c55e',  // Approved status, checkmarks
  700: '#15803d',
}

warning: {
  50: '#fffbeb',
  500: '#f59e0b',  // Review status, medium confidence
  700: '#b45309',
}

error: {
  50: '#fef2f2',
  500: '#ef4444',  // Failed status, validation errors
  700: '#b91c1c',
}
```

### Jurisdiction Colors
```typescript
jurisdiction: {
  hk: '#3b82f6',   // Blue for Hong Kong
  sg: '#22c55e',   // Green for Singapore
  au: '#f59e0b',   // Amber for Australia
}
```

**Usage:**
- Primary actions: `bg-primary-600 hover:bg-primary-500`
- Status badges: Use semantic colors
- Jurisdiction badges: Use jurisdiction colors with 50-value backgrounds

---

## Typography

### Font Families
```typescript
fontFamily: {
  sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
  mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
}
```

### Scale
- **xs (12px):** Badges, labels
- **sm (14px):** Body text, buttons
- **base (16px):** Primary body
- **lg (18px):** Subheadings
- **xl (20px):** Section headers
- **2xl (24px):** Page titles
- **3xl (30px):** Dashboard headers

### Component Typography
- Page titles: `text-3xl font-bold text-gray-900`
- Section headers: `text-xl font-semibold text-gray-900`
- Body text: `text-sm font-normal text-gray-700`
- Buttons: `text-sm font-semibold`
- Numeric data: `font-mono text-right tabular-nums`

---

## Spacing System

4px base scale (Tailwind default):
- **Card padding:** `p-6` (24px)
- **Button padding:** `px-6 py-3` (24px H, 12px V)
- **Form fields:** `space-y-4` (16px gap)
- **Section gaps:** `gap-6` (24px)
- **Page margins:** `px-6 py-8` (24px H, 32px V)

---

## Key Components

### Project Card

**Purpose:** At-a-glance project status with quick actions

```tsx
<div className="group relative rounded-lg border border-gray-200 bg-white p-6
                shadow-sm transition-all hover:shadow-md hover:border-gray-300">
  <h3 className="text-lg font-semibold">{project.project_name}</h3>

  {/* Jurisdiction & Status */}
  <div className="mt-2 flex gap-2">
    <Badge variant="hk">HK</Badge>
    <Badge variant="status-review">Review</Badge>
  </div>

  {/* Metadata */}
  <div className="mt-3 text-sm text-gray-600">
    <p>Client: {project.client.company_name}</p>
    <p>FYE: {formatDate(project.financial_year_end, 'HK')}</p>
  </div>
</div>
```

**States:**
- Hover: `border-gray-300 shadow-md scale-[1.02]`
- Active: `border-blue-500 shadow-lg`
- Processing: Animated pulse on status badge

---

### Jurisdiction Badge

**Purpose:** Instant market identification

```tsx
// HK Badge (Blue)
<span className="inline-flex items-center rounded-md bg-blue-50 px-2.5 py-0.5
                 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
  HK
</span>

// SG Badge (Green)
<span className="... bg-green-50 text-green-700 ring-green-700/10">SG</span>

// AU Badge (Amber)
<span className="... bg-amber-50 text-amber-700 ring-amber-700/10">AU</span>
```

---

### Status Indicator

**Purpose:** Communicate project/report state

```tsx
const statusStyles = {
  draft: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700 animate-pulse",
  review: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700"
}

<span className={cn(
  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
  statusStyles[status]
)}>
  {status === 'processing' && <Loader2 className="h-3 w-3 animate-spin" />}
  {statusText}
</span>
```

---

### File Upload Zone

**Purpose:** Secure drag-drop file acceptance

```tsx
<div className="relative flex flex-col items-center justify-center rounded-lg
                border-2 border-dashed border-gray-300 bg-gray-50 p-12
                hover:border-gray-400 hover:bg-gray-100">

  {/* Drag-over state */}
  {isDragOver && (
    <div className="border-blue-500 bg-blue-50">
      <Upload className="h-8 w-8 text-blue-500" />
      <p>Drop file here</p>
    </div>
  )}

  {/* Error state */}
  {error && (
    <div className="border-red-300 bg-red-50">
      <AlertCircle className="h-8 w-8 text-red-500" />
      <p className="text-red-700">{error}</p>
    </div>
  )}
</div>
```

**Validations:**
- File type: `.xlsx` only
- Max size: 50MB
- Macro detection: Blocked
- Instant feedback on all validations

---

### Confidence Score

**Purpose:** Visual AI confidence indicator

```tsx
const getConfidenceBadge = (score: number) => {
  if (score >= 80) return "bg-green-100 text-green-700"; // High
  if (score >= 60) return "bg-yellow-100 text-yellow-800"; // Medium
  return "bg-red-100 text-red-700"; // Low
}

<div className="inline-flex items-center gap-2">
  <span className={cn(
    "inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold",
    getConfidenceBadge(score)
  )}>
    {score >= 80 && <CheckCircle className="h-4 w-4" />}
    {score < 60 && <AlertCircle className="h-4 w-4" />}
    {score}%
  </span>
</div>
```

---

### Primary Action Button

**Purpose:** Main CTA (Generate Report)

```tsx
<Button className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-500
                   disabled:bg-gray-300 disabled:cursor-not-allowed">
  <Sparkles className="h-5 w-5" />
  Generate Report
</Button>

{/* Loading state */}
<Button disabled>
  <Loader2 className="h-5 w-5 animate-spin" />
  Generating...
</Button>
```

---

## Accessibility

✅ **Color Contrast:** All text meets WCAG AA (4.5:1 minimum)
✅ **Keyboard Navigation:** Full keyboard operability
✅ **Focus Indicators:** `ring-2 ring-blue-500` on all interactive elements
✅ **ARIA Attributes:** Proper roles, labels, live regions
✅ **Semantic HTML:** `<nav>`, `<main>`, `<button>`, `<table>`

---

## Icons

**Library:** Lucide React

Common icons:
- `Sparkles` - AI/Generate
- `Upload` - File upload
- `Download` - Export
- `CheckCircle` - Success
- `AlertCircle` - Warning
- `XCircle` - Error
- `Lock` - Security
- `Eye` - Review
- `Edit3` - Edit

**Sizing:**
- Standard buttons: `h-5 w-5` (20px)
- Small status: `h-4 w-4` (16px)
- Large features: `h-8 w-8` (32px)

---

## Responsive Layout

```tsx
// Project grid
<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">

// Side-by-side comparison
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">

// Settings with sidebar
<div className="grid grid-cols-1 lg:grid-cols-[250px_1fr] gap-8">
```

**Breakpoints:**
- `sm`: 640px (mobile)
- `md`: 768px (tablet)
- `lg`: 1024px (laptop)
- `xl`: 1280px (desktop)
- `2xl`: 1536px (large desktop)

---

## Dark Mode

```tsx
// Component example
<div className="bg-white dark:bg-gray-800
                border-gray-200 dark:border-gray-700
                text-gray-900 dark:text-gray-100">
```

**Toggle:**
```tsx
function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
      <Sun className="dark:hidden" />
      <Moon className="hidden dark:block" />
    </button>
  );
}
```

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] Install shadcn/ui with Tailwind
- [ ] Configure color palette
- [ ] Set up typography
- [ ] Install Lucide icons

### Phase 2: Core Components
- [ ] Button variants (primary, secondary, outline, ghost)
- [ ] Card component
- [ ] Badge component (jurisdiction, status)
- [ ] Input/Form components

### Phase 3: Complex Components
- [ ] Project card
- [ ] File upload zone
- [ ] Report section display
- [ ] Confidence score visualization
- [ ] Progress modal

### Phase 4: Layouts
- [ ] Dashboard grid
- [ ] Side-by-side comparison
- [ ] Navigation bar
- [ ] Settings layout

---

## Usage Examples

### Market-Aware Currency Display
```tsx
import { CurrencyFormatter } from '@/utils/currency';

<p>Revenue: {CurrencyFormatter.format(1234567.89, project.currency)}</p>
// Output: "HK$1,234,567.89" (if HK project)
```

### Date Formatting
```tsx
import { DateFormatter } from '@/utils/date';

<p>FYE: {DateFormatter.formatByJurisdiction(date, project.jurisdiction)}</p>
// Output: "17/10/2025" (if HK/SG/AU project)
```

### Jurisdiction Badge
```tsx
<Badge variant={`jurisdiction-${project.jurisdiction.toLowerCase()}`}>
  {project.jurisdiction}
</Badge>
```

---

## References

- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Lucide Icons](https://lucide.dev/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-18 | 1.0 | Initial design system specification |
| 2025-10-24 | 1.1 | Added document history for consistency |

---

**Document Status:** ✅ Approved for Implementation
**Implementation Status:** ✅ Active design system in use (see `frontend/` directory)
**Maintainer:** Frontend Team
