import os
from pathlib import Path

from civicpulse.scraper.indexer import FTSIndexer

KNOWN_GOOD_QUERIES = [
    "town board meeting minutes",
    "zoning board application",
    "town clerk records",
    "parking permit",
    "public hearing notice",
    "sanitation schedule",
    "building permit",
    "planning board agenda",
]


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot compute a percentile without scores.")
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percent
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def collect_top_scores(vault_path: Path) -> list[float]:
    indexer = FTSIndexer(vault_path)
    indexer.index()
    scores = []
    for query in KNOWN_GOOD_QUERIES:
        results = indexer.query(query, top_n=1)
        if results:
            scores.append(results[0].score)
    return scores


def main() -> None:
    vault_path = Path(os.getenv("CIVICPULSE_VAULT_PATH", "./vault"))
    scores = collect_top_scores(vault_path)
    score_floor = percentile(scores, 0.25)
    print(f"Known-good queries with hits: {len(scores)}")
    print(f"25th-percentile top score: {score_floor:.6f}")
    print(f"Recommended CIVICPULSE_SCORE_FLOOR={score_floor:.6f}")


if __name__ == "__main__":
    main()
