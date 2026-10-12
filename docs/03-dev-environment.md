# 03. Development Environment Setup

Follow this once, top to bottom. Commands are given for macOS/Linux (bash) and Windows (PowerShell) where they differ.

## 1. Prerequisites

| Tool | Version | Used for | Check |
|---|---|---|---|
| Python | 3.11 or newer | ML service, training | `python --version` |
| Git | any recent | version control | `git --version` |
| Docker Desktop | recent (includes Compose v2) | container image, compose | `docker --version`, `docker compose version` |
| JDK | 17 or newer | later, Spring Boot services | `java -version` |
| An editor | VS Code or IntelliJ/PyCharm | | |
| Kaggle account | free | dataset download | |

Optional: `make` (macOS/Linux have it; on Windows use WSL or run the raw commands shown in the Makefile).

## 2. Create the repository

```bash
cd digital-banking-fraud
git init
git add .
git commit -m "chore: initial project scaffold"
# create an empty repo on GitHub, then:
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

## 3. Python environment (ML service)

Always work inside a virtual environment.

```bash
cd fraud-ml-service
python -m venv .venv

# activate
source .venv/bin/activate            # macOS / Linux
# .venv\Scripts\Activate.ps1         # Windows PowerShell

python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt -r requirements-train.txt
```

After the first successful install, record the exact versions so the environment is reproducible:

```bash
pip freeze > requirements.lock
```

Commit `requirements.lock`. From then on, if something works on your machine but not in Docker, compare against this file.

## 4. Verify the toolchain

```bash
ruff check .          # lint (no output = clean)
pytest                # no tests yet is fine; it must not crash
python -c "import fastapi, sklearn, lightgbm, pandas; print('imports ok')"
```

## 5. Kaggle API (dataset download)

1. In your Kaggle account settings, create an API token. It downloads a `kaggle.json` file.
2. Place it at `~/.kaggle/kaggle.json` (macOS/Linux) or `%USERPROFILE%\.kaggle\kaggle.json` (Windows).
3. macOS/Linux only: `chmod 600 ~/.kaggle/kaggle.json`.
4. Download PaySim:

```bash
cd fraud-ml-service
kaggle datasets download -d ealaxi/paysim1 -p data/raw --unzip
ls data/raw
```

You should see a single large CSV (the PaySim log, roughly 6.3 million rows). If the command fails, you can download the same dataset manually from its Kaggle page and place the CSV in `data/raw/`.

Never commit anything in `data/` (the `.gitignore` already blocks it).

## 6. Docker check

```bash
docker run --rm hello-world
docker compose version
```

Once the service exists (Phase 5):

```bash
cd infra
docker compose up --build
```

## 7. Environment variables

Copy the example file and adjust if needed:

```bash
cd fraud-ml-service
cp .env.example .env          # Windows: copy .env.example .env
```

`.env` is git-ignored. See `.env.example` for each variable's meaning.

## 8. Editor setup (recommended)

- Select the `.venv` interpreter in your editor.
- Enable format-on-save with Ruff (VS Code: the "Ruff" extension).
- Install a Markdown preview with Mermaid support to read the architecture diagrams (VS Code: "Markdown Preview Mermaid Support").

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ImportError: libgomp.so.1` when importing LightGBM (Linux/Docker) | Missing OpenMP runtime | `apt-get install libgomp1` (the Dockerfile already does this) |
| LightGBM install fails on macOS | Missing OpenMP | `brew install libomp` |
| `pip install` is very slow or fails on a package | Python version too new/old for a wheel | Use Python 3.11 specifically |
| PowerShell blocks venv activation | Execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Kaggle CLI says 401 / unauthorized | Token missing or wrong path | Re-check step 5 |
| Pandas runs out of memory on the full dataset | 6M rows with wide dtypes | Use the dtype map in the dataset plan; filter to TRANSFER and CASH_OUT early |
| Docker container cannot find the model | Volume not mounted or `CURRENT` missing | See runbook, "Model not ready" |
