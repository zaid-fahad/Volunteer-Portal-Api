# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies in a single layer to keep image size tiny
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Set entrypoint to run migrations and collectstatic
ENTRYPOINT ["/app/entrypoint.sh"]

# OPTIMIZED FOR 2GB RAM SERVER:
# - Drops down to 1 worker process with 4 lightweight threads to minimize RAM usage.
# - Automatically restarts the process every 500 requests to permanently kill Python memory leaks.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--max-requests", "500", "--max-requests-jitter", "50", "--timeout", "60", "VMApp.wsgi:application"]
