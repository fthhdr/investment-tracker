#!/bin/bash
# ─────────────────────────────────────────────────────────────
# run.sh — Launch the Investment Tracker Dashboard
# Usage: ./run.sh   (or double-click in your terminal)
# ─────────────────────────────────────────────────────────────

# 1. Make sure we're in the right directory
cd "$(dirname "$0")"

# 2. Install/upgrade dependencies
echo "📦 Checking dependencies..."
pip install -r requirements.txt -q

# 3. Launch Streamlit
echo "🚀 Launching Investment Tracker Dashboard..."
echo "   Open http://localhost:8501 in your browser"
echo ""
streamlit run app.py --server.port 8501 --server.headless false
