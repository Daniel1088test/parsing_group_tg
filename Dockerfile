FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Install system dependencies required for psycopg, Pillow, and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    procps \
    postgresql-client \
    postgresql-client-common \
    # Залежності для Pillow
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    # Додаткові системні утиліти
    git \
    && rm -rf /var/lib/apt/lists/*

# Create directory for database backups
RUN mkdir -p /app/db_backups

# Copy fix requirements script and requirements files
COPY fix_requirements.py requirements.txt requirements-base.txt ./

# Install wheel and setuptools first to ensure proper package building
RUN pip install --upgrade pip setuptools wheel

# Install pyaes explicitly first to avoid build issues
RUN pip install --no-cache-dir pyaes==1.6.1

# 1. Встановлюємо базові залежності для стабільної роботи
RUN pip install --no-cache-dir -r requirements-base.txt

# 2. Ensure psycopg2 is installed first (both binary and regular versions)
RUN pip install --no-cache-dir psycopg2-binary==2.9.9
RUN pip install --no-cache-dir psycopg2==2.9.9 || echo "Regular psycopg2 failed to install, continuing with binary version"

# 3. Встановлюємо Pillow окремо, щоб переконатися, що він правильно встановлений
RUN pip install --no-cache-dir Pillow==10.1.0

# 4. Виправляємо requirements.txt і встановлюємо всі залежності
RUN python fix_requirements.py && \
    pip install --no-cache-dir -r requirements.txt || \
    echo "Warning: Could not install all requirements, continuing with base dependencies"

# Copy project
COPY . .

# Create required directories
RUN mkdir -p staticfiles media logs/bot data/sessions

# Make scripts executable
RUN chmod +x migrate-railway.py run_bot.py run_parser.py start-railway.sh run.py

# Test database connectivity before starting
RUN echo "Testing database connection during build..." && \
    python -c "import sys; \
import psycopg2; \
print('✓ psycopg2 is properly installed'); \
" || \
    echo "Warning: psycopg2 test failed, but continuing build"

# Run the application
CMD ["bash", "start-railway.sh"] 