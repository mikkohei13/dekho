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
- **Frontend:** Server-rendered Jinja2 templates with minimal vanilla JS
- **Dependencies:** Managed with uv (`pyproject.toml` / `uv.lock`)

## Database

Use this command to get more information about the database:

```bash
uv run dev_db_summary.py
```

- tracks_file_data
  • track_id (TEXT, NULL PK)
  • filepath (TEXT, NULL)
  • title (TEXT, NULL)
  • artist (TEXT, NULL)
  • duration (REAL, NULL)
  • url (TEXT, NULL)
  • date_created (TEXT, NULL)
  • date_added (TEXT, NULL)

- track_remote_data
  • track_id (TEXT, NULL PK)
  • prompt (TEXT, NULL)
  • tags (TEXT, NULL)
  • negative_tags (TEXT, NULL)
  • FKs: track_id -> tracks_file_data.track_id

- track_user_data
  • track_id (TEXT, NULL PK)
  • notes (TEXT, NULL)
  • title_new (TEXT, NULL)
  • FKs: track_id -> tracks_file_data.track_id

- label_definitions
  • id (INTEGER, NULL PK)
  • key (TEXT, NOT NULL)
  • category (TEXT, NOT NULL)
  • label (TEXT, NOT NULL)

- track_user_data_labels
  • track_id (TEXT, NOT NULL PK)
  • label_id (INTEGER, NOT NULL PK)
  • FKs: label_id -> label_definitions.id, track_id -> track_user_data.track_id

## Upcoming features (keep these in mind but **don't develop unless asked**)

- Add label like0 = set as not liked
- Try tpo get more metadata from Suno, e.g. persona and version, cover boolean, cover id
- Styling
    - track header fix
    - track listing styles
    - show stars in track listing track titles
    - liquid glass with blurred background?
- Show description in track listing, allowing to filter by it
- Show filters on navbar, keep all labels visible
- Show track label selection in the same order as they are in the catalog
- Improve UI design
- Add labels to tracks (e.g. "good", "bad")
- Add genres to tracks
- Add player that keeps always open on the bottom

## Development principles

- Keep it simple
- This is one-person app, so avoid premature optimization
- No accessibility features
- No authentication
- Desktop-optimized UI, no mobile support
- No JavaScript frameworks
