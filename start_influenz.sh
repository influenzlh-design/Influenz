#!/bin/bash

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   🐜  INFLUENZ COLONY — STARTUP CHECK  🐜               ║"
echo "║   Scout → Forager → Worker → Queen                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Check .env exists ──────────────────────────────────────────────
echo "▶ Checking .env file..."
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "  ✅ Credentials loaded"
else
    echo "  ❌ .env file not found!"
    echo "     Copy .env.example to .env and fill in your API keys."
    exit 1
fi

# ── Step 2: Check required keys are set ───────────────────────────────────
echo "▶ Checking API keys..."

if [ -z "$GROQ_API_KEY" ]; then
    echo "  ❌ GROQ_API_KEY is missing from .env"
    echo "     Get a free key at: console.groq.com"
    exit 1
else
    echo "  ✅ GROQ_API_KEY found"
fi

if [ -z "$YOUTUBE_API_KEY" ]; then
    echo "  ❌ YOUTUBE_API_KEY is missing from .env"
    echo "     Get a free key at: console.cloud.google.com → YouTube Data API v3"
    exit 1
else
    echo "  ✅ YOUTUBE_API_KEY found"
fi

# ── Step 3: Check Python dependencies ─────────────────────────────────────
echo "▶ Checking Python dependencies..."

python -c "import groq, googleapiclient, dotenv, schedule" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  ❌ Missing dependencies. Run:"
    echo "     pip install groq google-api-python-client python-dotenv schedule"
    exit 1
else
    echo "  ✅ All dependencies present"
fi

# ── Step 4: Check colony files exist ──────────────────────────────────────
echo "▶ Checking colony agent files..."

MISSING=0
for f in colony_memory.py scout_agent.py forager_agent.py worker_agent.py queen_agent.py; do
    if [ ! -f "$f" ]; then
        echo "  ❌ Missing: $f"
        MISSING=1
    else
        echo "  ✅ Found: $f"
    fi
done

if [ $MISSING -ne 0 ]; then
    echo ""
    echo "  One or more agent files are missing. Check your project folder."
    exit 1
fi

# ── Step 5: Launch the colony ─────────────────────────────────────────────
echo ""
echo "  ✅ All systems nominal."
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   🚀  Launching Queen Influenz...                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

python queen_agent.py
