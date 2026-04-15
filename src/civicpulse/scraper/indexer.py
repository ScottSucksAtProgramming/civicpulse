import os
import sqlite3
from pathlib import Path

import frontmatter

from civicpulse.scraper.models import Result


class FTSIndexer:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path

    def index(self) -> None:
        db_path = self.vault_path / ".index.db"
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        cur.executescript(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                title, content, source_url, document_type, date, meeting_id,
                chunk_index UNINDEXED, file_path UNINDEXED,
                tokenize='porter ascii'
            );
            CREATE TABLE IF NOT EXISTS _index_state (
                file_path TEXT PRIMARY KEY, mtime REAL
            );
            """
        )

        state = {
            r["file_path"]: r["mtime"]
            for r in cur.execute("SELECT file_path, mtime FROM _index_state")
        }

        md_files = [p for p in self.vault_path.rglob("*.md")]
        current_paths = set()

        for md_file in md_files:
            path_str = str(md_file)
            current_paths.add(path_str)
            mtime = os.path.getmtime(md_file)
            if state.get(path_str) == mtime:
                continue

            post = frontmatter.load(md_file)
            cur.execute("DELETE FROM fts_chunks WHERE file_path = ?", (path_str,))
            cur.execute(
                "INSERT INTO fts_chunks VALUES (?,?,?,?,?,?,?,?)",
                (
                    post.metadata.get("title", ""),
                    post.content,
                    post.metadata.get("source_url", ""),
                    post.metadata.get("document_type", ""),
                    post.metadata.get("date", ""),
                    post.metadata.get("meeting_id", ""),
                    str(post.metadata.get("chunk_index", 0)),
                    path_str,
                ),
            )
            cur.execute(
                "INSERT OR REPLACE INTO _index_state VALUES (?, ?)",
                (path_str, mtime),
            )

        stale = set(state) - current_paths
        for path_str in stale:
            cur.execute("DELETE FROM fts_chunks WHERE file_path = ?", (path_str,))
            cur.execute("DELETE FROM _index_state WHERE file_path = ?", (path_str,))

        con.commit()
        con.close()

    def query(self, q: str, filters: dict | None = None, top_n: int = 10) -> list[Result]:
        db_path = self.vault_path / ".index.db"
        if not db_path.exists():
            return []

        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        table_exists = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'fts_chunks'"
        ).fetchone()
        if table_exists is None:
            con.close()
            return []

        sql = """
            SELECT title, content, source_url, document_type, date, meeting_id,
                   chunk_index, file_path, rank
            FROM fts_chunks
            WHERE fts_chunks MATCH ?
        """
        params: list = [q]

        if filters:
            if "document_type" in filters:
                sql += " AND document_type = ?"
                params.append(filters["document_type"])
            if "date" in filters:
                sql += " AND date BETWEEN ? AND ?"
                params.extend(filters["date"])

        sql += " ORDER BY rank LIMIT ?"
        params.append(top_n)

        rows = con.execute(sql, params).fetchall()
        con.close()

        return [
            Result(
                file_path=r["file_path"],
                source_url=r["source_url"],
                document_type=r["document_type"],
                date=r["date"] or None,
                meeting_id=r["meeting_id"] or None,
                title=r["title"],
                chunk_index=int(r["chunk_index"]),
                score=abs(r["rank"]),
                content_preview=r["content"][:200],
            )
            for r in rows
        ]
