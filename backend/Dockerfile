# Stage 1: Builder
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN python -m pip install --no-cache-dir uv

# Copy configuration files
COPY pyproject.toml .

# Create virtual environment and install dependencies
ENV UV_HTTP_TIMEOUT=300

RUN printf "torch==2.9.1+cpu\ntorchvision==0.24.1+cpu\n" > constraints.txt && \
    uv venv /opt/venv && \
    uv pip compile pyproject.toml -o requirements.txt \
      --index-url https://pypi.org/simple \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      --constraint constraints.txt && \
    uv pip install -r requirements.txt \
      --python /opt/venv \
      --index-url https://pypi.org/simple \
      --extra-index-url https://download.pytorch.org/whl/cpu

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies
# curl for healthchecks if needed
RUN apt-get update && apt-get install -y \
    curl \
    libgomp1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
