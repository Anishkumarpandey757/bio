# SensoryAssess Pro - AI-Assisted Sensory Integration Assessment System

## Overview

SensoryAssess Pro is a comprehensive web-based assessment platform designed for healthcare professionals to evaluate sensory processing in children aged 6-7 years. The system guides therapists through a structured multi-step assessment workflow, collecting demographic data, medical history, physical parameters, and exercise performance videos. The application emphasizes clinical clarity, data accuracy, and professional credibility with a healthcare-focused design system.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Framework:** React with TypeScript using Vite as the build tool

**UI Component Library:** Shadcn/ui (Radix UI primitives) with Tailwind CSS
- Material Design Healthcare variant for clinical credibility
- Custom design tokens for medical applications
- WCAG 2.1 AA accessibility compliance
- Typography: Inter for readability, Roboto Mono for clinical measurements

**State Management:**
- React Context API for global assessment state (`AssessmentContext`)
- TanStack React Query for server state management and API calls
- React Hook Form with Zod validation for form handling

**Routing:** Wouter (lightweight client-side routing)

**Form Validation:** 
- Zod schemas defined in shared layer for type-safe validation
- @hookform/resolvers for React Hook Form integration
- Drizzle-zod for database schema validation

**Multi-Step Workflow:**
- 9-step progressive disclosure pattern
- Step indicator component showing completion status
- Form state persisted in context across navigation
- Steps: Demographics → Medical History → Physical Parameters → Education → Caregiver → Therapist → Age Selection → Exercise Upload → Results

### Backend Architecture

**Runtime:** Node.js with Express.js server

**API Design:** RESTful endpoints
- POST/GET /api/assessments - Create and retrieve assessments
- CRUD operations for assessment data
- JSON request/response format

**Database Layer:**
- Drizzle ORM for type-safe database operations
- PostgreSQL as primary database (configured via DATABASE_URL)
- Connection pooling via node-postgres (pg)
- Schema-first approach with migrations in `/migrations` directory

**Build System:**
- ESBuild for server bundling (production)
- Vite dev server in development with HMR
- Selective dependency bundling to reduce cold start times
- Development middleware integration for seamless DX

**Session Management:**
- Express sessions configured (connect-pg-simple for PostgreSQL session store)
- Support for authentication patterns (passport infrastructure present)

### Data Model

**Core Entities:**

1. **Assessments** - Main assessment record
   - Demographic data (child name, gender, DOB, calculated age)
   - Birth/medical history (birth weight, complications, disabilities)
   - Physical parameters (height, weight, BMI auto-calculation)
   - Educational info (school enrollment, type, class)
   - Caregiver details (name, relation, contact)
   - Therapist info (name, profession, license, designation)
   - Age group selection (6-7 year ranges or other)
   - Exercise video data (9 exercise types)

2. **Users** - Healthcare professionals/therapists
   - Username-based authentication structure
   - Supports future multi-user scenarios

**Exercise Types:**
- Prone Extension
- Supine Flexion
- One Leg Standing (4 variations: left/right, eyes open/closed)
- Tandem Walking (eyes open/closed)
- Jumping Jacks

**Video Upload Workflow:**
- File upload with type validation (MP4, MOV)
- Client-side video trimming capability
- Status tracking: pending → uploading → uploaded → ready
- Blob URL generation for preview

### Report Generation

**PDF Export:**
- jsPDF library for document generation
- autoTable plugin for structured data tables
- Formatted sections: demographics, medical history, physical parameters, exercises
- Professional medical report styling
- Date formatting using date-fns

### Design System

**Color Tokens:**
- Primary: Clinical blue (HSL 203 87% 42%)
- Semantic colors for states (destructive, muted, accent)
- Light/dark mode support via CSS variables
- Card elevation system for visual hierarchy

**Spacing:** Tailwind utility-based (4px increments)

**Component Patterns:**
- Form sections with icons and descriptions
- Conditional field rendering based on user input
- Required/optional field labeling
- Navigation with back/next controls
- Loading and error states

## External Dependencies

### Core Libraries

**Frontend:**
- @tanstack/react-query - Server state management
- react-hook-form - Form handling
- zod - Runtime type validation
- wouter - Client-side routing
- date-fns - Date manipulation and formatting

**UI Components:**
- @radix-ui/* - Accessible primitive components (dialogs, dropdowns, forms, etc.)
- class-variance-authority - Component variant management
- tailwindcss - Utility-first CSS framework
- lucide-react - Icon library

**PDF Generation:**
- jspdf - PDF document creation
- jspdf-autotable - Table generation for PDFs

**Backend:**
- express - Web server framework
- drizzle-orm - Type-safe ORM
- pg (node-postgres) - PostgreSQL client
- drizzle-zod - Schema validation bridge

**Development:**
- typescript - Type safety
- vite - Frontend build tool and dev server
- tsx - TypeScript execution for Node.js
- esbuild - Production server bundling

### Database

**PostgreSQL** (provisioned via DATABASE_URL environment variable)
- Drizzle Kit for schema migrations
- Connection pooling for performance
- Session storage via connect-pg-simple

### Build & Deployment

**Replit-specific plugins:**
- @replit/vite-plugin-runtime-error-modal - Development error overlay
- @replit/vite-plugin-cartographer - Code navigation
- @replit/vite-plugin-dev-banner - Development indicators

### Typography

**Google Fonts:**
- Inter (weights: 300, 400, 500, 600, 700)
- Roboto Mono (weights: 400, 500)

### Path Aliases

- @/ → client/src/
- @shared/ → shared/
- @assets/ → attached_assets/