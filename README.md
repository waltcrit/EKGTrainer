# EKG Trainer

A full-stack EKG teaching platform combining a structured MDX lesson curriculum with an interactive strip viewer and signal-pipeline interpretation.

## What it is

**EKG Academy** is the web interface — a structured, self-paced curriculum for learning to read electrocardiograms, with three levels (Beginner, Intermediate, Advanced) and embedded interactive components. The platform uses real PTB-XL ECG data alongside synthesized teaching cases.

The **Python backend** serves pre-processed ECG strips, runs signal analysis, and exposes an API consumed by the Next.js frontend.

## Project structure

```text
EKGTrainer/
├── web/               # Next.js 15 app (EKG Academy)
│   ├── src/           # App source (pages, components, API routes)
│   └── content/       # MDX lesson content
│       └── learn/
│           ├── beginner/
│           ├── intermediate/
│           └── advanced/
├── python/            # FastAPI backend (ECG data + analysis)
│   ├── server.py
│   ├── analyze_ecg.py
│   └── requirements.txt
└── scripts/           # Data pipeline scripts (PTB-XL, case generation)
    ├── generate_cases.py
    ├── generate_12lead_ekgs.py
    └── generate_ptbxl_ekgs.py
```

## Web app

Built with Next.js 15, React 19, Tailwind CSS, and `next-mdx-remote`.

```bash
cd web
npm install
npm run dev        # http://localhost:3000
npm run build
npm run lint
```

## Python environment

Base Python dependencies live in [python/requirements.txt](python/requirements.txt).

To sync a machine to the exact dependency set currently used in this repo, install the pinned lock file:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r python/requirements-lock.txt
```

When the environment is intentionally updated, regenerate [python/requirements-lock.txt](python/requirements-lock.txt) from the project virtual environment with:

```bash
pip freeze > python/requirements-lock.txt
```

The lock file includes the ECG-Digitiser Git dependency used by the Python pipeline.

## EKG case data

Teaching cases are sourced from the [PTB-XL dataset](https://physionet.org/content/ptb-xl/) (PhysioNet, CC BY 4.0) and from synthesized cases where no real-data equivalent exists. See [scripts/ptbxl_diagnosis_codes.md](scripts/ptbxl_diagnosis_codes.md) for the full coverage map.

To regenerate cases:

```bash
# Rhythm strips
python3 scripts/generate_cases.py --render-style physionet

# 12-lead synthetic
python3 scripts/generate_12lead_ekgs.py --render-style physionet

# Replace with real PTB-XL data where available
python3 scripts/generate_ptbxl_ekgs.py --render-style physionet --remote
```

## Deployment

- **Web**: Vercel (`vercel.json`)
- **Backend**: Railway (`railway.toml`, `Dockerfile`)

## Production security settings (recommended)

### Web (`web/`)

Set these environment variables in Vercel (or your hosting provider):

- `PYTHON_SERVICE_URL`: URL to the Python service (e.g. your Railway app).
- `PYTHON_API_KEY`: shared secret used to authenticate calls from the web app to the Python service.

### Python service (`python/server.py`)

Set these environment variables in Railway (or wherever you deploy the Python service):

- `PYTHON_API_KEY`: **must match** the web app’s `PYTHON_API_KEY`. When set, `/analyze` requires `Authorization: Bearer <token>`.
- `ALLOWED_ORIGINS`: comma-separated list of allowed web origins (default: `http://localhost:3000`).
- `MAX_IMAGE_BYTES`: max decoded upload size in bytes (default: 4 MiB).
- `RATE_MAX_REQUESTS`: max requests per IP per window (default: 60).
- `RATE_WINDOW_S`: rate limit window in seconds (default: 3600).

Notes:

- The Python `/analyze` endpoint is CPU-heavy. Do not deploy it publicly without `PYTHON_API_KEY` (and consider adding a shared external rate limiter if you scale to multiple instances).
