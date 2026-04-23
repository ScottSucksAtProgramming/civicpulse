import datetime
import sqlite3
from pathlib import Path

from civicpulse.backend.privacy import redact
from civicpulse.backend.types import SoapboxSubmitRequest


class QueryLogger:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def ensure_table(self) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS query_log (
                    id INTEGER PRIMARY KEY,
                    document_type TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )
            con.commit()

    def log_query(self, document_type: str | None) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                INSERT INTO query_log (document_type, timestamp)
                VALUES (?, ?)
                """,
                (document_type, datetime.datetime.now(datetime.UTC).isoformat()),
            )
            con.commit()


class UnansweredLogger:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def ensure_table(self) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS unanswered_log (
                    id INTEGER PRIMARY KEY,
                    redacted_query TEXT,
                    failure_type TEXT,
                    document_type TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )
            con.commit()

    def log_refusal(
        self,
        redacted_query: str,
        failure_type: str,
        document_type: str | None,
    ) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                INSERT INTO unanswered_log (
                    redacted_query, failure_type, document_type, timestamp
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    redact(redacted_query),
                    failure_type,
                    document_type,
                    datetime.datetime.now(datetime.UTC).isoformat(),
                ),
            )
            con.commit()


class SoapboxLogger:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def ensure_table(self) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS soapbox_log (
                    id INTEGER PRIMARY KEY,
                    summary TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            con.commit()

    def log_submission(self, request: SoapboxSubmitRequest) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                INSERT INTO soapbox_log (summary, topic, timestamp)
                VALUES (?, ?, ?)
                """,
                (
                    redact(request.summary),
                    request.topic,
                    datetime.datetime.now(datetime.UTC).isoformat(),
                ),
            )
            con.commit()


class FeedbackLogger:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def ensure_table(self) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_log (
                    id INTEGER PRIMARY KEY,
                    rating TEXT,
                    redacted_comment TEXT,
                    document_type TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )
            con.commit()

    def log_feedback(
        self,
        rating: str,
        comment: str | None,
        document_type: str | None,
    ) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                INSERT INTO feedback_log (
                    rating, redacted_comment, document_type, timestamp
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    rating,
                    redact(comment) if comment is not None else None,
                    document_type,
                    datetime.datetime.now(datetime.UTC).isoformat(),
                ),
            )
            con.commit()


class ScraperLogger:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def ensure_table(self) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS scraper_log (
                    id INTEGER PRIMARY KEY,
                    source_name TEXT,
                    url TEXT,
                    error_type TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )
            con.commit()

    def log_run(
        self,
        source_name: str,
        url: str | None,
        error_type: str | None,
    ) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                """
                INSERT INTO scraper_log (source_name, url, error_type, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    source_name,
                    url,
                    error_type,
                    datetime.datetime.now(datetime.UTC).isoformat(),
                ),
            )
            con.commit()
