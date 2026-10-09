#!/usr/bin/env bash
set -e

# Run database migrations if DATABASE_URL is provided
if [ -n "$DATABASE_URL" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
else
    echo "WARNING: DATABASE_URL is not set. Skipping migrations."
fi

# Collect static files for WhiteNoise
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Execute the container's main command (e.g. gunicorn)
exec "$@"
