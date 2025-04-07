FROM python:3.11-slim@sha256:b2968bc39eeb4645556bd34de3f58551eab7d1ac88709f11a8487c222ef3a4b5

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install system dependencies required for psycopg and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    postgresql-client \
    postgresql-client-common \
    && rm -rf /var/lib/apt/lists/*

# Create directory for database backups
RUN mkdir -p /app/db_backups

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create required directories
RUN mkdir -p staticfiles media

# Run the application
CMD ["bash", "start.sh"] 