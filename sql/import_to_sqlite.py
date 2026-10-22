#!/usr/bin/env python3
"""Import the Heywhale MySQL dumps into a portable SQLite database."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
DB_PATH = PROJECT_DIR / "data" / "olist.sqlite"
SQL_FILES = [
    "olist_analysis_customers.sql",
    "olist_analysis_order_items.sql",
    "olist_analysis_orders.sql",
    "olist_analysis_payments.sql",
    "olist_analysis_products.sql",
    "olist_analysis_reviews.sql",
    "olist_analysis_sellers.sql",
]


def mysql_string_escapes_to_sqlite(statement: str) -> str:
    """Translate MySQL backslash escapes inside quoted literals to SQLite SQL."""
    out: list[str] = []
    i = 0
    in_string = False
    escapes = {
        "0": "\x00",
        "b": "\b",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "Z": "\x1a",
        "\\": "\\",
        '"': '"',
    }
    while i < len(statement):
        char = statement[i]
        if not in_string:
            out.append(char)
            if char == "'":
                in_string = True
            i += 1
            continue
        if char == "\\" and i + 1 < len(statement):
            next_char = statement[i + 1]
            decoded = escapes.get(next_char, next_char)
            # A decoded apostrophe must be doubled in a SQLite string literal.
            out.append("''" if decoded == "'" else decoded)
            i += 2
            continue
        out.append(char)
        if char == "'":
            # MySQL escapes apostrophes with backslash; doubled quotes can also occur.
            if i + 1 < len(statement) and statement[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            in_string = False
        i += 1
    return "".join(out)


def sqlite_create_table(mysql_ddl: list[str]) -> str:
    """Keep column and primary-key definitions, dropping MySQL-only indexes/options."""
    text = "\n".join(mysql_ddl)
    match = re.search(r"CREATE TABLE\s+`[^`]+`\s*\(.*?\)\s*ENGINE=.*?;", text, re.S)
    if not match:
        raise ValueError("Could not locate a MySQL CREATE TABLE statement")
    ddl = match.group(0)
    ddl = re.sub(r"\)\s*ENGINE=.*?;", ");", ddl, flags=re.S)
    lines = ddl.splitlines()
    body_start = next(i for i, line in enumerate(lines) if line.lstrip().startswith("CREATE TABLE"))
    body_lines: list[str] = []
    inside = False
    for line in lines[body_start:]:
        if "(" in line and not inside:
            inside = True
            body_lines.append(line)
            continue
        if not inside:
            continue
        if line.strip() == ");":
            while body_lines and body_lines[-1].rstrip().endswith(","):
                body_lines[-1] = body_lines[-1].rstrip()[:-1]
            body_lines.append(line)
            break
        if re.match(r"\s*(?:KEY|UNIQUE KEY|CONSTRAINT)\b", line, re.I):
            continue
        body_lines.append(line)
    if not body_lines or body_lines[-1].strip() != ");":
        raise ValueError("Could not rebuild SQLite CREATE TABLE statement")
    return "\n".join(body_lines)


def import_file(conn: sqlite3.Connection, path: Path) -> tuple[str, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    ddl_lines: list[str] = []
    in_ddl = False
    inserts = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("CREATE TABLE"):
            in_ddl = True
            ddl_lines = [line]
            continue
        if in_ddl:
            ddl_lines.append(line)
            if re.search(r"\)\s*ENGINE=.*?;\s*$", line):
                conn.execute(sqlite_create_table(ddl_lines))
                in_ddl = False
            continue
        if not stripped or stripped.startswith("--") or stripped.startswith("/*!"):
            continue
        if stripped.startswith(("LOCK TABLES", "UNLOCK TABLES", "ALTER TABLE")):
            continue
        if stripped.startswith("DROP TABLE"):
            conn.execute(stripped.replace("`", ""))
            continue
        if stripped.startswith("INSERT INTO"):
            statement = mysql_string_escapes_to_sqlite(stripped.replace("`", ""))
            conn.execute(statement)
            inserts += 1
    table_match = re.search(r"olist_analysis_(.+)\.sql$", path.name)
    table = table_match.group(1) if table_match else path.stem
    return table, inserts


def main() -> None:
    missing = [name for name in SQL_FILES if not (RAW_DIR / name).is_file()]
    if missing:
        raise SystemExit("Missing SQL files: " + ", ".join(missing))
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    try:
        for name in SQL_FILES:
            with conn:
                table, inserts = import_file(conn, RAW_DIR / name)
            count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            print(f"{table}: {count:,} rows ({inserts} insert batches)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_customers_customer_unique_id ON customers(customer_unique_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_payments_order_id ON payments(order_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_reviews_order_id ON reviews(order_id)")
        conn.commit()
    finally:
        conn.close()
    print(f"Database: {DB_PATH} ({DB_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
