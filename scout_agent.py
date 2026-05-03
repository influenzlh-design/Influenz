"""
influenz / scout_agent.py
-------------------------
Scout agent — finds trending YouTube topics in the AI/automation niche,
scores them by engagement signal, and queues the best ones in ColonyMemory
for the Forager agent to turn into Short scripts.

Replaces the original Twitter/Tweepy version. Same class pattern,
same interface so QueenAgent can call it identically.

Dependencies:
    pip install google-api-python-client python-dotenv

Usage (standalone):
    python scout_agent.py --run-now
    python scout_agent.py --peek
"""

import os
import math
import time
import argparse
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from googleapiclient.discovery import build
from colony_memory import ColonyMemory

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s  [SCOUT]  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scout")

# ── Topic clusters ─────────────────────────────────────────────────────────
# These are the niches Influenz owns. Rotate and add as you learn
# what content resonates. Each string = one YouTube search query.

KEYWORD_CLUSTERS = [
    "AI agents automation 2026",
    "build AI startup from scratch",
    "autonomous AI social media",
    "indie hacker AI tools",
    "LLM workflow automation",
    "no code AI agent tutorial",
    "AI content creation automation",
    "YouTube Shorts AI generated",
    "solopreneur AI business",
    "AI side project build in public",
]

# Minimum like/view ratio to queue a topic.
# Below this = low engagement niche, not worth covering.
MIN_ENGAGEMENT_RATIO = 0.02


# ── YouTube helpers ────────────────────────────────────────────────────────

def build_youtube():
    if not YOUTUBE_API_KEY:
        raise EnvironmentError(
            "YOUTUBE_API_KEY not set. "
            "Get a free key at console.cloud.google.com → "
            "Enable 'YouTube Data API v3' → Credentials → API Key."
        )
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)


def search_videos(yt, query: str, max_results: int = 5) -> list:
    response = yt.search().list(
        part="snippet",
        q=query,
        type="video",
        videoDuration="short",
        order="relevance",
        publishedAfter="2025-01-01T00:00:00Z",
        maxResults=max_results,
        relevanceLanguage="en",
    ).execute()
    return response.get("items", [])


def get_video_stats(yt, video_ids: list) -> dict:
    response = yt.videos().list(
        part="statistics",
        id=",".join(video_ids),
    ).execute()
    return {
        item["id"]: item.get("statistics", {})
        for item in response.get("items", [])
    }


# ── Scoring ────────────────────────────────────────────────────────────────

def score_topic(view_count: int, like_count: int, comment_count: int) -> float:
    """
    Composite score (0.0–1.0) combining:
      engagement ratio (50%) + comment ratio (30%) + reach log-scale (20%)
    Higher = more worth covering.
    """
    if view_count == 0:
        return 0.0
    engagement    = like_count / view_count
    comment_ratio = comment_count / view_count
    reach         = min(math.log10(max(view_count, 1)) / 7, 1.0)
    return round((engagement * 0.5) + (comment_ratio * 0.3) + (reach * 0.2), 4)


# ── ScoutAgent ─────────────────────────────────────────────────────────────

class ScoutAgent:
    """
    Scans YouTube for trending topics and queues them in ColonyMemory.
    QueenAgent calls: scout = ScoutAgent(); scout.scout()
    """

    def __init__(self):
        self.memory   = ColonyMemory()
        self.keywords = KEYWORD_CLUSTERS
        log.debug("ScoutAgent initialised.")

    def scout(self) -> dict:
        """
        Main entry point. Searches all keyword clusters,
        scores results, saves new topics to memory.
        Returns a summary dict for the Queen's log.
        """
        log.info(f"🐜 [SCOUT | {datetime.now().strftime('%H:%M:%S')}] Scanning for topics...")

        try:
            yt = build_youtube()
        except EnvironmentError as e:
            log.error(str(e))
            return {"topics_found": 0, "topics_saved": 0, "error": str(e)}

        total_found = 0
        total_saved = 0

        for query in self.keywords:
            log.info(f"  Searching: '{query}'")

            try:
                items = search_videos(yt, query, max_results=5)
            except Exception as e:
                log.warning(f"  Search failed for '{query}': {e}")
                continue

            if not items:
                continue

            video_ids = [item["id"]["videoId"] for item in items]

            try:
                stats_map = get_video_stats(yt, video_ids)
            except Exception as e:
                log.warning(f"  Stats fetch failed: {e}")
                stats_map = {}

            total_found += len(items)

            for item in items:
                vid_id  = item["id"]["videoId"]
                snippet = item["snippet"]
                stats   = stats_map.get(vid_id, {})

                views    = int(stats.get("viewCount",    0))
                likes    = int(stats.get("likeCount",    0))
                comments = int(stats.get("commentCount", 0))
                ratio    = round(likes / views, 4) if views else 0
                score    = score_topic(views, likes, comments)

                if views > 0 and ratio < MIN_ENGAGEMENT_RATIO:
                    log.debug(f"  Skipping low-engagement: {vid_id} (ratio={ratio:.3f})")
                    continue

                saved = self.memory.save_topic(
                    query            = query,
                    video_id         = vid_id,
                    title            = snippet.get("title", ""),
                    channel          = snippet.get("channelTitle", ""),
                    view_count       = views,
                    like_count       = likes,
                    comment_count    = comments,
                    engagement_ratio = ratio,
                    score            = score,
                )
                if saved:
                    total_saved += 1
                    log.info(f"  ✅ Queued: \"{snippet.get('title', '')[:55]}\" (score={score})")

            time.sleep(1)   # polite gap between queries

        result = {
            "topics_found": total_found,
            "topics_saved": total_saved,
        }
        log.info(f"🐜 Scout complete — found {total_found}, queued {total_saved} new topics.")
        return result

    def peek(self, limit: int = 10) -> None:
        """Print current topic queue — handy for manual inspection."""
        rows = self.memory.peek_topics(limit=limit)
        if not rows:
            print("Queue is empty. Run scout() first.")
            return
        print(f"\n{'ID':>4}  {'Score':>6}  {'Eng%':>5}  {'Views':>8}  Title")
        print("-" * 75)
        for r in rows:
            print(
                f"{r['id']:>4}  {r['score']:>6.4f}  "
                f"{r['engagement_ratio']*100:>4.1f}%  "
                f"{r['view_count']:>8,}  "
                f"{r['title'][:45]}"
            )
        print()


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Influenz Scout Agent")
    parser.add_argument("--run-now", action="store_true",
                        help="Run a single scout sweep and exit.")
    parser.add_argument("--peek",    action="store_true",
                        help="Show current topic queue and exit.")
    args = parser.parse_args()

    scout = ScoutAgent()

    if args.peek:
        scout.peek()
    elif args.run_now:
        scout.scout()
    else:
        # Default: single sweep (Queen handles the scheduling)
        scout.scout()
