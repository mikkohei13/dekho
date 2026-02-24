# Dekho

Music Track Database based on Flask, uv, and SQLite. Aims to help me to keep track of my music tracks generated in Suno. Most business logic will be in Flask, and frontend has only minimal vanilla JavaScript.

## Setup

To run the app, use:

```bash
uv run flask --app dekho run --reload
```

The app is available at http://127.0.0.1:5001

## Architecture

- **Backend:** Flask (`app.py`), serves HTML and a REST API
- **Database:** SQLite via Python's built-in `sqlite3`
- **Frontend:** Server-rendered Jinja2 templates with minimal vanilla JS
- **Dependencies:** Managed with uv (`pyproject.toml` / `uv.lock`)

## Database

The SQLite database contains primary data.

Table `tracks_file_data` has the following columns:
- track_id: string, primary key
- filepath: string
- title: string
- artist: string
- duration: float
- url: string
- date_created: datetime
- date_added: datetime

Table `track_remote_data` has the following columns:
- track_id: string, foreign key to `tracks_file_data.track_id`
- prompt: string
- tags: string
- negative_tags: string

Table `track_user_data` has the following columns:
- track_id: string, foreign key to `tracks_file_data.track_id`
- notes: string
- title_new: string

## Upcoming features (keep these in mind but **don't develop unless asked**)

- TBD

## Development principles

- Keep it simple
- This is one-person app, so avoid premature optimization
- No authentication

