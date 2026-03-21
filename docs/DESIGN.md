# Design System Strategy: The Bold Editorial

## 1. Overview & Creative North Star
**Creative North Star: "The Neo-Brutalist Editor"**

This design system is not a standard corporate interface; it is a high-impact, editorial-first experience. It draws inspiration from modern poster design and neo-brutalist digital trends, prioritizing clarity through extreme contrast and intentional asymmetry. 

While many modern systems strive for "softness," this system embraces "intent." We break the typical "template" look by using exaggerated corner radii (`xl: 3rem`), heavy 2px strokes, and a stark tonal palette. By overlapping illustrative elements with structured containers and utilizing high-contrast typography scales, we create a rhythmic, tactile environment that feels both professional and rebellious.

---

## 2. Colors & Surface Strategy
The palette is built on a foundation of absolute high contrast. The interplay between Deep Charcoal (`#191A23`) and Lime Green (`#B9FF66`) creates an energetic tension that demands attention.

### Color Tokens
*   **Primary (Action):** `primary: #3f6900` | `primary_container: #B9FF66` (The Signature Lime)
*   **Neutral (Foundation):** `surface: #fbf8ff` | `on_surface: #1a1b24`
*   **Secondary:** `secondary: #5d5d68` (Used for subtle UI meta-data)

### The "No-Line" Rule for Layout
To maintain a high-end editorial feel, **prohibit 1px solid borders for sectioning.** Large layout blocks must be defined by background color shifts alone. For example, a `surface_container_low` section should sit directly against a `surface` background. This creates "visual air" and prevents the UI from looking cluttered or like a generic wireframe.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. 
1.  **Base:** `surface` (The canvas)
2.  **Sectioning:** `surface_container_low` or `primary_container` (Large content blocks)
3.  **Components:** `surface_container_lowest` (Cards)

### Signature Textures
Avoid 100% flat presentation on hero elements. Use subtle gradients transitioning from `primary` to `primary_container` on high-value CTAs or illustrative backgrounds to provide a "soulful" polish that simple flat hex codes cannot achieve.

---

## 3. Typography
The typographic system is designed to be the primary structural element of the brand.

*   **Display & Headlines (Space Grotesk):** These are your "vocal" elements. Use `display-lg` (3.5rem) for hero statements. The tight kerning and geometric shapes of Space Grotesk convey authority.
*   **Titles & Body (Inter):** Inter provides the functional "silence" required for readability. Use `title-lg` (1.375rem) for card headers to ensure clear information architecture.
*   **The Highlight Pattern:** Always use a `primary_container` (Lime) background behind `headline` or `title` text for section headings to create a "marker highlight" effect, reinforcing the editorial aesthetic.

---

## 4. Elevation & Depth
In this system, depth is achieved through **Tonal Layering** and physical strokes rather than traditional skeuomorphic shadows.

### The Layering Principle
Place `surface_container_lowest` cards on `surface_container_low` sections. This creates a soft, natural lift. 

### Ambient Shadows
When an element must "float" (e.g., a dropdown or a high-priority modal), use an extra-diffused shadow:
*   **Blur:** 24px - 40px
*   **Opacity:** 4% - 8%
*   **Color:** Use a tinted version of `on_surface` (deep navy/charcoal) rather than pure black to mimic natural light.

### The "Ghost Border" Fallback
High-contrast 2px black borders are a signature component style. However, if a UI element requires a subtle boundary for accessibility (like a disabled input), use a **Ghost Border**: the `outline_variant` token at 20% opacity.

### Glassmorphism
For floating navigation bars or overlay tags, use backdrop blurs (10px+) with semi-transparent `surface` colors. This prevents the UI from feeling "pasted on" and allows the vibrant Lime Green and Deep Charcoal to bleed through the interface.

---

## 5. Components

### Buttons & Pills
*   **Primary:** Pill-shaped (`full` roundedness), `primary_container` background, 2px black border. Text in `on_surface`.
*   **Secondary:** Pill-shaped, `on_surface` background, white text. No border.
*   **States:** On hover, primary buttons should shift their background to `primary_fixed_dim`.

### Cards (The "Editorial Container")
*   **Style:** `xl` (3rem/45px) rounded corners, 2px solid `on_surface` border.
*   **Content Separation:** Forbid divider lines. Use vertical white space (`spacing.8` or `spacing.10`) to separate headers from body text.
*   **Variants:** Alternate between `surface_container_lowest`, `primary_container`, and `on_surface` (with white text) to create a rhythmic scroll.

### Chips & Badges
*   **Style:** Pill-shaped, `primary_container` background.
*   **Usage:** Use for categories, tags, or "Services" labels. Always accompanied by `label-md` typography.

### Input Fields
*   **Style:** `sm` (0.5rem) rounded corners, 2px `on_surface` border. 
*   **Interaction:** Focus state should trigger a `primary_container` (Lime) "Ghost Border" or a subtle 2px offset shadow.

### Icons & Graphics
*   **Library:** Use `lucide-react` for all functional iconography.
*   **Style:** Flat, illustrative, and geometric. Use a combination of thick black outlines (`stroke-width: 2.5`) and blocks of Lime Green. Icons should feel like "stickers" placed on the UI.
*   **Sizing:** Prefer `20px` to `32px` depending on context (Metrics use `32px`, headers use `20px`).
*   **Replacement Policy:** Strictly forbid the use of emojis for UI elements. All visual markers must be imported from the icon library.

---

## 6. Do's and Don'ts

### Do:
*   **Do** use asymmetrical layouts. A card on the left can be slightly larger than its neighbor on the right to guide the eye.
*   **Do** use the Spacing Scale strictly. `spacing.16` (5.5rem) is your friend for hero section padding.
*   **Do** overlap illustrative icons over the edges of containers to break the "grid box" feel.

### Don't:
*   **Don't** use 1px borders. If it needs a line, make it 2px and intentional.
*   **Don't** use standard grey shadows. They muddy the high-contrast lime-and-charcoal aesthetic.
*   **Don't** use divider lines in lists. Use `surface` color shifts or generous white space to define rows.
*   **Don't** use center-alignment for long-form body text. Keep it editorial: left-aligned for authority and readability.