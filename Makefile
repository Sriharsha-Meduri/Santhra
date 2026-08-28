# Santhra developer shortcuts
.PHONY: help setup data train evaluate samples backend frontend test docker-build docker-up clean

help:
	@echo "setup        Install backend + frontend deps"
	@echo "data         Download clean images + build train/val/test dataset"
	@echo "train        Train classifier + anomaly AE + fit calibration"
	@echo "evaluate     Evaluate on test split -> docs/evaluation.md"
	@echo "samples      Generate curated sample images"
	@echo "backend      Run FastAPI (http://localhost:8000)"
	@echo "frontend     Run Vite dev server (http://localhost:5173)"
	@echo "test         Run backend test suite"
	@echo "docker-up    Build & run full stack via docker compose"

setup:
	pip install -r backend/requirements.txt
	cd frontend && npm install

data:
	python ml/scripts/prepare_clean_images.py --max-sources 1200
	python ml/datasets/build_dataset.py

train:
	python ml/training/train.py --epochs 14
	python ml/training/train_anomaly.py --epochs 18
	python ml/training/calibrate.py

evaluate:
	python ml/evaluation/evaluate.py

samples:
	python scripts/generate_samples.py

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && python -m pytest -q

docker-build:
	docker compose build

docker-up:
	docker compose up --build

clean:
	rm -rf media *.db backend/**/__pycache__ frontend/dist
