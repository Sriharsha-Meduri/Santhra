#!/usr/bin/env bash
# Evaluate the trained model on the held-out test split.
set -euo pipefail
cd "$(dirname "$0")/.."
python ml/evaluation/evaluate.py
echo "Report written to docs/evaluation.md and ml/evaluation/results/."
