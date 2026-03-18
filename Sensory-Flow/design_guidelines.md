# Design Guidelines: AI-Assisted Sensory Integration Assessment System

## Design Approach: Medical Design System
**Selected Framework:** Material Design Healthcare Variant with clinical modifications
**Rationale:** Healthcare applications demand clarity, structure, and professional trust. This assessment tool prioritizes data accuracy, workflow efficiency, and clinical credibility over visual flourishes.

## Core Design Principles
1. **Clinical Clarity:** Every element serves a functional purpose in the assessment workflow
2. **Progressive Disclosure:** Complex medical forms broken into digestible steps with clear progress indicators
3. **Professional Trust:** Visual design conveys medical credibility and data security
4. **Accessibility First:** WCAG 2.1 AA compliance for healthcare professionals working in various lighting conditions

## Typography System
**Primary Font:** Inter (Google Fonts) - excellent legibility for medical data
- **Headings:** 600 weight, sizes: 32px (h1), 24px (h2), 18px (h3)
- **Body Text:** 400 weight, 16px for form labels and content
- **Small Text:** 400 weight, 14px for helper text and descriptions
- **Data Display:** 500 weight, 16px for emphasizing medical values/results

**Secondary Font:** Roboto Mono (Google Fonts) - for displaying clinical measurements, BMI, age calculations

## Layout System
**Spacing Units:** Tailwind utilities - 4, 6, 8, 12, 16 units (p-4, m-6, gap-8, etc.)
**Container Strategy:**
- Form pages: max-w-4xl centered with generous padding
- Assessment exercise grid: max-w-6xl
- Report preview: max-w-5xl

**Grid Structure:**
- Multi-step forms: Single column for clarity, 2-column for related paired fields (height/weight)
- Exercise selection: 3-column grid on desktop (grid-cols-1 md:grid-cols-2 lg:grid-cols-3)
- Dashboard/results: 2-column layout (sidebar navigation + main content)

## Component Library

### Navigation & Progress
**Multi-Step Indicator:**
- Horizontal stepper showing: Demographics → Medical History → Physical Parameters → Education → Caregiver → Therapist → Age Selection → Exercise Upload → Results
- Completed steps: filled circle with checkmark icon
- Current step: outlined circle with bold text
- Upcoming steps: light outlined circles
- Breadcrumb below stepper showing current section name

**Header:**
- Fixed top navigation with app logo/name on left
- User/therapist info on right with logout option
- Subtle shadow for depth separation

### Form Elements
**Input Fields:**
- Clean rectangular inputs with subtle border
- Floating labels that move up when focused/filled
- Consistent height (h-12) for all text inputs
- Helper text below in smaller gray text
- Error states with red border and error icon

**Dropdown Selects:**
- Native select with custom styling
- Chevron down icon on right
- Same height as text inputs for visual consistency

**Date Pickers:**
- Calendar icon prefix
- DD/MM/YYYY format clearly indicated
- Material-style calendar overlay

**Conditional Fields:**
- Appear with smooth slide-down animation when triggered
- Indented slightly (ml-4) to show relationship to parent field
- Light background (gray-50) to distinguish dependent fields

**Auto-calculated Fields:**
- Read-only styling with different background (blue-50)
- Calculator icon prefix
- Bold value display

### Exercise Upload Interface
**Exercise Cards:**
- White cards with subtle shadow and border
- Exercise name with descriptive icon (Activity icon from Heroicons)
- Upload state indicator: Empty → Uploading → Trimming → Ready
- Video thumbnail preview once uploaded
- Action buttons: Upload, Trim, Replace, Remove

**Video Upload Area:**
- Large dashed border dropzone
- Upload cloud icon centered
- "Drag & drop or click to upload" text
- Supported formats clearly stated: "MP4, MOV (Max 500MB)"

**Video Trimmer:**
- Timeline scrubber with start/end handles
- Preview player above
- Duration display and trim controls
- "Save Trim" and "Cancel" buttons

### Results & Report Display
**Results Dashboard:**
- Summary cards showing exercise completion status
- 2-column grid layout for exercise results
- Each card shows: Exercise name, Score/Value, Status indicator
- Visual indicators: Green checkmark (completed), Yellow clock (processing), Red X (failed)

**Report Preview:**
- PDF-like white container with subtle shadow
- Header: Assessment title, date, therapist info
- Sections clearly separated with dividers
- Tabular data for demographic information
- Results displayed with labels and values in structured format
- Download button (prominent, top-right): "Download PDF Report" with download icon

### Buttons
**Primary Actions:** 
- Solid background, white text
- Icons paired with text (e.g., "Next Step" with arrow-right)
- h-12 height, px-6 horizontal padding
- Rounded corners (rounded-lg)

**Secondary Actions:**
- Outline style with border
- Same dimensions as primary

**Icon Buttons:**
- Square (w-10 h-10) for standalone icon actions
- Circular for floating actions

### Icons
**Library:** Heroicons (via CDN)
**Usage:**
- Form sections: Clipboard, Heart, Scale, Book, User, Briefcase icons
- Actions: Upload, Download, Play, Pause, Check, X, Pencil
- Status: CheckCircle (success), Clock (pending), XCircle (error)
- Navigation: ChevronRight, ChevronLeft, Home
- Size: w-5 h-5 for inline icons, w-6 h-6 for section headers

## Visual Hierarchy
**Page Structure:**
1. Page title (h1) with subtitle/description
2. Progress indicator (for multi-step flows)
3. Main content area with clear sections
4. Action buttons at bottom: Back (left), Next/Submit (right)

**Form Sections:**
- Section headers with icons
- Grouped fields with subtle background containers
- Mandatory fields marked with red asterisk
- Optional fields labeled "(Optional)" in gray

## Data Display Patterns
**Demographic Summary Cards:**
- White cards with border
- Icon on left, data on right
- Label-value pairs vertically stacked
- Use color coding sparingly: only for status indicators

**Assessment Results Table:**
- Alternating row backgrounds for readability
- Column headers with sort indicators (if applicable)
- Hover states on rows
- Score/value columns right-aligned

## Animations
**Minimal, Purposeful Motion:**
- Form validation: Subtle shake on error
- Modal overlays: Fade in with scale (200ms)
- Dropdown menus: Slide down (150ms)
- Page transitions: None (instant for clinical efficiency)
- Loading states: Simple spinner, no elaborate animations

## Images
**No hero images required.** This is a functional medical application. Use icons and structured layouts instead.

**Icons only for:**
- Exercise type visualization (stick figure illustrations if needed, sourced from medical icon libraries)
- Status indicators
- Form section headers

## Accessibility Requirements
- All form inputs have associated labels
- Error messages are announced to screen readers
- Keyboard navigation fully supported (Tab order, Enter to submit)
- Focus states clearly visible (blue ring)
- Color is never the only indicator of status
- Minimum touch target size: 44x44px for mobile
- Contrast ratios meet WCAG AA standards (4.5:1 for text)

## Responsive Behavior
**Desktop (lg: 1024px+):** Primary experience, full feature set
**Tablet (md: 768px):** 2-column grids become single column, sidebar navigation becomes hamburger
**Mobile:** Not primary target, but forms remain usable in single column layout

## Key Differentiators
- No decorative elements or marketing flourishes
- Focus on workflow efficiency over visual delight
- Clinical white space (not artistic whitespace)
- Professional medical aesthetic throughout
- Data integrity and clarity prioritized over engagement metrics