#!/usr/bin/env bash
# =============================================================================
# fundwatch — Startup Funding Monitor & Human-in-the-Loop Job Outreach Bot
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Ensure Virtual Environment
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment not found at $VENV_DIR. Creating now..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -e ".[dev]"
fi

# Activate virtualenv
source "$VENV_DIR/bin/activate"

# 2. Ensure .env exists if example is present
if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/.env.example" ]; then
    echo "ℹ️  Creating .env from .env.example..."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
fi

# Ensure data directory exists
mkdir -p "$SCRIPT_DIR/data"

# 3. Command Dispatcher
COMMAND="${1:-ui}"
shift || true

case "$COMMAND" in
    ui|web|dashboard)
        PORT="${PORT:-8000}"
        HOST="${HOST:-0.0.0.0}"
        if [ ! -d "$SCRIPT_DIR/src/fundwatch/web/static/assets" ] && [ -d "$SCRIPT_DIR/frontend" ]; then
            echo "📦 Building modern React+Vite frontend..."
            (cd "$SCRIPT_DIR/frontend" && npm run build)
        fi
        echo "=========================================================="
        echo " 🚀 Starting FundWatch Animated React Web Dashboard"
        echo " 🌐 URL: http://localhost:${PORT}"
        echo " 📁 Resume: /home/viper/Downloads/Resumes/2+/Suriyan.pdf"
        echo " ✉️  Human Review Outbox enabled"
        echo "=========================================================="
        exec fundwatch ui --host "$HOST" --port "$PORT" "$@"
        ;;

    build-ui|build-frontend)
        echo "📦 Building React+Vite UI bundle..."
        (cd "$SCRIPT_DIR/frontend" && npm run build)
        ;;

    poll|once)
        echo "🔄 Running on-demand feed polling cycle..."
        exec fundwatch once "$@"
        ;;

    monitor|loop|run)
        echo "⏱️  Running continuous background monitoring loop..."
        exec fundwatch run "$@"
        ;;

    outbox)
        exec fundwatch outbox list "$@"
        ;;

    test)
        echo "🧪 Running full test suite..."
        exec pytest tests/ "$@"
        ;;

    help|-h|--help)
        echo "Usage: ./run.sh [command] [options]"
        echo ""
        echo "Commands:"
        echo "  ui          Start the clean monochrome web dashboard (default) on http://localhost:8000"
        echo "  poll        Run a single feed polling and funding extraction cycle"
        echo "  monitor     Run continuous scheduled monitoring loop"
        echo "  outbox      View and review pending cold outreach drafts"
        echo "  test        Run unit and integration test suite (pytest)"
        echo "  help        Display this help message"
        echo ""
        echo "Environment variables:"
        echo "  PORT=8000   Port to bind dashboard (default: 8000)"
        echo "  HOST=0.0.0.0 Host interface to bind (default: 0.0.0.0)"
        exit 0
        ;;

    *)
        # Pass directly to fundwatch CLI
        exec fundwatch "$COMMAND" "$@"
        ;;
esac
