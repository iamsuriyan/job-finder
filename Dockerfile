FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Install curl for healthcheck / network testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging files and source code
COPY pyproject.toml README.md config.yaml ./
COPY src/ ./src/

# Install python dependencies and fundwatch package
RUN pip install --no-cache-dir .

# Create data directory with appuser ownership
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

VOLUME ["/app/data"]

CMD ["python", "-m", "fundwatch", "run"]
