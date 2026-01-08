#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Nomalyze...${NC}"

# Wait for database to be ready (if DATABASE_URL is set)
if [ -n "$DATABASE_URL" ]; then
    echo -e "${YELLOW}Waiting for database...${NC}"

    # Extract host and port from DATABASE_URL
    # Format: postgres://user:pass@host:port/dbname
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    # Default port if not found
    DB_PORT=${DB_PORT:-5432}

    # Wait up to 30 seconds for database
    for i in {1..30}; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
            echo -e "${GREEN}Database is ready!${NC}"
            break
        fi
        echo "Waiting for database... ($i/30)"
        sleep 1
    done
fi

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python manage.py migrate --noinput

# Collect static files in production
if [ "$DEBUG" = "False" ] || [ "$DEBUG" = "false" ] || [ "$DEBUG" = "0" ]; then
    echo -e "${YELLOW}Collecting static files...${NC}"
    python manage.py collectstatic --noinput
fi

echo -e "${GREEN}Starting server...${NC}"

# Execute the main command (e.g., gunicorn or runserver)
exec "$@"
