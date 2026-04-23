import os
import re
from pathlib import Path
from typing import Callable

import frontmatter

from civicpulse.scraper.indexer import FTSIndexer
from civicpulse.scraper.models import VaultChunk
from civicpulse.scraper.writer import VaultWriter

YOUTUBE_CHANNEL_ID = "UCIYf6QoRXGaBgbqO24thUlg"
WINDOW_SECONDS = 180
WINDOW_OVERLAP_SECONDS = 30
WINDOW_STEP_SECONDS = WINDOW_SECONDS - WINDOW_OVERLAP_SECONDS
TITLE_PATTERN = re.compile(r"(town board|public hearing)", re.IGNORECASE)


class YouTubeDataClient:
    def __init__(self, api_key: str) -> None:
        from googleapiclient.discovery import build

        self._service = build("youtube", "v3", developerKey=api_key)

    def list_channel_videos(self, channel_id: str) -> list[dict[str, str]]:
        videos: list[dict[str, str]] = []
        page_token: str | None = None

        while True:
            response = (
                self._service.search()
                .list(
                    part="id,snippet",
                    channelId=channel_id,
                    type="video",
                    maxResults=50,
                    order="date",
                    pageToken=page_token,
                )
                .execute()
            )
            for item in response.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                snippet = item.get("snippet", {})
                if not video_id:
                    continue
                videos.append(
                    {
                        "video_id": video_id,
                        "title": snippet.get("title", ""),
                        "published_at": snippet.get("publishedAt", ""),
                    }
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                return videos


class YouTubeScraper:
    def __init__(
        self,
        vault_path: Path,
        youtube_client: YouTubeDataClient | None = None,
        transcript_fetcher: Callable[[str], list[dict]] | None = None,
        no_transcript_log_path: Path | None = None,
        api_key: str | None = None,
        channel_id: str = YOUTUBE_CHANNEL_ID,
    ) -> None:
        resolved_api_key = api_key or os.getenv("CIVICPULSE_YOUTUBE_API_KEY")
        if youtube_client is None and not resolved_api_key:
            raise RuntimeError("CIVICPULSE_YOUTUBE_API_KEY is not configured.")

        self._vault_path = vault_path
        self._youtube_client = youtube_client or YouTubeDataClient(resolved_api_key or "")
        self._transcript_fetcher = transcript_fetcher or self._fetch_transcript
        self._no_transcript_log_path = (
            no_transcript_log_path or Path("data/youtube/no-transcript.txt")
        )
        self._channel_id = channel_id
        self._writer = VaultWriter(vault_path)
        self._indexer = FTSIndexer(vault_path)

    def scrape_all(self) -> int:
        self._vault_path.mkdir(parents=True, exist_ok=True)
        self._no_transcript_log_path.parent.mkdir(parents=True, exist_ok=True)
        processed_video_ids = self._existing_video_ids()
        written = 0

        for video in self._youtube_client.list_channel_videos(self._channel_id):
            if not TITLE_PATTERN.search(video["title"]):
                continue
            if video["video_id"] in processed_video_ids:
                continue

            try:
                transcript = self._transcript_fetcher(video["video_id"])
            except Exception:
                self._append_no_transcript(video["video_id"], video["title"])
                continue

            for chunk in self._chunk_video(video, transcript):
                self._writer.write(chunk)
                written += 1

        self._indexer.index()
        return written

    def _existing_video_ids(self) -> set[str]:
        video_ids: set[str] = set()
        base = self._vault_path / "meeting-video"
        if not base.exists():
            return video_ids

        for path in base.rglob("*.md"):
            post = frontmatter.load(path)
            video_id = post.metadata.get("video_id")
            if isinstance(video_id, str):
                video_ids.add(video_id)
        return video_ids

    def _chunk_video(self, video: dict[str, str], transcript: list[dict]) -> list[VaultChunk]:
        if not transcript:
            return []

        max_end = max(item["start"] + item.get("duration", 0) for item in transcript)
        chunks: list[VaultChunk] = []
        chunk_index = 0
        window_start = 0

        while window_start < max_end:
            window_end = window_start + WINDOW_SECONDS
            texts = [
                item["text"].strip()
                for item in transcript
                if item["start"] < window_end
                and item["start"] + item.get("duration", 0) > window_start
                and item["text"].strip()
            ]
            if texts:
                content = self._truncate_words(" ".join(texts), limit=200)
                timestamp_start = int(window_start)
                chunks.append(
                    VaultChunk(
                        content=content,
                        source_url=f"https://youtu.be/{video['video_id']}?t={timestamp_start}",
                        document_type="meeting-video",
                        date=video["published_at"][:10] or None,
                        meeting_id=None,
                        title=f"{video['title']} @ {timestamp_start}s",
                        chunk_index=chunk_index,
                        slug=f"{video['video_id']}-{timestamp_start}",
                        extra_metadata={
                            "video_id": video["video_id"],
                            "video_title": video["title"],
                            "published_at": video["published_at"],
                            "timestamp_start": timestamp_start,
                        },
                    )
                )
                chunk_index += 1
            window_start += WINDOW_STEP_SECONDS
        return chunks

    def _append_no_transcript(self, video_id: str, title: str) -> None:
        with self._no_transcript_log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{video_id}\t{title}\n")

    @staticmethod
    def _truncate_words(text: str, limit: int) -> str:
        words = text.split()
        if len(words) <= limit:
            return text
        return " ".join(words[:limit])

    @staticmethod
    def _fetch_transcript(video_id: str) -> list[dict]:
        from youtube_transcript_api import YouTubeTranscriptApi

        return YouTubeTranscriptApi().fetch(video_id).to_raw_data()
