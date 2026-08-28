#!/usr/bin/env bash
# Full training pipeline: data -> classifier -> anomaly AE -> calibration -> samples.
set -euo pipefail
cd "$(dirname "$0")/.."
MAX_SOURCES="${MAX_SOURCES:-1200}"
EPOCHS="${EPOCHS:-14}"

python ml/scripts/prepare_clean_images.py --max-sources "$MAX_SOURCES"
python ml/datasets/build_dataset.py
python ml/training/train.py --epochs "$EPOCHS"
python ml/training/train_anomaly.py --epochs 18
python ml/training/calibrate.py
python scripts/generate_samples.py
echo "Training pipeline complete. Checkpoints in ml/checkpoints/."
