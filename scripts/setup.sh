#!/usr/bin/env bash
# Install backend + frontend dependencies for local (non-Docker) development.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== backend deps =="
pip install -r backend/requirements.txt
echo "== frontend deps =="
cd frontend && npm install
echo "Setup complete. Next: 'make data && make train' (or use committed checkpoints), then 'make backend' and 'make frontend'."
