FROM python:3.11-slim

# System deps for opencv-python-headless and git (ECG-Digitiser install)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Install ECG-Digitiser from GitHub (not on PyPI)
# Failure is non-fatal — fallback OpenCV digitizer is used automatically
RUN pip install --no-cache-dir \
    git+https://github.com/felixkrones/ECG-Digitiser.git \
    || echo "ECG-Digitiser not available, fallback digitizer will be used"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
