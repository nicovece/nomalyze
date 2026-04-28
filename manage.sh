#!/bin/bash

# Django management script - runs manage.py commands from the src directory
# Usage: ./manage.sh [command] [options]
#
# Prefers nomalyze-backend/.venv so project deps (django-browser-reload, etc.)
# are used instead of a partial system site-packages install.

if [ $# -eq 0 ]; then
    echo "Usage: ./manage.sh [command] [options]"
    echo "Examples:"
    echo "  ./manage.sh runserver"
    echo "  ./manage.sh makemigrations"
    echo "  ./manage.sh migrate"
    echo "  ./manage.sh createsuperuser"
    echo "  ./manage.sh shell"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
elif [ -x "$SCRIPT_DIR/.venv/bin/python3" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo "No Python interpreter found. Install Python 3 or create .venv:"
    echo "  cd \"$SCRIPT_DIR\" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

if [ ! -x "$SCRIPT_DIR/.venv/bin/python" ] && [ ! -x "$SCRIPT_DIR/.venv/bin/python3" ]; then
    echo "Note: no .venv in $SCRIPT_DIR — using $PYTHON (install deps there to avoid missing modules)."
fi

cd "$SCRIPT_DIR/src" && exec "$PYTHON" manage.py "$@"
