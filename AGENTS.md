## Development principles

- Keep it simple
- This is one-person app, so avoid premature optimization
- Add unit tests to ./tests for the most important features
- Avoid unnecessary complexity:
  - No accessibility features
  - No authentication
  - Desktop-optimized UI, no mobile support
  - No JavaScript frameworks

Use this command to get more information about the database:

```bash
uv run dev_db_summary.py
```

Run tests with:

```bash
uv run -m unittest discover -s tests -v  
```