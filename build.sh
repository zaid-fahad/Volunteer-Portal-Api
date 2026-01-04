#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run migrations only if DATABASE_URL is present
if [ -n "$DATABASE_URL" ]; then
    echo "Running migrations..."
    python manage.py migrate
else
    echo "DATABASE_URL not set. Skipping migrations during build phase."
fi
