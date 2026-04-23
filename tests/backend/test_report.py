import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_report(vault_path: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CIVICPULSE_VAULT_PATH": str(vault_path)}
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "report.py")],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_report_prints_all_sections_and_metrics(tmp_path):
    db_path = tmp_path / ".index.db"
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            CREATE TABLE query_log (
                id INTEGER PRIMARY KEY,
                document_type TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        con.executemany(
            "INSERT INTO query_log (document_type, timestamp) VALUES (?, ?)",
            [
                ("agenda", "2026-04-21T12:00:00+00:00"),
                ("agenda", "2026-04-21T13:00:00+00:00"),
                ("budget", "2026-04-22T09:00:00+00:00"),
            ],
        )
        con.execute(
            """
            CREATE TABLE unanswered_log (
                id INTEGER PRIMARY KEY,
                redacted_query TEXT,
                failure_type TEXT,
                document_type TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        con.executemany(
            """
            INSERT INTO unanswered_log (
                redacted_query, failure_type, document_type, timestamp
            ) VALUES (?, ?, ?, ?)
            """,
            [
                ("q1", "no_citation", "agenda", "2026-04-22T10:00:00+00:00"),
                ("q2", "no_results", None, "2026-04-22T11:00:00+00:00"),
            ],
        )
        con.execute(
            """
            CREATE TABLE draft_log (
                recipient TEXT NOT NULL,
                topic TEXT NOT NULL,
                abstracted_concern TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL DEFAULT 'suggestion'
            )
            """
        )
        con.executemany(
            """
            INSERT INTO draft_log (
                recipient, topic, abstracted_concern, timestamp, event_type
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    "Town Board",
                    "roads",
                    "A road concern.",
                    "2026-04-22T12:00:00+00:00",
                    "suggestion",
                ),
                (
                    "Town Board",
                    "roads",
                    "A road concern.",
                    "2026-04-22T12:01:00+00:00",
                    "generation",
                ),
            ],
        )
        con.execute(
            """
            CREATE TABLE soapbox_log (
                id INTEGER PRIMARY KEY,
                summary TEXT NOT NULL,
                topic TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        con.executemany(
            "INSERT INTO soapbox_log (summary, topic, timestamp) VALUES (?, ?, ?)",
            [
                ("More lighting", "public safety", "2026-04-22T13:00:00+00:00"),
                ("Safer crossings", "public safety", "2026-04-22T14:00:00+00:00"),
            ],
        )
        con.execute(
            """
            CREATE TABLE scraper_log (
                id INTEGER PRIMARY KEY,
                source_name TEXT,
                url TEXT,
                error_type TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        con.executemany(
            "INSERT INTO scraper_log (source_name, url, error_type, timestamp) VALUES (?, ?, ?, ?)",
            [
                ("AgendaCenterScraper", None, None, "2026-04-22T13:00:00+00:00"),
                ("AgendaCenterScraper", None, "RuntimeError", "2026-04-22T14:00:00+00:00"),
            ],
        )
        con.execute(
            """
            CREATE TABLE feedback_log (
                id INTEGER PRIMARY KEY,
                rating TEXT,
                redacted_comment TEXT,
                document_type TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )
        con.executemany(
            """
            INSERT INTO feedback_log (
                rating, redacted_comment, document_type, timestamp
            ) VALUES (?, ?, ?, ?)
            """,
            [
                ("up", None, "agenda", "2026-04-22T15:00:00+00:00"),
                ("down", "Confusing", "agenda", "2026-04-22T16:00:00+00:00"),
                ("down", None, "budget", "2026-04-22T17:00:00+00:00"),
            ],
        )
        con.commit()

    result = run_report(tmp_path)

    assert result.returncode == 0
    assert "1. Query Volume" in result.stdout
    assert "Total queries: 3" in result.stdout
    assert "agenda: 2" in result.stdout
    assert "3. Failure Breakdown" in result.stdout
    assert "no_citation (citation-proxy (not semantic grounding check)): 1" in result.stdout
    assert "Completion rate: 100.0%" in result.stdout
    assert "public safety: 2" in result.stdout
    assert (
        "AgendaCenterScraper: 2 runs, 1 failures, most recent error: RuntimeError"
        in result.stdout
    )
    assert "Thumbs down rate: 66.7%" in result.stdout
    assert "agenda: 50.0% thumbs down" in result.stdout


def test_report_exits_cleanly_when_tables_are_missing(tmp_path):
    result = run_report(tmp_path)

    assert result.returncode == 0
    assert "1. Query Volume" in result.stdout
    assert "No query_log data." in result.stdout
    assert "7. Feedback" in result.stdout
