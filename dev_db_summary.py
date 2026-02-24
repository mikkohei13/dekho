"""Print a compact development summary of the SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("dekho.sqlite3")


def _get_user_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def _format_column(column: sqlite3.Row) -> str:
    nullable = "NOT NULL" if column["notnull"] else "NULL"
    pk = " PK" if column["pk"] else ""
    declared_type = column["type"] or "ANY"
    return f"{column['name']} ({declared_type}, {nullable}{pk})"


def main() -> None:
    resolved_db_path = DB_PATH.resolve()
    print("=== DB Summary ===")
    print(f"Path: {resolved_db_path}")

    if not DB_PATH.exists():
        print("Status: missing (no database file yet)")
        return

    print(f"Size: {DB_PATH.stat().st_size:,} bytes")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        sqlite_version = connection.execute("SELECT sqlite_version()").fetchone()[0]
        print(f"SQLite: {sqlite_version}")

        tables = _get_user_tables(connection)
        print(f"Tables: {len(tables)}")

        for table_name in tables:
            row_count = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"\n- {table_name} ({row_count:,} rows)")

            columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            for column in columns:
                print(f"  • {_format_column(column)}")

            foreign_keys = connection.execute(
                f"PRAGMA foreign_key_list({table_name})"
            ).fetchall()
            if foreign_keys:
                formatted_fks = ", ".join(
                    f"{fk['from']} -> {fk['table']}.{fk['to']}" for fk in foreign_keys
                )
                print(f"  • FKs: {formatted_fks}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
