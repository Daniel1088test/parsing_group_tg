FROM python:3.12-slim

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

# Copy fix requirements script and requirements files
COPY fix_requirements.py requirements.txt requirements-base.txt ./

# 1. Встановлюємо базові залежності для стабільної роботи
RUN pip install --no-cache-dir -r requirements-base.txt

# 2. Виправляємо requirements.txt і встановлюємо всі залежності
RUN python fix_requirements.py && \
    pip install --no-cache-dir -r requirements.txt || \
    echo "Warning: Could not install all requirements, continuing with base dependencies"

# Copy project
COPY . .

# Create required directories
RUN mkdir -p staticfiles media logs/bot data/sessions

# Make scripts executable
RUN chmod +x migrate-railway.py run_bot.py run_parser.py start-railway.sh

# Run the application
CMD ["bash", "start-railway.sh"] 