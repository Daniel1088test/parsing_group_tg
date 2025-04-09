#!/bin/bash
# Comprehensive fix script for Railway deployment issues

echo "===== Starting comprehensive Railway fix ====="

# 1. Ensure DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
  echo "❌ ERROR: DATABASE_URL environment variable is not set. Cannot continue."
  exit 1
fi

echo "✅ DATABASE_URL is set: ${DATABASE_URL:0:15}..."

# 2. Push updates to git for Railway to deploy
echo "1️⃣ Committing and pushing all changes to Railway..."
git add railway_fix.sh sql_fix.py fix_aiohttp_sessions.py core/settings.py deploy_fixes.sh
git commit -m "Fix database connection and migration issues"
git push origin main

# 3. Verify Railway deployment and execute fixes remotely
echo "2️⃣ Now wait for Railway to deploy the changes, then run:"
echo "   - railway run ./railway_fix.sh"
echo "   - railway restart"

# 4. Give instructions for manual steps
echo "3️⃣ If issues persist after Railway deployment, connect to Railway and run:"
echo "   - railway connect"
echo "   - cd /app"
echo "   - bash ./railway_fix.sh"

echo "===== Fix script instructions complete =====" 