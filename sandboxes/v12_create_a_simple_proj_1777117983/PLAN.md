# Project: Todo List Application

## Goal
To create a functional, clean-architecture-based ToDo List application using Next.js, ensuring proper file structure and data handling.

## Architecture
The application will follow a modern Next.js structure, utilizing the `/app` directory for routing and strict file extensions (`.tsx` for components, `route.ts` for API endpoints). Data persistence will be handled via a dedicated database layer (`lib/db.ts`) adhering to Clean Architecture principles.

## File Structure
- app/layout.tsx — Defines the root layout and structure for the application.
- app/page.tsx — The main page component, responsible for rendering the UI and handling user interaction.
- lib/db.ts — Database abstraction layer, handling all data persistence logic.

- NEXT.js RULE: If building a Next.js app, strictly use the `/app` router. NEVER list `pages/` directory files if `app/` is present.
- EXTENSION RULE: For Next-js projects, always use `.tsx` for files in the `app/` directory and `route.ts` for `api/` files.
- FEATURE COMPLETENESS RULE: The structure explicitly lists the required modules for complex features (like DB, login, or dashboards) to ensure implementation completeness.

## Implementation Role Mapping
- `code_architect`: Overall structure, layouts, and entry points.
- `researcher`: Documentation and complex grounding (e.g., architectural decisions).
- `api_integration`: API routes, networking, and security logic.
- `data_analysis`: Database schemas, queries, and logic.

If a step primarily requires tools over code, specify `[TOOL: searcher]`.