# Technical & architecture notes

## Fetching lyrics from Suno

Lyrics are fetched server-side from public Suno track pages by parsing Next.js Flight payloads embedded in self.__next_f.push(...) script tags.

- Input: track URL from DB (tracks_file_data.url).
- Fetch: raw HTML via urllib.request with a browser-like user agent.
- Decode: each self.__next_f.push([..., "<escaped>"]) payload is unescaped with JSON string decoding.
- Parse:
  - payload lines with JSON fragments (n:[...] / n:{...}) are parsed and walked recursively,
  - best metadata node containing any of prompt, tags, negative_tags is selected (fields are optional).
- Prompt resolution:
  - if prompt is a token like $25, it is resolved through Flight text references,
  - collected from either:
    1) inline ref format: 25:Txxxx,<text...> (text starts on same line/chunk), or
    2) marker + next chunk format: 25:Txxxx, followed by a separate decoded chunk containing the text body.
- Output: {prompt, tags, negative_tags} with missing fields as None.
- Persistence: values are upserted into track_remote_data and merged back into the track details API response.

### Supported cases now

- Full metadata present (prompt, tags, negative_tags).
- Partial metadata (any subset of those fields).
- Prompt as plain text directly in metadata.
- Prompt as $<id> reference with:
  - inline T text payload, or
  - marker-only ref followed by a separate text chunk.
- Missing negative_tags

## Labels

- Source of truth is `dekho/labels.py` (`LABEL_CATALOG`): each label has a stable `key`, `category`, and display `label`.
- On startup, `init_db()` seeds `label_definitions` from catalog with upsert-by-key (`key` is unique).
- Track assignments are stored in `track_user_data_labels` (`track_id`, `label_id`) and saved via `POST /api/tracks/<track_id>/user-data`.
- API payload uses label keys (`labels: string[]`), validated against current catalog (`normalize_label_keys`).
- Track filtering is key-based via `POST /api/tracks/filter-by-labels`; SQL returns tracks that contain all selected labels.
- Safety check: index route (`/`) returns plain-text error instead of UI if DB has assigned label keys not present in current `LABEL_CATALOG`.
