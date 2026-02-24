---
name: db-schema-summary
description: Inspects this app's database schema by running a local summary command. Use when database table/column structure or schema details are needed.
---

# DB Schema Summary

## Instructions

When the task needs database structure details (tables, columns, types, nullable/default info), run:

```bash
uv run dev_db_summary.py
```

Use the command output as the source of truth for schema-level answers.

## When To Use

- User asks about database schema, tables, columns, or field details.
- You need quick DB context before writing or reviewing DB-related code.
- You need to verify table/column names to avoid guessing.

## Notes

- Run from the repository root so the script resolves correctly.
- If the command fails, report the error and ask the user before trying alternatives.
