"""
influenz / queen_agent.py
-------------------------
Queen agent — orchestrates the entire colony on a schedule.
Calls Scout → Forager → Worker in sequence.

Colony chain:
    ScoutAgent   (every 24h) — finds trending YouTube topics
    ForagerAgent (every  6h) — generates Shorts scripts from topics
    WorkerAgent  (every  6h) — prepares approved scripts for production

Usage:
    python queen_agent.py          # start the colony (runs forever)
    python queen_agent.py --once   # run one full cycle and exit
    python queen_agent.py --stats  # show colony memory stats
"""

import subprocess
import time
import argparse
import logging
import schedule
from datetime import datetime

LOG_LEVEL = "INFO"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s  [QUEEN]  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("queen")


class QueenAgent:

    def __init__(self):
        self.cycle       = 0
        self.colony_name = "INFLUENZ"

    def announce(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.info(f"👑 [{self.colony_name} | {timestamp} | Cycle {self.cycle}] {message}")

    # ── Agent runners ──────────────────────────────────────────────────────

    def run_scout_cycle(self) -> None:
        self.announce("DEPLOY: Scout agent — scanning YouTube for trending topics.")
        result = subprocess.run(
            ["python", "scout_agent.py", "--run-now"],
            capture_output=False,
        )
        if result.returncode != 0:
            log.warning("Scout cycle exited with errors — check logs above.")

    def run_forager_cycle(self) -> None:
        self.announce("DEPLOY: Forager agent — generating scripts from queued topics.")
        result = subprocess.run(
            ["python", "forager_agent.py", "--run-now"],
            capture_output=False,
        )
        if result.returncode != 0:
            log.warning("Forager cycle exited with errors — check logs above.")

    def run_worker_cycle(self) -> None:
        self.announce("DEPLOY: Worker agent — preparing approved scripts for production.")
        result = subprocess.run(
            ["python", "worker_agent.py"],
            capture_output=False,
        )
        if result.returncode != 0:
            log.warning("Worker cycle exited with errors — check logs above.")

    # ── Stats ──────────────────────────────────────────────────────────────

    def print_stats(self) -> None:
        try:
            from colony_memory import ColonyMemory
            mem   = ColonyMemory()
            stats = mem.get_stats()
            print("\n── Colony Memory Stats ──────────────────")
            for table, counts in stats.items():
                print(f"  {table}:")
                for status, n in counts.items():
                    print(f"    {status:<20} {n}")
            print()
        except Exception as e:
            log.error(f"Could not read stats: {e}")

    # ── Full colony startup ────────────────────────────────────────────────

    def start_colony(self) -> None:
        print("""
        ╔══════════════════════════════════════════════╗
        ║   🐜  INFLUENZ COLONY ACTIVATED  🐜          ║
        ║   Scout → Forager → Worker                  ║
        ║   "Build in public. Automate everything."   ║
        ╚══════════════════════════════════════════════╝
        """)

        self.announce("Queen assuming control. Colony starting.")

        # ── Schedule ───────────────────────────────────────────────────────
        # Scout: once per day (YouTube quota is 10k units/day)
        # Forager: every 6 hours (generates new scripts from queued topics)
        # Worker: every 6 hours (outputs production sheets for approved scripts)
        schedule.every(24).hours.do(self.run_scout_cycle)
        schedule.every(6).hours.do(self.run_forager_cycle)
        schedule.every(6).hours.do(self.run_worker_cycle)

        # ── Initial full cycle on startup ──────────────────────────────────
        self.run_scout_cycle()
        self.run_forager_cycle()
        self.run_worker_cycle()

        self.announce("Initial cycle complete. Colony running on schedule.")
        self.announce("Scout runs every 24h | Forager + Worker run every 6h.")
        self.announce("Press Ctrl+C to hibernate the colony.")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
                self.cycle += 1
        except KeyboardInterrupt:
            self.announce("Colony hibernating. Goodbye.")

    def run_once(self) -> None:
        """Run one full Scout → Forager → Worker cycle and exit."""
        self.announce("Single cycle mode — running once then exiting.")
        self.run_scout_cycle()
        self.run_forager_cycle()
        self.run_worker_cycle()
        self.announce("Single cycle complete.")


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Influenz Queen Agent — Colony Orchestrator")
    parser.add_argument("--once",  action="store_true",
                        help="Run one full cycle (Scout+Forager+Worker) and exit.")
    parser.add_argument("--stats", action="store_true",
                        help="Show colony memory stats and exit.")
    args = parser.parse_args()

    queen = QueenAgent()

    if args.stats:
        queen.print_stats()
    elif args.once:
        queen.run_once()
    else:
        queen.start_colony()
