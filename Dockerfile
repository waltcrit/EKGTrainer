# ── Stage 1: Python dependencies ────────────────────────────────────────────
FROM python:3.11-slim AS python-deps

WORKDIR /python

# System libs needed by opencv-headless and scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY python/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ECG-Digitiser is not on PyPI — install from GitHub
RUN pip install --no-cache-dir \
    git+https://github.com/felixkrones/ECG-Digitiser.git \
    || echo "WARNING: ECG-Digitiser install failed — falling back to OpenCV digitizer"

COPY python/ .


# ── Stage 2: Next.js build ───────────────────────────────────────────────────
FROM node:20-slim AS nextjs-build

WORKDIR /app
COPY web/package*.json ./
RUN npm ci
COPY web/ .
RUN npm run build


# ── Stage 3: Final runtime image ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Install Node.js into the Python base image
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libgl1 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python env from stage 1
COPY --from=python-deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=python-deps /usr/local/bin/python3 /usr/local/bin/python3
COPY --from=python-deps /python /python

# Copy Next.js build + node_modules from stage 2
COPY --from=nextjs-build /app/.next ./.next
COPY --from=nextjs-build /app/node_modules ./node_modules
COPY --from=nextjs-build /app/package.json ./package.json
COPY --from=nextjs-build /app/public ./public

# Make python script accessible at the path the API route expects
# PYTHON_SCRIPT = join(process.cwd(), "..", "python", "analyze_ecg.py")
# process.cwd() = /app, so script lives at /python/analyze_ecg.py ✓

ENV NODE_ENV=production
ENV PYTHON_BIN=python3
ENV PORT=3000

EXPOSE 3000

CMD ["node_modules/.bin/next", "start", "-p", "3000"]
