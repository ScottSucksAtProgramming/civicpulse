import frontmatter
import pytest

from civicpulse.scraper.sources.youtube import YouTubeScraper


class StubYouTubeClient:
    def __init__(self, videos):
        self.videos = videos

    def list_channel_videos(self, channel_id: str):
        return list(self.videos)


def test_youtube_scraper_chunks_transcripts_with_overlap(tmp_path):
    videos = [
        {
            "video_id": "abc123",
            "title": "Town Board Meeting - Waterfront Rezoning",
            "published_at": "2026-04-01T19:00:00Z",
        }
    ]
    transcript = [
        {"text": "Opening remarks", "start": 0, "duration": 60},
        {"text": "Waterfront rezoning discussion begins", "start": 160, "duration": 60},
        {"text": "Public hearing comments continue", "start": 320, "duration": 60},
    ]

    scraper = YouTubeScraper(
        vault_path=tmp_path / "vault",
        youtube_client=StubYouTubeClient(videos),
        transcript_fetcher=lambda video_id: transcript,
        no_transcript_log_path=tmp_path / "data" / "youtube" / "no-transcript.txt",
        api_key="test-key",
    )

    written = scraper.scrape_all()

    assert written == 3
    chunk_files = sorted((tmp_path / "vault" / "meeting-video").rglob("*.md"))
    assert len(chunk_files) == 3

    first = frontmatter.load(chunk_files[0])
    second = frontmatter.load(chunk_files[1])
    third = frontmatter.load(chunk_files[2])

    assert first["document_type"] == "meeting-video"
    assert first["video_id"] == "abc123"
    assert first["video_title"] == "Town Board Meeting - Waterfront Rezoning"
    assert first["published_at"] == "2026-04-01T19:00:00Z"
    assert first["timestamp_start"] == 0
    assert first["source_url"] == "https://youtu.be/abc123?t=0"
    assert second["timestamp_start"] == 150
    assert second["source_url"] == "https://youtu.be/abc123?t=150"
    assert third["timestamp_start"] == 300
    assert len(third.content.split()) <= 200


def test_youtube_scraper_logs_videos_without_transcripts(tmp_path):
    videos = [
        {
            "video_id": "missing123",
            "title": "Public Hearing - Waterfront Rezoning",
            "published_at": "2026-04-01T19:00:00Z",
        }
    ]

    scraper = YouTubeScraper(
        vault_path=tmp_path / "vault",
        youtube_client=StubYouTubeClient(videos),
        transcript_fetcher=lambda video_id: (_ for _ in ()).throw(RuntimeError("no transcript")),
        no_transcript_log_path=tmp_path / "data" / "youtube" / "no-transcript.txt",
        api_key="test-key",
    )

    written = scraper.scrape_all()

    assert written == 0
    assert list((tmp_path / "vault").rglob("*.md")) == []
    assert (tmp_path / "data" / "youtube" / "no-transcript.txt").read_text().strip() == (
        "missing123\tPublic Hearing - Waterfront Rezoning"
    )


def test_youtube_scraper_skips_video_ids_already_in_vault(tmp_path):
    existing_file = tmp_path / "vault" / "meeting-video" / "2026" / "existing.md"
    existing_file.parent.mkdir(parents=True, exist_ok=True)
    existing_file.write_text(
        "---\n"
        "source_url: https://youtu.be/abc123?t=0\n"
        "document_type: meeting-video\n"
        "date: 2026-04-01\n"
        "title: Existing chunk\n"
        "chunk_index: 0\n"
        "video_id: abc123\n"
        "video_title: Existing\n"
        "published_at: 2026-04-01T19:00:00Z\n"
        "timestamp_start: 0\n"
        "---\n"
        "Existing content\n",
        encoding="utf-8",
    )

    scraper = YouTubeScraper(
        vault_path=tmp_path / "vault",
        youtube_client=StubYouTubeClient(
            [
                {
                    "video_id": "abc123",
                    "title": "Town Board Meeting - Already Indexed",
                    "published_at": "2026-04-01T19:00:00Z",
                }
            ]
        ),
        transcript_fetcher=lambda video_id: [{"text": "ignored", "start": 0, "duration": 10}],
        no_transcript_log_path=tmp_path / "data" / "youtube" / "no-transcript.txt",
        api_key="test-key",
    )

    written = scraper.scrape_all()

    assert written == 0
    assert len(list((tmp_path / "vault" / "meeting-video").rglob("*.md"))) == 1


def test_youtube_scraper_requires_api_key_when_client_not_injected(tmp_path, monkeypatch):
    monkeypatch.delenv("CIVICPULSE_YOUTUBE_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="CIVICPULSE_YOUTUBE_API_KEY"):
        YouTubeScraper(vault_path=tmp_path / "vault", api_key=None)
