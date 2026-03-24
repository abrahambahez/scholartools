# Design System: Brutalist Scholastic

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Radical Archivist."** 

This system moves away from the soft, organic textures of traditional editorial design and adopts a "Brutalist Scholastic" aesthetic. It is an intentional collision between the intellectual weight of a Renaissance manuscript and the raw, unyielding structure of a 90s underground zine. 

We break the "template" look by rejecting the standard "safe" UI tropes—shadows, rounded corners, and subtle borders are strictly forbidden. Instead, we lean into **structural aggression**. We use rigid, visible grids, thick black strokes, and high-density information layouts. The goal is to create an interface that feels like a technical manual rediscovered in a basement—functional, uncompromising, and intellectually rebellious.

---

## 2. Colors
The palette is a high-contrast dialogue between the past (Parchment) and a radical present (Oxblood and Solid Black).

*   **Primary (#610000 / #8B0000):** Our "Oxblood." Use this for key actions and critical emphasis. It represents the "Enlightened Rebel"—blood, ink, and passion.
*   **Surface/Background (#FCF9F0):** Our "Parchment." This provides a high-contrast, historical base that prevents the brutalism from feeling cold or purely digital.
*   **Structural Black (#000000):** Used for all borders, dividers, and "Zine-style" structural framing.

### The "Visible Skeleton" Rule
Unlike traditional systems that hide their structure, this system celebrates it. Prohibit the use of 1px borders or subtle sectioning. All containers must be defined by **2px to 4px solid black borders** (`on_background`). To separate content within a container, use a hard shift in background color (e.g., a `surface_container_high` block nested within a `surface` frame).

### Surface Hierarchy & Nesting
Hierarchy is achieved through "Tonal Inversion" and "Structural Stacking":
1.  **Level 0 (Base):** `surface` (#FCF9F0).
2.  **Level 1 (In-set Content):** `surface_container` (#F1EEE5) surrounded by a 2px black border.
3.  **Level 2 (High Density):** `surface_container_highest` (#E5E2DA) for technical data or code-like monospaced blocks.

**Note:** Never use Glassmorphism or Gradients. This system is tactile and opaque. It represents physical ink on heavy paper.

---

## 3. Typography
Typography is the primary engine of our brand identity, clashing the academic with the industrial.

*   **Display & Headline (Newsreader):** The "Renaissance Soul." Use these for large, expressive titles. It should feel authoritative, slightly archaic, and deeply human.
*   **Body & Labels (Space Grotesk / Monospace):** The "Zine Structure." All functional information, data, and UI labels must use the industrial-weight monospaced aesthetic. This creates a "Technical Manual" feel that contrasts the beauty of the headlines.

**Scale Philosophy:**
*   **Headlines:** Utilize `display-lg` (3.5rem) with tight tracking to create a "wall of text" impact.
*   **Information Density:** Use `label-sm` (0.6875rem) for metadata, wrapped in small black-bordered boxes to mimic a cataloging system.

---

## 4. Elevation & Depth
In a brutalist system, depth is a lie. We reject the "Z-axis" of traditional material design.

*   **The Flat-Stack Principle:** Depth is conveyed only through **thickness** and **layering**, never shadows. If an element needs to "pop," give it a heavier 4px border compared to the surrounding 2px borders.
*   **Zero Shadows:** The `elevation` tokens are replaced by `border-width` shifts. A "raised" card is simply a card with a thicker `on_background` stroke or a high-contrast background fill (e.g., Oxblood text on a Black background).
*   **No "Ghost Borders":** We do not use transparency to soften edges. Every line must be 100% opaque. If a boundary is needed, it is a hard black line or it does not exist.

---

## 5. Components

### Buttons
*   **Primary:** Solid Black (#000000) background, White (#FFFFFF) Monospaced text, 0px border-radius.
*   **Secondary:** Parchment (#FCF9F0) background, 2px Black border, Black Monospaced text.
*   **Interaction:** On hover, the button should "Invert" (Black becomes Oxblood or White) with zero transition time. It must feel instant and mechanical.

### Input Fields
*   **Styling:** A 2px solid black rectangle. No rounded corners.
*   **Labeling:** Labels should be placed in a "tab" format (a smaller black-bordered box) that sits directly on top of the input border, creating a blueprint-style appearance.

### Cards & Lists
*   **Structure:** Every card is a cell in a grid. Use visible `px` dividers (2px thick) to separate list items. 
*   **Spacing:** Use "Normal Spacing" (e.g., `spacing-2`) to maintain high information density while still allowing for structure. 

### Chips & Tags
*   **Design:** Rectangular boxes with 1px or 2px black borders. Use `label-sm` monospace font. They should look like stamped serial numbers on a document.

### Technical Data Tables
*   **Style:** High-density grids with every cell bordered. Use `surface_container_low` for headers to distinguish them from data rows.

---

## 6. Do's and Don'ts

### Do:
*   **Embrace the Grid:** Align elements to a rigid, visible grid. Let the vertical and horizontal lines show.
*   **Use Intentional Asymmetry:** Break a symmetrical layout by extending a black structural line to the edge of the viewport.
*   **Keep it Stark:** Use 0px border-radius on *everything*.
*   **Prioritize Legibility:** High contrast (Black on Parchment) is your greatest tool for accessibility.

### Don't:
*   **Do Not use Shadows:** Never use `box-shadow` or `drop-shadow`.
*   **Do Not use Softness:** No gradients, no blurs, and no rounded corners.
*   **Do Not use "Spacious" Spacing:** Avoid overly "breathable" layouts that feel like generic SaaS templates. The layout should feel "full" and "intentional," like a well-packed newspaper.
*   **Do Not use 1px Borders:** They feel "thin" and "default." Stick to the 2px-4px range for a deliberate, hand-inked feel.