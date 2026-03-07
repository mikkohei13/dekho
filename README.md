# Dekho

Music Track Database based on Flask, uv, and SQLite. Aims to help me to keep track of music tracks generated in Suno. Most business logic is in Flask, and frontend has only minimal vanilla JavaScript.

Features:
- Shows a list of tracks with their metadata.
- Scans music folder and updates the database (table tracks_file_data)
- Allows user to fetch remote data (table track_remote_data).
- Allows user to edit track metadata (table track_user_data).
- Allows user to add labels to tracks (table track_user_data_labels). Labels are defined in the `labels.py` file.

## Setup

To run the app, use:

```bash
uv run flask --app dekho run --reload
```

The app is available at http://127.0.0.1:5000

## Architecture

- **Backend:** Flask (`app.py`), serves HTML and a REST API
- **Database:** SQLite via Python's built-in `sqlite3`
- **Frontend:** Server-rendered Jinja2 templates with vanilla JS modules in `dekho/static/scripts/index/`
- **Dependencies:** Managed with uv (`pyproject.toml` / `uv.lock`)

## Technical overview

See more details in `ARCHITECTURE.md`.

- **App shape:** One Flask app (`create_app`) serves the main page, scan page, and JSON API routes under `/api/*`.
- **Core backend modules:**
  - `dekho/app.py`: route handlers, request validation, file serving.
  - `dekho/db.py`: repository-style DB reads/writes for track, user, remote, and label data.
  - `dekho/db_schema.py`: SQLite schema/index creation used by `init_db()`.
  - `dekho/scan.py`: scan pipeline (discover files, deduplicate, extract metadata, upsert DB, generate artifacts).
  - `dekho/remote_metadata.py`: parser for Suno track page metadata.
- **Frontend modules:**
  - `dekho/templates/index.html`: HTML shell + server-injected bootstrap data.
  - `dekho/static/scripts/index/main.js`: entrypoint orchestration.
  - `dekho/static/scripts/index/api.js`, `state.js`, `events.js`, `render-track-list.js`, `render-track-details.js`: API calls, state management, event wiring, and UI rendering.
- **Request/data flow:**
  1. `/` renders track list from SQLite data.
  2. Frontend loads track details via `/api/tracks/<track_id>`.
  3. User edits are saved to `/api/tracks/<track_id>/user-data`.
  4. Remote enrichment is fetched via `/api/tracks/<track_id>/remote-data`.
  5. `/scan` runs filesystem sync and updates stored metadata/artifacts.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```

## Database

Use this command to get more information about the database:

```bash
uv run dev_db_summary.py
```

- label_definitions
  • id (INTEGER, NULL PK)
  • key (TEXT, NOT NULL)
  • category (TEXT, NOT NULL)
  • label (TEXT, NOT NULL)

- track_remote_data
  • track_id (TEXT, NULL PK)
  • prompt (TEXT, NULL)
  • tags (TEXT, NULL)
  • negative_tags (TEXT, NULL)
  • has_cover_clip_id (INTEGER, NOT NULL)
  • major_model_version (TEXT, NULL)
  • model_name (TEXT, NULL)
  • persona_name (TEXT, NULL)
  • FKs: track_id -> tracks_file_data.track_id

- track_user_data
  • track_id (TEXT, NULL PK)
  • notes (TEXT, NULL)
  • title_new (TEXT, NULL)
  • FKs: track_id -> tracks_file_data.track_id

- track_user_data_labels
  • track_id (TEXT, NOT NULL PK)
  • label_id (INTEGER, NOT NULL PK)
  • FKs: label_id -> label_definitions.id, track_id -> track_user_data.track_id

- tracks_file_data
  • track_id (TEXT, NULL PK)
  • filepath (TEXT, NULL)
  • title (TEXT, NULL)
  • artist (TEXT, NULL)
  • duration (REAL, NULL)
  • url (TEXT, NULL)
  • date_created (TEXT, NULL)
  • date_added (TEXT, NULL)

## Upcoming features (keep these in mind but **don't develop unless asked**)

- Label: make cover
- Show player only when a track is selected
- Styling
    - track header fix
    - track listing styles
    - liquid glass with blurred background?
- Show description in track listing, allowing to filter by it
- Show filters on navbar, keep all labels visible
- Show track label selection in the same order as they are in the catalog

## Development principles

- Keep it simple
- This is one-person app, so avoid premature optimization
- Add unit tests to ./tests for the most important features
- Avoid unnecessary complexity:
  - No accessibility features
  - No authentication
  - Desktop-optimized UI, no mobile support
  - No JavaScript frameworks
