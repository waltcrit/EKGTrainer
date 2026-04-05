# EKGTrainer

## Python Environment

Base Python dependencies live in [python/requirements.txt](python/requirements.txt).

To sync a machine to the exact dependency set currently used in this repo, install the pinned lock file:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r python/requirements-lock.txt
```

When the environment is intentionally updated, regenerate or refresh [python/requirements-lock.txt](python/requirements-lock.txt) from the project virtual environment with:

```bash
pip freeze > python/requirements-lock.txt
```

The lock file includes the ECG-Digitiser Git dependency used by the Python pipeline.
