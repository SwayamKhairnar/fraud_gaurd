# Convenience commands for fraud-ml-service. Every target is a short command you can also run by hand.
# Targets marked (Phase N) work once the scripts for that phase exist.

PY ?= python

.PHONY: help setup lint format test test-fast data eda features train export serve \
        docker-build docker-run compose-up compose-down contracts-check clean

help:
	@echo "setup            install all dependencies"
	@echo "lint / format    ruff check / ruff format"
	@echo "test / test-fast pytest with coverage / without slow tests"
	@echo "contracts-check  validate contract examples against schemas"
	@echo "data             download PaySim into data/raw"
	@echo "features         build the offline feature table        (Phase 2)"
	@echo "train            train and evaluate models              (Phase 3)"
	@echo "export           export artifacts to artifacts/models   (Phase 3)"
	@echo "serve            run the API locally                    (Phase 4)"
	@echo "docker-build     build the image                        (Phase 5)"
	@echo "compose-up/down  run via docker compose                 (Phase 5)"

setup:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt -r requirements-dev.txt -r requirements-train.txt

lint:
	ruff check .

format:
	ruff format .

test:
	pytest --cov=app

test-fast:
	pytest -m "not slow"

contracts-check:
	$(PY) -m scripts.check_contracts

data:
	kaggle datasets download -d ealaxi/paysim1 -p data/raw --unzip

features:
	$(PY) -m training.prepare_data
	$(PY) -m training.build_features

train:
	$(PY) -m training.train --model baseline
	$(PY) -m training.train --model lightgbm
	$(PY) -m training.evaluate

export:
	$(PY) -m training.export_artifacts

serve:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t fraud-ml-service:dev .

docker-run:
	docker run --rm -p 8000:8000 -v "$(CURDIR)/artifacts/models:/srv/artifacts/models:ro" fraud-ml-service:dev

compose-up:
	cd ../infra && docker compose up --build -d

compose-down:
	cd ../infra && docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
