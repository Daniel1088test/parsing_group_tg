FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV RAILWAY_ENVIRONMENT=production
ENV DJANGO_SETTINGS_MODULE=core.settings

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

# Install critical packages first to avoid issues
RUN pip install --no-cache-dir pyaes==1.6.1 psycopg2-binary==2.9.9 dj-database-url==2.1.0 python-dotenv==1.0.0 whitenoise==6.6.0 django-storages==1.14.2

# 1. Встановлюємо базові залежності для стабільної роботи
RUN pip install --no-cache-dir -r requirements-base.txt

# 2. Ensure psycopg2 is installed (both binary and regular versions if possible)
RUN pip install --no-cache-dir psycopg2==2.9.9 || echo "Regular psycopg2 failed to install, continuing with binary version"

# 3. Встановлюємо Pillow окремо, щоб переконатися, що він правильно встановлений
RUN pip install --no-cache-dir Pillow==10.1.0

# 4. Виправляємо requirements.txt і встановлюємо всі залежності
RUN python fix_requirements.py && \
    pip install --no-cache-dir -r requirements.txt || \
    echo "Warning: Could not install all requirements, continuing with base dependencies"

# Copy project
COPY . .

# Create required directories (will be handled by run.py but create them here for safety)
RUN mkdir -p staticfiles static media logs/bot data/sessions

# Create health check files
RUN for file in health.txt healthz.txt health.html healthz.html; do \
    echo "OK" > $file; \
    echo "OK" > static/$file; \
    echo "OK" > staticfiles/$file; \
    done

# Make scripts executable
RUN chmod +x start-railway.sh run.py fix_django_settings.py fix_requirements.py

# Test database connectivity before starting
RUN echo "Testing database connection during build..." && \
    python -c "import sys; \
import psycopg2; \
import dj_database_url; \
print('✓ psycopg2 and dj_database_url are properly installed'); \
" || \
    echo "Warning: Database connectivity test failed, but continuing build"

# Run the application using our single entry point
CMD ["bash", "start-railway.sh"] 