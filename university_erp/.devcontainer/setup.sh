#!/usr/bin/env bash
set -e

echo "================================================"
echo "  University ERP — Codespace Setup"
echo "================================================"

cd "$(dirname "$0")/.."

echo ""
echo "[1/3] Building all Docker images..."
docker compose build

echo ""
echo "[2/3] Starting all services..."
docker compose up -d

echo ""
echo "[3/3] Waiting for services to become healthy..."

MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  HEALTHY=$(docker compose ps --format json 2>/dev/null | grep -c '"healthy"' || true)
  TOTAL=$(docker compose ps --format json 2>/dev/null | wc -l || true)

  # Postgres + RabbitMQ must be healthy (2 health-checked services)
  if [ "$HEALTHY" -ge 2 ]; then
    break
  fi

  sleep 3
  ELAPSED=$((ELAPSED + 3))
  echo "  ...waiting ($ELAPSED s)"
done

echo ""
echo "================================================"
echo "  ✅ University ERP is ready!"
echo ""
echo "  Open the 'Ports' tab and click port 8000"
echo "  Or run: gp preview \$(gp url 8000)"
echo "================================================"
docker compose ps
