# AGENTS.md - MTG Deck Builder (FastAPI + React)

## Project Overview
A local-first Magic: The Gathering deck builder with a FastAPI backend and a React (Vite) frontend. It builds decks from YAML configurations using the `mtg_deck_builder` library, analyzes results, and manages files under the project `data/` directory.

## Architecture Guidelines

### Core Components
- **Backend (FastAPI)**: REST API for deck building, analysis, file I/O, inventory, and configuration
- **Frontend (React + Vite)**: Modern UI with tabbed navigation, live YAML editor, deck viewer, and analysis
- **Database Layer (SQLAlchemy)**: SQLite with repository pattern and MTGJSON-derived models
- **YAML Deck Builder**: Configuration-driven pipeline with scoring, categories, mana base, and fallback logic
- **File Safety**: Safe path resolution so all reads/writes are confined to `data/*`

### Project Structure
```
MTGDecks/
├── backend/                   # FastAPI app and routers
│   ├── app.py                 # FastAPI app factory + router mounting
│   └── routers/               # API endpoints (build, arena import, configs, decks, inventory, snapshots)
├── frontend/                  # React app (Vite)
│   ├── src/
│   │   ├── App.tsx           # Main tabs + orchestration
│   │   └── panels/           # UI components (BuilderForm, DeckViewer, DeckAnalysis, etc.)
│   └── vite.config.ts        # Dev server + proxy to FastAPI
├── mtg_deck_builder/          # Core deck building logic
│   ├── db/                    # DB session, repositories, MTGJSON models
│   ├── models/                # Deck, DeckConfig, analyzers/exporters
│   └── yaml_builder/          # YAML builder pipeline and helpers
├── data/                      # Local data root (db, configs, decks, inventory, exports)
└── tests/                     # pytest suite
```

## Coding Standards

### Python Best Practices
- **Formatting**: Black (88 chars) and isort
- **Typing**: Full type hints; Pydantic v2 models for API/data contracts
- **Naming**: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_CASE` for constants
- **Docs**: Google-style docstrings for public APIs; concise comments explain “why”

### TypeScript/React Style
- Use function components with hooks
- Keep components focused; lift state to parents only as needed
- Prefer explicit prop types and narrow state
- Keep UI logic separate from data-fetching helpers
- Co-locate component styles; use CSS variables for themes

## Backend Guidelines (FastAPI)
- Dependency injection via `Depends` for config and DB URL/session
- All file I/O must use the safe-path utility and be rooted in `data/`
- Return structured JSON for deck build results: decklist, analysis, arena export, and optional debug context/logs
- Log meaningful build steps; expose debug summaries when `debug=true`
- Keep routers cohesive: `build`, `arena_import`, `configs`, `decks_fs`, `inventory_fs`, `snapshots`

## Database Guidelines (SQLAlchemy)
- Use the repository pattern for all data access
- Keep models in sync with schema; prefer relationships over manual joins
- SQLite for local dev; design queries for correctness first, optimize when needed
- Migrations via Alembic (planned)

## YAML Configuration System
- Validate YAML to `DeckConfig` before use
- Use `DeckBuildContext` to track selections, reasons, sources, and logs
- Categories must track targets; ensure scaling if targets exceed non-land slots
- Scoring drives selection; fallback fills below threshold when needed
- Mana base logic adds special lands and basic lands using mana symbol distribution

## Frontend Guidelines (React + Vite)
- **Vite Dev Server**: Use `npm run dev`; HMR enabled (proxy to FastAPI for `/api`)
- **Tabs**: Builder, Deck Viewer, Files, (Inventory as needed)
- **Builder**: Two-column form + live YAML editor; Build button; collapsible panels; debug log/context display
- **Deck Viewer**: Deck table with column selector, sorting, hover card preview, reasons/scores, Arena export copy, load/save
- **Deck Analysis**: Mana curve, type counts, rarity breakdown, color balance (local, no external APIs)
- **Files Panel**: List/read/write YAML and deck JSON in `data/`
- **UX**: Dark theme, tooltips, concise help text; avoid external calls unless explicitly enabled

## Testing Strategy
- **pytest** for backend and library logic
- Unit tests for YAML builder, repository filters, analyzers/exporters
- Sample YAML configs and inventories under `tests/sample_data/`
- Consider lightweight UI tests for critical flows (optional)

## Error Handling & Logging
- Use structured logs on the backend; include clear build-phase markers
- Return `HTTPException` with precise messages on validation failures
- In the builder, record `unmet_conditions`, `operations`, and `category_summary`
- Frontend surfaces backend errors and debug information in the UI

## Performance Considerations
- Query only necessary columns/relationships for summary cards
- Cache and reuse repository results when feasible
- Keep client bundles small; lazy-load heavy UI areas if needed

## Technology Stack
- **Python**: 3.12+
- **FastAPI** + **Uvicorn**
- **SQLAlchemy** + SQLite
- **Pydantic v2**
- **React 18** + **TypeScript** + **Vite**
- **js-yaml** for YAML parsing in UI

## Troubleshooting
- HMR works only with `npm run dev` on `http://localhost:5173` (proxy to FastAPI)
- Ensure venv is 3.12+ and packages installed from `requirements.txt`
- All app data must live under `data/`; safe-path rejects traversal
- If matplotlib isn’t installed, plotting helpers are optional and should not break backend imports

## API Guidelines
- RESTful endpoints with proper verbs/status codes
- JSON payloads and responses; Pydantic models where appropriate
- Consistent error structure; clear validation messages

## Deployment Notes
- Use `.env` or config files to set data roots/paths if needed
- Keep `node_modules` and venv out of version control (`.gitignore` updated)
- Consider building the React app and serving static files via FastAPI in production

## Contributing
- Use feature branches; keep commits small and focused
- Update docs when changing APIs or user flows
- Write tests for builder logic and critical routers
- Follow the style guidelines above for Python and React 