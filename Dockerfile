# Use Debian-based Python image (better compatibility than Alpine for SQLite)
FROM python:3.13-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    SQLITE_DB_PATH=/app/data/db.sqlite3

# Install system dependencies (for psycopg2, Pillow, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create and set workdir
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy Django app
COPY . .

# Create persistent data dir
RUN mkdir -p /app/data

# (Optional) Set non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
