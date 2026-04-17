# MCP Anywhere - Landing Page

A premium landing page for MCP Anywhere, the unified gateway for Model Context Protocol servers.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 🎨 Design System

The landing page uses a token-based design system for easy customization.

### Design Tokens

All design tokens are defined in `design-system/design-system.json`:
- **Colors**: Dark theme with teal brand and violet accents
- **Typography**: Font families, sizes, and weights
- **Spacing**: 4px base spacing scale
- **Shadows**: Including glow effects for premium feel
- **Motion**: Duration and easing curves for animations

### CSS Variables

Tokens are mapped to CSS variables in `src/styles/tokens.css`. Use these variables in your components:

```css
/* Colors */
--bg-canvas
--bg-surface
--text-primary
--text-secondary
--brand-primary
--brand-hover

/* Spacing */
--space-1 through --space-24

/* Motion */
--duration-fast
--duration-normal
--duration-slow
--easing-ease-out
```

## 🧩 Component Structure

### Base Components (`src/components/`)
- **Button**: Primary, secondary, outline, ghost variants
- **Card**: Glassy cards with hover effects
- **Badge**: Pill-shaped labels
- **CodeBlock**: Syntax-highlighted code with copy button
- **Container**: Max-width content wrapper
- **Section**: Page section wrapper

### Page Sections (`src/sections/`)
- **Header**: Sticky navigation with logo
- **Hero**: Main headline with architecture diagram
- **ProblemSolution**: Problem/solution comparison
- **Features**: Feature grid with icons
- **HowItWorks**: Three-step process
- **Security**: Security features showcase
- **Integrations**: Integration logos
- **FAQ**: Interactive accordion
- **GetStarted**: Final CTA section
- **Footer**: Site footer with links

## 🎭 Animations

Animations are CSS-based for maximum performance. All animations respect `prefers-reduced-motion`.

### Available Animations
- `animate-fade-in`: Fade in with slight upward movement
- `animate-fade-in-scale`: Fade in with scale effect
- `animate-slide-in-left`: Slide in from left
- `animate-slide-in-right`: Slide in from right

### Delay Utilities
Add stagger effects with delay classes: `delay-100`, `delay-200`, etc.

## 🎯 Customization Guide

### Change Brand Colors

Edit `design-system/design-system.json`:

```json
{
  "theme": {
    "color": {
      "palette": {
        "brand": {
          "500": "#YOUR_COLOR"
        }
      }
    }
  }
}
```

Tokens automatically map to CSS variables. Rebuild to see changes.

### Modify Animations

Edit keyframes in `src/styles/globals.css`:

```css
@keyframes yourAnimation {
  from { /* start state */ }
  to { /* end state */ }
}
```

### Add New Sections

1. Create component in `src/sections/YourSection.tsx`
2. Import and add to `src/App.tsx`
3. Use base components for consistency

## 📱 Responsive Design

The layout is mobile-first and responsive:
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

Use utility classes:
- `md:grid-cols-2` - 2 columns on medium screens
- `md:flex-row` - Row layout on medium screens

## 🔧 Technical Stack

- **React 18**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool
- **Lucide React**: Icon library
- **CSS Variables**: Theming system

## 🏗️ Project Structure

```
mcp-anywhere/
├── design-system/
│   └── design-system.json    # Design token source of truth
├── src/
│   ├── assets/
│   │   └── images/
│   │       └── logo.png       # MCP Anywhere logo
│   ├── components/            # Reusable components
│   ├── sections/              # Page sections
│   ├── styles/
│   │   ├── tokens.css         # CSS variables from tokens
│   │   ├── globals.css        # Global styles & animations
│   │   └── components.css     # Component styles
│   ├── App.tsx                # Main app component
│   └── main.tsx               # Entry point
├── index.html                 # HTML template
├── vite.config.ts             # Vite configuration
└── tsconfig.json              # TypeScript configuration
```

## 🎨 Visual Features

### Premium AI Aesthetic
- Dark theme with deep navy background
- Animated gradient glows
- Glass morphism effects
- Strategic use of glow shadows
- Teal and violet accent colors

### Micro-interactions
- Button shimmer on hover
- Card lift with glow
- Smooth color transitions
- Accordion expand/collapse
- Navigation fade effects

### Architecture Diagram
- Interactive client-gateway-servers visualization
- Animated connection lines
- Pulsing gateway with glow
- Hover effects on components

## 🚀 Deployment

### Build for Production

```bash
npm run build
```

Output will be in `dist/` directory.

### GitHub Pages

The Vite config is set up for GitHub Pages deployment:

```typescript
export default defineConfig({
  base: '/',
  plugins: [react()]
})
```

Adjust `base` if deploying to a subdirectory.

## ♿ Accessibility

- Semantic HTML structure
- ARIA labels on interactive elements
- Keyboard navigation support
- Focus indicators visible
- Respects `prefers-reduced-motion`
- Proper heading hierarchy

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Test the build (`npm run build`)
5. Submit a pull request

## 📞 Support

- **GitHub**: [locomotive-agency/mcp-anywhere](https://github.com/locomotive-agency/mcp-anywhere)
- **Documentation**: Coming soon
- **MCP Spec**: [modelcontextprotocol.io](https://modelcontextprotocol.io)

---

Built with ❤️ by the community
