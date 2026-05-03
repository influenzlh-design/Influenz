"""
influenz / forager_agent.py
---------------------------
Forager agent — reads queued topics from ColonyMemory, calls Groq LLM
to generate a YouTube Shorts script (55 seconds), title, description,
and hashtags, then saves everything back to memory for human review.

New agent — sits between ScoutAgent and WorkerAgent in the colony chain:
    Scout → Forager → (human approves) → Worker

Dependencies:
    pip install groq python-dotenv

Usage (standalone):
    python forager_agent.py --run-now
    python forager_agent.py --run-now --all
    python forager_agent.py --peek
    python forager_agent.py --approve 1
"""

import os
import json
import time
import argparse
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from groq import Groq
from colony_memory import ColonyMemory

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LOG_LEVEL    = os.getenv("LOG_LEVEL", "INFO")
MODEL        = "llama-3.1-8b-instant"   # free, fast — swap to mixtral-8x7b for richer output

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s  [FORAGER]  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("forager")

# ── Prompts ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Influenz — the Forager agent of an autonomous AI ant colony 
building a YouTube Shorts channel in the AI/automation niche.

Your job: produce SHORT, PUNCHY YouTube Shorts scripts that are genuinely useful and 
feel human. No fluff. No hollow hype. The colony's credibility depends on every script 
being worth 55 seconds of someone's time.

Output ONLY valid JSON — no markdown, no preamble, no explanation outside the JSON.
The JSON must have exactly these keys:
{
  "short_title": "Compelling YouTube title, max 60 chars, no clickbait",
  "hook": "Opening line — first 3 seconds. Must create immediate curiosity or tension.",
  "script_body": "Main content — approx 120 words spoken naturally at ~130wpm = 55 seconds total including hook and CTA. Cover 1 tight insight or how-to. Conversational, direct.",
  "cta": "Closing call to action — one sentence, max 15 words. Subscribe or comment prompt.",
  "yt_description": "YouTube description — 2-3 sentences expanding on the topic. No spam.",
  "hashtags": "#AIAgents #Automation #BuildInPublic #YouTubeShorts #Influenz"
}"""


# ── LLM call ──────────────────────────────────────────────────────────────

def generate_script(topic_title: str, query: str) -> dict:
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY not set. "
            "Get a free key at console.groq.com → API Keys → Create API Key."
        )

    client = Groq(api_key=GROQ_API_KEY)

    user_prompt = (
        f"Write a YouTube Shorts script about this topic:\n"
        f"Topic title: {topic_title}\n"
        f"Search context: {query}\n\n"
        f"The script is for the Influenz channel — an AI ant colony building "
        f"social presence autonomously. Weave in that angle naturally if it fits, "
        f"but prioritise delivering real value on the topic first."
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.75,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)

    required = {"short_title", "hook", "script_body", "cta", "yt_description", "hashtags"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"LLM response missing keys: {missing}")

    return data


# ── Quality check ──────────────────────────────────────────────────────────

def estimate_duration(text: str, wpm: int = 130) -> tuple:
    words = len(text.split())
    secs  = round((words / wpm) * 60)
    return words, secs


def quality_check(script: dict) -> list:
    warnings = []
    full_text = f"{script['hook']} {script['script_body']} {script['cta']}"
    words, secs = estimate_duration(full_text)

    if secs < 35:
        warnings.append(f"Script short: ~{secs}s (target 45–65s)")
    if secs > 70:
        warnings.append(f"Script long: ~{secs}s (target 45–65s)")
    if len(script["short_title"]) > 60:
        warnings.append(f"Title long: {len(script['short_title'])} chars (max 60)")

    return warnings


# ── ForagerAgent ───────────────────────────────────────────────────────────

class ForagerAgent:
    """
    Reads top-scored queued topics from ColonyMemory and generates
    YouTube Shorts scripts via Groq. Saves results for human review.
    QueenAgent calls: forager = ForagerAgent(); forager.forage()
    """

    def __init__(self):
        self.memory = ColonyMemory()
        log.debug("ForagerAgent initialised.")

    def forage(self, process_all: bool = False) -> dict:
        """
        Main entry point. Processes 1 topic (or all if process_all=True).
        Returns summary dict for the Queen's log.
        """
        log.info(f"🐜 [FORAGER | {datetime.now().strftime('%H:%M:%S')}] Checking topic queue...")

        limit = 100 if process_all else 1
        topics = self.memory.get_queued_topics(limit=limit)

        if not topics:
            log.info("  No queued topics. Run ScoutAgent first.")
            return {"processed": 0, "failed": 0}

        processed, failed = 0, 0

        for topic in topics:
            topic_id    = topic["id"]
            topic_title = topic["title"]
            query       = topic["query"]

            log.info(f"  Processing topic #{topic_id}: \"{topic_title[:55]}\"")

            try:
                script   = generate_script(topic_title, query)
                warnings = quality_check(script)
                for w in warnings:
                    log.warning(f"  Quality: {w}")

                full_text    = f"{script['hook']} {script['script_body']} {script['cta']}"
                words, secs  = estimate_duration(full_text)

                script_id = self.memory.save_script(
                    topic_id       = topic_id,
                    short_title    = script["short_title"],
                    hook           = script["hook"],
                    script_body    = script["script_body"],
                    cta            = script["cta"],
                    yt_description = script["yt_description"],
                    hashtags       = script["hashtags"],
                    word_count     = words,
                    estimated_secs = secs,
                )

                self.memory.mark_topic(topic_id, "processed")
                processed += 1
                log.info(f"  ✅ Script #{script_id} saved — ~{secs}s, {words} words.")

            except Exception as e:
                log.error(f"  ❌ Failed for topic #{topic_id}: {e}")
                self.memory.mark_topic(topic_id, "error")
                failed += 1

            if len(topics) > 1:
                time.sleep(2)   # rate-limit courtesy between Groq calls

        result = {"processed": processed, "failed": failed}
        log.info(f"🐜 Forager complete — {processed} scripts generated, {failed} failed.")
        return result

    def peek(self, limit: int = 3) -> None:
        """Print pending scripts for human review."""
        scripts = self.memory.get_pending_scripts(limit=limit)
        if not scripts:
            print("No scripts pending review. Run forage() first.")
            return

        for s in scripts:
            print(f"\n{'='*68}")
            print(f"Script #{s['id']} | ~{s['estimated_secs']}s")
            print(f"TITLE : {s['short_title']}")
            print(f"\nHOOK  :\n{s['hook']}")
            print(f"\nBODY  :\n{s['script_body']}")
            print(f"\nCTA   :\n{s['cta']}")
            print(f"\nDESC  :\n{s['yt_description']}")
            print(f"\nTAGS  :\n{s['hashtags']}")
        print(f"\n{'='*68}")
        print("To approve: python forager_agent.py --approve <id>")
        print()

    def approve(self, script_id: int) -> None:
        self.memory.approve_script(script_id)
        log.info(f"Script #{script_id} approved — ready for Worker/recording.")


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Influenz Forager Agent")
    parser.add_argument("--run-now",  action="store_true",
                        help="Process the top queued topic and exit.")
    parser.add_argument("--all",      action="store_true",
                        help="With --run-now: process ALL queued topics.")
    parser.add_argument("--peek",     action="store_true",
                        help="Preview pending scripts and exit.")
    parser.add_argument("--approve",  type=int, metavar="ID",
                        help="Approve script by ID.")
    args = parser.parse_args()

    forager = ForagerAgent()

    if args.peek:
        forager.peek()
    elif args.approve:
        forager.approve(args.approve)
    elif args.run_now:
        forager.forage(process_all=args.all)
    else:
        forager.forage()
