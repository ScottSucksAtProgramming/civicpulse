#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

FAILURE_TYPES = (
    "zero_results",
    "low_score",
    "no_citation",
    "pii_refusal",
    "evaluative_redirect",
)


def db_path() -> Path:
    vault_path = Path(os.getenv("CIVICPULSE_VAULT_PATH", "./vault"))
    return vault_path / ".index.db"


def fetchall(con: sqlite3.Connection, query: str, params: tuple = ()) -> list[sqlite3.Row]:
    try:
        return list(con.execute(query, params))
    except sqlite3.OperationalError:
        return []


def scalar(con: sqlite3.Connection, query: str, params: tuple = (), default=0):
    rows = fetchall(con, query, params)
    if not rows:
        return default
    value = rows[0][0]
    return default if value is None else value


def percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def print_query_volume(con: sqlite3.Connection) -> None:
    print("1. Query Volume")
    total = scalar(con, "SELECT COUNT(*) FROM query_log")
    if total == 0:
        print("No query_log data.")
        print()
        return

    print(f"Total queries: {total}")
    print("By day:")
    for row in fetchall(
        con,
        """
        SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS count
        FROM query_log
        GROUP BY day
        ORDER BY day
        """,
    ):
        print(f"- {row['day']}: {row['count']}")
    print()


def print_top_document_types(con: sqlite3.Connection) -> None:
    print("2. Top Document Types")
    rows = fetchall(
        con,
        """
        SELECT COALESCE(document_type, '(none)') AS document_type, COUNT(*) AS count
        FROM query_log
        GROUP BY document_type
        ORDER BY count DESC, document_type
        LIMIT 10
        """,
    )
    if not rows:
        print("No query_log data.")
        print()
        return
    for row in rows:
        print(f"- {row['document_type']}: {row['count']}")
    print()


def print_failure_breakdown(con: sqlite3.Connection) -> None:
    print("3. Failure Breakdown")
    counts = {
        row["failure_type"]: row["count"]
        for row in fetchall(
            con,
            """
            SELECT failure_type, COUNT(*) AS count
            FROM unanswered_log
            GROUP BY failure_type
            """,
        )
    }
    if not counts:
        print("No unanswered_log data.")
    for failure_type in FAILURE_TYPES:
        label = failure_type
        if failure_type == "no_citation":
            label = "no_citation (citation-proxy (not semantic grounding check))"
        print(f"- {label}: {counts.get(failure_type, 0)}")
    for failure_type in sorted(set(counts) - set(FAILURE_TYPES)):
        print(f"- {failure_type}: {counts[failure_type]}")
    print()


def print_letter_flow(con: sqlite3.Connection) -> None:
    print("4. Letter Flow")
    suggestions = scalar(
        con,
        "SELECT COUNT(*) FROM draft_log WHERE event_type = 'suggestion'",
    )
    generations = scalar(
        con,
        "SELECT COUNT(*) FROM draft_log WHERE event_type = 'generation'",
    )
    print(f"Suggestions: {suggestions}")
    print(f"Generations: {generations}")
    print(f"Completion rate: {percent(generations, suggestions)}")
    print()


def print_soapbox_topics(con: sqlite3.Connection) -> None:
    print("5. Soapbox Topics")
    rows = fetchall(
        con,
        """
        SELECT topic, COUNT(*) AS count
        FROM soapbox_log
        GROUP BY topic
        ORDER BY count DESC, topic
        LIMIT 10
        """,
    )
    if not rows:
        print("No soapbox_log data.")
        print()
        return
    for row in rows:
        print(f"- {row['topic']}: {row['count']}")
    print()


def print_scraper_health(con: sqlite3.Connection) -> None:
    print("6. Scraper Health")
    rows = fetchall(
        con,
        """
        WITH latest AS (
            SELECT source_name, error_type
            FROM scraper_log AS s
            WHERE timestamp = (
                SELECT MAX(timestamp)
                FROM scraper_log
                WHERE source_name = s.source_name
            )
        )
        SELECT
            s.source_name,
            COUNT(*) AS run_count,
            SUM(CASE WHEN s.error_type IS NULL THEN 0 ELSE 1 END) AS failure_count,
            latest.error_type AS most_recent_error
        FROM scraper_log AS s
        JOIN latest ON latest.source_name = s.source_name
        GROUP BY s.source_name
        ORDER BY s.source_name
        """,
    )
    if not rows:
        print("No scraper_log data.")
        print()
        return
    for row in rows:
        most_recent_error = row["most_recent_error"] or "None"
        print(
            f"- {row['source_name']}: {row['run_count']} runs, "
            f"{row['failure_count']} failures, most recent error: {most_recent_error}"
        )
    print()


def print_feedback(con: sqlite3.Connection) -> None:
    print("7. Feedback")
    up = scalar(con, "SELECT COUNT(*) FROM feedback_log WHERE rating = 'up'")
    down = scalar(con, "SELECT COUNT(*) FROM feedback_log WHERE rating = 'down'")
    total = up + down
    print(f"Thumbs up: {up}")
    print(f"Thumbs down: {down}")
    print(f"Thumbs down rate: {percent(down, total)}")

    rows = fetchall(
        con,
        """
        SELECT
            COALESCE(document_type, '(none)') AS document_type,
            COUNT(*) AS total,
            SUM(CASE WHEN rating = 'down' THEN 1 ELSE 0 END) AS down_count
        FROM feedback_log
        GROUP BY document_type
        ORDER BY document_type
        """,
    )
    if rows:
        print("Thumbs down rate by document type:")
        for row in rows:
            print(
                f"- {row['document_type']}: "
                f"{percent(row['down_count'], row['total'])} thumbs down"
            )
    print()


def main() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        print("CivicPulse Pilot Report")
        print("=======================")
        print()
        print_query_volume(con)
        print_top_document_types(con)
        print_failure_breakdown(con)
        print_letter_flow(con)
        print_soapbox_topics(con)
        print_scraper_health(con)
        print_feedback(con)


if __name__ == "__main__":
    main()
