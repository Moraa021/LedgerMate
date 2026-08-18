# LedgerMate Design System Documentation

## Overview

This document describes the modern, production-ready design system for LedgerMate's landing page and web application. Built with semantic HTML5, modern CSS3, vanilla JavaScript, and optimized for accessibility (WCAG AA) and SEO.

---

## Table of Contents

1. [Color Palette](#color-palette)
2. [Typography](#typography)
3. [Spacing System](#spacing-system)
4. [Components](#components)
5. [Layout Architecture](#layout-architecture)
6. [Accessibility](#accessibility)
7. [Performance](#performance)
8. [Browser Support](#browser-support)

---

## Color Palette

### Primary Colors (Emerald/Teal)

- **Primary Dark**: `#059669` - CTA buttons, active states
- **Primary**: `#10b981` - Default interactive elements
- **Primary Light**: `#34d399` - Hover states
- **Primary Light**: `#d1fae5` - Light backgrounds
- **Primary BG**: `#f0fdf4` - Very light backgrounds

### Neutral Colors (Slate)

- **Slate 900**: `#0f172a` - Headlines, primary text
- **Slate 800**: `#1e293b` - Secondary text
- **Slate 700**: `#334155` - Body text
- **Slate 600**: `#475569` - Tertiary text
- **Slate 500**: `#64748b` - Disabled text
- **Slate 100**: `#f1f5f9` - Light backgrounds
- **Slate 50**: `#f8fafc` - Very light backgrounds

### Semantic Colors

- **Success**: `#10b981` - Positive actions
- **Danger**: `#ef4444` - Destructive actions
- **Warning**: `#f59e0b` - Warnings
- **Info**: `#3b82f6` - Information

### Usage Guidelines

```html
<!-- Primary Button -->
<button class="btn btn-primary">Get Started</button>

<!-- Secondary Button -->
<button class="btn btn-secondary">Learn More</button>

<!-- Text with semantic color -->
<span style="color: var(--color-success)">✓ Verified</span>
```

---

## Typography

### Font Family

- **Primary**: `Inter` (all text)
- **System Fallback**: `-apple-system, BlinkMacSystemFont, Segoe UI, Roboto`
- **Monospace**: `Courier New` (code blocks)

### Font Sizes

| Variable | Size | Usage |
|----------|------|-------|
| `--text-xs` | 12px | Labels, captions |
| `--text-sm` | 14px | Small text, metadata |
| `--text-base` | 16px | Body text |
| `--text-lg` | 18px | Large body text |
| `--text-xl` | 20px | Subheadings |
| `--text-2xl` | 24px | Feature titles |
| `--text-3xl` | 30px | Section headers |
| `--text-4xl` | 36px | Large headers |
| `--text-5xl` | 48px | Hero headlines |

### Font Weights

| Variable | Weight | Usage |
|----------|--------|-------|
| `--font-normal` | 400 | Body text |
| `--font-medium` | 500 | Emphasized text |
| `--font-semibold` | 600 | Subheadings |
| `--font-bold` | 700 | Headings |
| `--font-extrabold` | 800 | Hero headlines |

### Line Heights

| Variable | Value | Usage |
|----------|-------|-------|
| `--leading-tight` | 1.25 | Headings |
| `--leading-snug` | 1.375 | Subheadings |
| `--leading-normal` | 1.5 | Body text |
| `--leading-relaxed` | 1.625 | Large text blocks |
| `--leading-loose` | 2 | Very spacious text |

### Usage Examples

```html
<!-- Hero Headline -->
<h1 style="font-size: var(--text-5xl); font-weight: var(--font-extrabold);">
    Automate Your Ledger
</h1>

<!-- Body Text -->
<p style="font-size: var(--text-base); line-height: var(--leading-relaxed);">
    Track M-Pesa transactions and generate reports...
</p>

<!-- Feature Title -->
<h3 style="font-size: var(--text-2xl); font-weight: var(--font-bold);">
    Instant M-Pesa Parsing
</h3>
```

---

## Spacing System

All spacing uses an 8px base unit for consistency.

| Variable | Size | Pixels |
|----------|------|--------|
| `--space-0` | 0 | 0px |
| `--space-1` | 0.25rem | 4px |
| `--space-2` | 0.5rem | 8px |
| `--space-3` | 0.75rem | 12px |
| `--space-4` | 1rem | 16px |
| `--space-6` | 1.5rem | 24px |
| `--space-8` | 2rem | 32px |
| `--space-10` | 2.5rem | 40px |
| `--space-12` | 3rem | 48px |
| `--space-16` | 4rem | 64px |
| `--space-20` | 5rem | 80px |
| `--space-24` | 6rem | 96px |

### Border Radius

| Variable | Size |
|----------|------|
| `--radius-none` | 0 |
| `--radius-sm` | 4px |
| `--radius-md` | 6px |
| `--radius-lg` | 8px |
| `--radius-xl` | 12px |
| `--radius-2xl` | 16px |
| `--radius-3xl` | 24px |
| `--radius-full` | 9999px (circles) |

### Shadow System

| Variable | Usage |
|----------|-------|
| `--shadow-sm` | Subtle shadows, borders |
| `--shadow` | Default elements |
| `--shadow-md` | Hover states |
| `--shadow-lg` | Elevated cards |
| `--shadow-xl` | Modal-like elements |
| `--shadow-2xl` | Maximum elevation |

---

## Components

### Buttons

#### Primary Button

```html
<button class="btn btn-primary">Get Started Free</button>
```

**States:**
- Default: Dark emerald (`#059669`)
- Hover: Lighter emerald (`#10b981`) + shadow
- Active: No transform
- Focus: 2px solid outline

#### Secondary Button

```html
<button class="btn btn-secondary">Learn More</button>
```

**States:**
- Default: Transparent with slate border
- Hover: Light slate background

#### Large Button

```html
<button class="btn btn-primary btn-lg">Start Free Trial</button>
```

**Sizes:**
- Default: `padding: 12px 24px; min-height: 44px`
- Large (`btn-lg`): `padding: 16px 32px; min-height: 48px`

### Cards

#### Feature Card

```html
<article class="feature-card">
    <div class="feature-icon-wrapper">
        <div class="feature-icon">
            <i class="fas fa-star"></i>
        </div>
    </div>
    <h3 class="feature-title">Feature Name</h3>
    <p class="feature-description">Description text...</p>
</article>
```

**Features:**
- Hover: Lift up 4px, highlight top border
- Icon: Background color shifts on hover
- Responsive: 1 col mobile, 2 cols tablet, 3 cols desktop

#### Pricing Card

```html
<article class="pricing-card featured">
    <h3 class="pricing-plan-name">Pro</h3>
    <div class="pricing-price">
        <span class="currency">KES</span>
        <span class="amount">1,999</span>
        <span class="period">/month</span>
    </div>
    <ul class="pricing-features">
        <li><i class="fas fa-check"></i> Feature 1</li>
        <li><i class="fas fa-check"></i> Feature 2</li>
    </ul>
    <button class="btn btn-primary">Get Started</button>
</article>
```

**Variants:**
- Default: Slate border
- Featured: Primary border + scale 1.05 + shadow

### Navigation

```html
<header>
    <nav class="container-nav">
        <div class="nav-wrapper">
            <div class="brand-section">
                <a href="/" class="brand-link">LedgerMate</a>
            </div>
            <div class="nav-links" id="nav-menu">
                <a href="#features" class="nav-link">Features</a>
            </div>
            <div class="nav-actions">
                <a href="/login" class="btn btn-secondary">Login</a>
                <a href="/signup" class="btn btn-primary">Get Started</a>
            </div>
        </div>
    </nav>
</header>
```

**Features:**
- Sticky positioning on scroll
- Backdrop blur effect
- Mobile hamburger menu
- Smooth transitions

### Modal

```html
<div id="demo-modal" class="modal" role="dialog" aria-hidden="true">
    <div class="modal-content">
        <button class="modal-close" aria-label="Close modal">&times;</button>
        <div class="modal-video-container">
            <iframe src="..."></iframe>
        </div>
    </div>
</div>
```

---

## Layout Architecture

### Hero Section

```html
<section id="hero" class="hero-section">
    <div class="hero-container">
        <div class="hero-content">
            <!-- Headline, subheadline, CTAs -->
        </div>
        <div class="hero-visual">
            <!-- Mock dashboard preview -->
        </div>
    </div>
</section>
```

**Responsive:**
- Mobile: Single column, full width
- Tablet+: Two columns, 1fr 1fr

### Features Grid

```html
<section id="features" class="features-section">
    <div class="section-container">
        <div class="section-header">
            <h2 class="section-title">Title</h2>
            <p class="section-subtitle">Subtitle</p>
        </div>
        <div class="features-grid">
            <!-- Feature cards -->
        </div>
    </div>
</section>
```

**Grid Layout:**
- Mobile: 1 column
- Tablet: 2 columns
- Desktop: 3 columns

### Section Containers

All sections use `max-width: 1280px` centered container.

```css
.section-container {
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 var(--space-4);
}
```

---

## Accessibility

### WCAG AA Compliance

✅ **Implemented:**
- Color contrast ratios ≥ 4.5:1 for normal text
- Color contrast ratios ≥ 3:1 for large text
- Semantic HTML5 (`<header>`, `<main>`, `<section>`, `<article>`, `<footer>`)
- Skip-to-main-content link
- ARIA labels on all icon buttons
- Proper heading hierarchy (h1-h6)
- Form labels associated with inputs
- Focus indicators (2px solid outline)
- Keyboard navigation support

### Keyboard Navigation

All interactive elements support:
- `Tab` / `Shift+Tab` - Move focus
- `Enter` - Activate buttons/links
- `Escape` - Close modals
- `Space` - Toggle mobile menu

### Screen Reader Support

```html
<!-- Icon with aria-hidden -->
<i class="fas fa-check" aria-hidden="true"></i>

<!-- Icon button with label -->
<button aria-label="Close modal">
    <i class="fas fa-times" aria-hidden="true"></i>
</button>

<!-- Skip link -->
<a href="#main-content" class="sr-only">Skip to main content</a>
```

### Testing

```bash
# Automated accessibility testing
# Use tools like:
# - axe DevTools (Chrome/Firefox)
# - WAVE (browser extension)
# - Lighthouse (built into Chrome DevTools)

# Manual testing:
# 1. Navigate site using Tab/Shift+Tab only
# 2. Test with screen reader (NVDA, JAWS, VoiceOver)
# 3. Zoom to 200% and check layout
# 4. Check color contrast with tools
```

---

## Performance

### Optimization Techniques

1. **CSS Variables**: Single source of truth for design tokens
2. **Lazy Loading**: Images loaded on-demand
3. **Intersection Observer**: Animate elements only when visible
4. **Minimal JavaScript**: Vanilla ES6+, no dependencies
5. **CSS Grid & Flexbox**: Modern layout techniques
6. **Backdrop Blur**: GPU-accelerated effects

### Load Time Targets

- **First Contentful Paint (FCP)**: < 1.8s
- **Largest Contentful Paint (LCP)**: < 2.5s
- **Cumulative Layout Shift (CLS)**: < 0.1
- **Total Bundle Size**: < 50KB (HTML + CSS + JS)

### Monitoring

```javascript
// Check performance metrics
if (window.performance) {
    window.addEventListener('load', () => {
        const perfData = window.performance.timing;
        const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
        console.log(`Page Load Time: ${pageLoadTime}ms`);
    });
}
```

---

## SEO

### Meta Tags

```html
<meta name="description" content="...">
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:type" content="website">
<meta property="og:image" content="...">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="...">
```

### Structured Data

```html
<!-- Schema.org markup for rich snippets -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "LedgerMate",
    "description": "...",
    "applicationCategory": "FinanceApplication"
}
</script>
```

### Best Practices

- ✅ Descriptive page titles
- ✅ H1 on every page
- ✅ Semantic HTML structure
- ✅ Image alt tags
- ✅ Internal linking
- ✅ Mobile-responsive design

---

## Browser Support

| Browser | Min Version |
|---------|-------------|
| Chrome | 90+ |
| Firefox | 88+ |
| Safari | 14+ |
| Edge | 90+ |
| iOS Safari | 14+ |
| Chrome Mobile | 90+ |

### Fallbacks

- CSS Grid → Flexbox fallback
- CSS Variables → Inline values
- Backdrop Filter → Solid background color
- ES6+ → Babel transpilation (if needed)

---

## Usage Guidelines

### 1. Creating a New Component

```html
<!-- Follow the component template -->
<article class="component-card">
    <div class="component-icon">
        <i class="fas fa-icon" aria-hidden="true"></i>
    </div>
    <h3 class="component-title">Title</h3>
    <p class="component-description">Description</p>
</article>
```

### 2. Responsive Images

```html
<!-- Lazy loading with fallback -->
<img 
    src="image.jpg" 
    alt="Descriptive text" 
    loading="lazy"
    width="400" 
    height="300"
>
```

### 3. Form Elements

```html
<!-- Accessible form input -->
<label for="email" class="form-label">Email Address</label>
<input 
    type="email" 
    id="email" 
    class="form-input" 
    placeholder="you@example.com"
    required
    aria-label="Email address"
>
```

### 4. Adding Icons

```html
<!-- Use Font Awesome -->
<i class="fas fa-check" aria-hidden="true"></i>

<!-- Always hide decorative icons from screen readers -->
<!-- Add aria-label to container for buttons -->
<button aria-label="Close menu">
    <i class="fas fa-times" aria-hidden="true"></i>
</button>
```

---

## Customization

### Changing Primary Color

Update the CSS variables in `:root`:

```css
:root {
    --color-primary: #YOUR_COLOR;
    --color-primary-dark: #DARKER_SHADE;
    --color-primary-light: #LIGHTER_SHADE;
}
```

### Adjusting Spacing

Modify space variables:

```css
:root {
    --space-4: 1rem; /* Default */
    --space-4: 1.25rem; /* More spacious */
}
```

### Changing Font

Update typography in `:root`:

```css
:root {
    --font-family: 'Poppins', sans-serif;
}

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
```

---

## Support & Troubleshooting

### Common Issues

**Q: Menu not closing on mobile**
- Ensure `nav-menu` has `aria-controls` attribute
- Check JavaScript module initialization

**Q: Cards not animating**
- Verify `AnimationModule.init()` is called
- Check browser supports `IntersectionObserver`
- Ensure `animate-in` class is being added

**Q: Colors look different**
- Check for CSS specificity conflicts
- Verify CSS variables are loaded
- Test in incognito mode (no extensions)

**Q: Buttons not accessible**
- Add `aria-label` to icon buttons
- Ensure focus outline is visible
- Test with keyboard navigation

---

## Resources

- [MDN Web Docs](https://developer.mozilla.org)
- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Font Awesome Icons](https://fontawesome.com/icons)
- [Accessibility Insights](https://accessibilityinsights.io/)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Aug 2026 | Initial release |

---

## Contact & Feedback

For design system updates and contributions, please reach out to the LedgerMate team.

**Happy building! 🚀**
