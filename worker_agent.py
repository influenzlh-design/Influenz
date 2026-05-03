"""
influenz / worker_agent.py
--------------------------
Worker agent — takes approved scripts from ColonyMemory and prepares
them for production (recording or CapCut text-to-video).

Sprint 1: Outputs approved scripts to console + marks as produced.
Sprint 2: Will auto-generate LinkedIn carousel slides from the same script.

No Twitter. No Tweepy. Platform is YouTube Shorts + LinkedIn.

Usage:
    python worker_agent.py            # process next approved script
    python worker_agent.py --all      # process all approved scripts
    python worker_agent.py --peek     # show what's ready to produce
"""

import os
import time
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
from colony_memory import ColonyMemory

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s  [WORKER]  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("worker")


class WorkerAgent:
    """
    Picks up approved scripts and prepares them for production.
    QueenAgent calls: worker = WorkerAgent(); worker.work()
    """

    def __init__(self):
        self.memory = ColonyMemory()
        log.debug("WorkerAgent initialised.")

    def work(self, process_all: bool = False) -> dict:
        """
        Main entry point. Processes 1 approved script (or all if process_all=True).
        Returns summary dict for the Queen's log.
        """
        log.info(f"🐜 [WORKER | {datetime.now().strftime('%H:%M:%S')}] Checking approved scripts...")

        limit   = 100 if process_all else 1
        scripts = self.memory.get_approved_scripts(limit=limit)

        if not scripts:
            log.info("  No approved scripts. Run: python forager_agent.py --approve <id>")
            return {"produced": 0}

        produced = 0

        for s in scripts:
            log.info(f"  Processing script #{s['id']}: \"{s['short_title']}\"")

            self._print_production_sheet(s)
            self.memory.mark_script(s["id"], "produced")
            produced += 1
            log.info(f"  ✅ Script #{s['id']} marked as produced.")

            if len(scripts) > 1:
                time.sleep(1)

        log.info(f"🐜 Worker complete — {produced} scripts ready for recording.")
        return {"produced": produced}

    def _print_production_sheet(self, script: dict) -> None:
        """
        Prints a clean production sheet for recording or CapCut input.
        In Sprint 2 this will also generate a LinkedIn carousel PDF.
        """
        secs  = script.get("estimated_secs", 0)
        title = script.get("short_title", "")

        print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  INFLUENZ — PRODUCTION SHEET                                        ║
╠══════════════════════════════════════════════════════════════════════╣
║  Script #{script['id']} | Target duration: ~{secs}s
╠══════════════════════════════════════════════════════════════════════╣

  YOUTUBE TITLE (copy-paste):
  {title}

  ── HOOK (first 3 seconds) ───────────────────────────────────────────
  {script.get('hook', '')}

  ── BODY ─────────────────────────────────────────────────────────────
  {script.get('script_body', '')}

  ── CTA (final line) ─────────────────────────────────────────────────
  {script.get('cta', '')}

  ── YOUTUBE DESCRIPTION (copy-paste) ─────────────────────────────────
  {script.get('yt_description', '')}

  ── HASHTAGS ─────────────────────────────────────────────────────────
  {script.get('hashtags', '')}

╠══════════════════════════════════════════════════════════════════════╣
║  NEXT STEPS:                                                        ║
║  1. Record yourself reading this (phone, ring light, one take)      ║
║  OR open CapCut → text-to-video → paste the body above             ║
║  2. Upload as a YouTube Short (vertical, under 60 seconds)          ║
║  3. Copy title + description + hashtags into YouTube on upload      ║
║  4. Post the script as a LinkedIn carousel (Sprint 2 automates this)║
╚══════════════════════════════════════════════════════════════════════╝
        """)

    def peek(self) -> None:
        """Show what scripts are approved and ready to produce."""
        scripts = self.memory.get_approved_scripts(limit=10)
        if not scripts:
            print("No approved scripts waiting. Approve one with:")
            print("  python forager_agent.py --approve <id>")
            return
        print(f"\n{'ID':>4}  {'Secs':>5}  Title")
        print("-" * 60)
        for s in scripts:
            print(f"{s['id']:>4}  {s['estimated_secs']:>5}s  {s['short_title'][:48]}")
        print()


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Influenz Worker Agent")
    parser.add_argument("--all",  action="store_true",
                        help="Process all approved scripts.")
    parser.add_argument("--peek", action="store_true",
                        help="Show approved scripts waiting for production.")
    args = parser.parse_args()

    worker = WorkerAgent()

    if args.peek:
        worker.peek()
    else:
        worker.work(process_all=args.all)