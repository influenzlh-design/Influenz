# 🐜 Influenz — Autonomous AI Ant Colony

> *An AI-powered content system that finds trending topics, writes scripts, and produces YouTube Shorts — autonomously.*

[![Build in Public](https://img.shields.io/badge/Build%20in%20Public-%F0%9F%90%9C-green)](https://youtube.com/@influenzh)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-@influenzh-red)](https://youtube.com/@influenzh)

---

## What is Influenz?

Influenz is a self-organising system of specialised AI agents — modelled on ant colony behaviour — that autonomously manages content discovery, script generation, and production for a YouTube Shorts channel.

No agency. No team. No manual research. Just agents.

The colony runs on **£0/month** using free API tiers.

---

## The Colony

```
Queen Agent
    │
    ├── Scout Agent    → scans YouTube for trending topics (every 24h)
    │
    ├── Forager Agent  → generates 55-second Short scripts via Groq LLM (every 6h)
    │
    └── Worker Agent   → prepares approved scripts for production (every 6h)

ColonyMemory (SQLite) — shared brain all agents read and write through
```

---

## How It Works

**1. Scout** queries YouTube Data API v3 across 10 keyword clusters in the AI/automation niche. It scores every result by engagement ratio, saves only high-quality topics, and queues them for the Forager.

**2. Forager** reads the top-scored topic, calls the Groq LLM (`llama-3.1-8b-instant`), and generates a complete script — hook, body, CTA, YouTube description, and hashtags — optimised for 55 seconds.

**3. Human approval** — every script sits at `pending_review` until you approve it. Nothing posts automatically.

**4. Worker** reads approved scripts and outputs a production sheet — everything copy-paste ready to record or feed into CapCut for faceless video generation.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/influenzlh-design/Influenz.git
cd Influenz

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install groq google-api-python-client python-dotenv schedule

# 4. Set up environment variables
cp .env.example .env
# Fill in your API keys in .env

# 5. Run the Scout
python scout_agent.py --run-now
python scout_agent.py --peek

# 6. Run the Forager
python forager_agent.py --run-now
python forager_agent.py --peek

# 7. Approve a script
python forager_agent.py --approve 1

# 8. Get your production sheet
python worker_agent.py

# 9. Run the full colony on schedule
python queen_agent.py
```

---

## API Keys Required

| Key | Where to get it | Cost |
|-----|----------------|------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Free |
| `YOUTUBE_API_KEY` | [console.cloud.google.com](https://console.cloud.google.com) → YouTube Data API v3 | Free |

---

## Environment Variables

```bash
# .env
GROQ_API_KEY=your_groq_key_here
YOUTUBE_API_KEY=your_youtube_key_here
DB_PATH=colony.db
LOG_LEVEL=INFO
```

---

## Agent Commands

### Scout
```bash
python scout_agent.py --run-now    # single sweep
python scout_agent.py --peek       # view topic queue
```

### Forager
```bash
python forager_agent.py --run-now          # process top topic
python forager_agent.py --run-now --all    # process all queued topics
python forager_agent.py --peek             # view pending scripts
python forager_agent.py --approve 1        # approve script by ID
```

### Worker
```bash
python worker_agent.py          # process next approved script
python worker_agent.py --all    # process all approved scripts
python worker_agent.py --peek   # view approved scripts
```

### Queen (full colony)
```bash
python queen_agent.py           # run forever on schedule
python queen_agent.py --once    # single cycle and exit
python queen_agent.py --stats   # colony memory stats
```

---

## Content Strategy

**Primary platform:** YouTube Shorts  
**Secondary platform:** LinkedIn (personal profile, carousel posts)  
**Niche:** AI agents, automation, indie hacking, build in public  
**Posting target:** 3 Shorts per week  
**Production method:** Faceless — terminal screen recordings + CapCut text-to-video  

---

## Roadmap

- [x] Sprint 0 — Accounts, tools, API keys
- [x] Sprint 1 — Scout + Forager agents live
- [x] Sprint 1 — First AI-generated Short published
- [ ] Sprint 2 — Worker auto-generates LinkedIn carousels
- [ ] Sprint 3 — Automated scheduling via YouTube API
- [ ] Sprint 4 — Open source the framework, Gumroad guide

---

## Built in Public

This entire project is documented publicly as it's built. Watch the colony grow:

- 📺 YouTube: [@influenzh](https://youtube.com/@influenzh)
- 💼 LinkedIn: [Adeiza Awwal](https://linkedin.com/in/influenz-founder)

---

## Tech Stack

- **Python 3.10+**
- **Groq** — free LLM inference (`llama-3.1-8b-instant`)
- **YouTube Data API v3** — trending topic discovery
- **SQLite** — shared colony memory (no server needed)
- **CapCut** — faceless video production
- **schedule** — agent scheduling

---

## License

MIT — use it, fork it, build your own colony.

---

*"The colony doesn't sleep. It just schedules."* 🐜
