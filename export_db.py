"""Export the SQLite database to CSV files for external analysis."""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path


DB_PATH = Path("dekho.sqlite3")
DEFAULT_OUTPUT_DIR = Path("export")


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


def _export_table(connection: sqlite3.Connection, table_name: str, output_path: Path) -> int:
    cursor = connection.execute(f'SELECT * FROM "{table_name}"')
    column_names = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(column_names)
        writer.writerows(rows)

    return len(rows)


def export_database(db_path: Path, output_dir: Path) -> None:
    if not db_path.exists():
        print(f"Database not found: {db_path.resolve()}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    try:
        tables = _get_user_tables(connection)
        if not tables:
            print("No tables found in database.")
            return

        print(f"Exporting {db_path.resolve()} -> {output_dir.resolve()}")
        for table_name in tables:
            output_path = output_dir / f"{table_name}.csv"
            row_count = _export_table(connection, table_name, output_path)
            print(f"  {table_name}.csv ({row_count:,} rows)")
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export dekho SQLite tables to CSV files."
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for CSV files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help=f"Path to SQLite database (default: {DB_PATH})",
    )
    args = parser.parse_args()
    export_database(args.db, args.output_dir)


if __name__ == "__main__":
    main()
