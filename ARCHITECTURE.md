# Technical & architecture notes

## Fetching metadata from Suno

Metadata are fetched server-side from public Suno track pages by parsing Next.js Flight payloads embedded in `self.__next_f.push(...)` script tags.

- Input: track URL from DB (`tracks_file_data.url`).
- Fetch: raw HTML via `urllib.request` with a browser-like user agent.
- Decode: each `self.__next_f.push([..., "<escaped>"])` payload is unescaped with JSON string decoding.
- Parse:
  - payload lines with JSON fragments (`n:[...]` / `n:{...}`) are parsed and walked recursively,
  - a content candidate node is selected for `prompt` / `tags` / `negative_tags`,
  - a model candidate node is selected independently for `major_model_version` / `model_name`.
- Prompt resolution:
  - if prompt is a token like `$25` or `$3e`, it is resolved through Flight text references (alphanumeric IDs supported),
  - collected from either:
    1) inline ref format: `25:Txxxx,<text...>` (text starts on same line/chunk), or
    2) marker + next chunk format: `25:Txxxx,` followed by a separate decoded chunk containing the text body.
  - validity gate: if resolved prompt still starts with `$` or is shorter than 5 characters, fallback lyric detection is attempted.
- Lyrics fallback (when prompt looks invalid):
  - scans decoded Flight text chunks and collected text refs for lyric-like candidates,
  - scores by stanza markers in `[]` or `()`, newline count, and text length (typically hundreds of characters),
  - returns best candidate only when confidence threshold is met,
  - otherwise returns literal `"failed"` (safe failure, no exception).
- Model field resolution order:
  1) best model candidate node,
  2) selected content candidate node,
  3) nested `metadata` object.
- Output: `{prompt, tags, negative_tags, has_cover_clip_id, major_model_version, model_name, persona_name}` with missing fields as `None`.
- Persistence: values are upserted into `track_remote_data` and merged back into the track details API response.

### Supported cases now

- Full metadata present (lyrics prompt, tags, negative_tags).
- Partial metadata (any subset of those fields).
- Prompt as plain text directly in metadata.
- Prompt as $<id> reference with:
  - inline T text payload, or
  - marker-only ref followed by a separate text chunk.
- Alphanumeric prompt refs (for example `$1e`, `$3e`).
- Invalid/short prompt fallback to lyric-like candidate extraction.
- Low-confidence fallback path returning `"failed"` instead of crashing.
- Model fields living on a different node than prompt/tags.
- Missing `negative_tags`.

### Important limitation

- The parser depends on Next.js Flight payloads in `self.__next_f.push(...)` script tags.
- Non-Flight snapshots (for example text-only exports) do not contain those payloads and correctly return `Suno metadata not found on track page.`

## Labels

- Source of truth is `dekho/labels.py` (`LABEL_CATALOG`): each label has a stable `key`, `category`, and display `label`.
- On startup, `init_db()` seeds `label_definitions` from catalog with upsert-by-key (`key` is unique). This does not delete old keys that were removed from LABEL_CATALOG.
- Track assignments are stored in `track_user_data_labels` (`track_id`, `label_id`) and saved via `POST /api/tracks/<track_id>/user-data`.
- API payload uses label keys (`labels: string[]`), validated against current catalog (`normalize_label_keys`).
- Track filtering is key-based via `POST /api/tracks/filter-by-labels`; SQL returns tracks that contain all selected labels.
- Safety check: index route (`/`) returns plain-text error instead of UI if DB has assigned label keys not present in current `LABEL_CATALOG`.

## Track list synchronization

- The left sidebar (`#tracks-list`) is updated through one client-side projection function: `renderTrackListItem(trackId, data)` in `dekho/static/scripts/index/render-track-list.js`.
- `renderTrackListItem` is the single path used after:
  - loading track details (`GET /api/tracks/<track_id>`),
  - saving user data (`POST /api/tracks/<track_id>/user-data`),
  - fetching Suno metadata (`POST /api/tracks/<track_id>/remote-data`).
- The function projects the API payload into sidebar UI fields (title, remote-tag indicator, labels, tags text), then reapplies filters.
- Row DOM uses `data-track-item-*` selectors (`data-track-item-title`, `data-track-item-display-title`, `data-track-item-tags`, `data-track-item-labels`) so new sidebar fields can be added by extending this projection in one place.

## Module map

- `dekho/app.py`: HTTP route registration, request validation, JSON/template responses.
- `dekho/db.py`: repository read/write functions for tracks, labels, and metadata.
- `dekho/db_schema.py`: SQL schema/index creation, called by `init_db()`.
- `dekho/scan.py`: scan orchestration and artifact generation.
- `dekho/remote_metadata.py`: Suno page parser and metadata extraction.
- `dekho/static/scripts/index/main.js`: frontend entrypoint orchestration.
- `dekho/static/scripts/index/api.js`: frontend API request wrappers.
- `dekho/static/scripts/index/state.js`: frontend mutable UI state and guard helpers.
- `dekho/static/scripts/index/render-track-list.js`: sidebar rendering/filter projection.
- `dekho/static/scripts/index/render-track-details.js`: details panel rendering and player header updates.

## API contracts

- `GET /api/tracks/<track_id>`
  - `200`: track payload with `track_id`, file/user/remote fields, `labels`, and `label_catalog`.
  - `404`: `{ "error": "Track not found" }`.
- `POST /api/tracks/<track_id>/user-data`
  - request: `{ "title_new": string, "notes": string, "labels": string[] }`.
  - `200`: updated track payload (same shape as GET details route).
  - `400`: validation errors for wrong types/unknown labels.
  - `404`: track not found.
- `POST /api/tracks/<track_id>/remote-data`
  - request body optional/ignored.
  - `200`: updated track payload (same shape as GET details route).
  - `400`: track URL missing or parser/domain validation errors.
  - `502`: upstream fetch/parsing failure.
- `POST /api/tracks/filter-by-labels`
  - request: `{ "labels": string[] }`.
  - `200`: `{ "track_ids": string[] }`.
  - `400`: label validation errors.

## Refactor safety workflow

- Change the contract first (route payload, DB shape, or frontend projection).
- Update/extend tests that lock that contract.
- Update direct callers (`main.js` and route handlers) last.
- Prefer helper extraction and file moves before behavioral changes.
