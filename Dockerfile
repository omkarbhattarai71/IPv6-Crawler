# Unified Dockerfile for IPv6 Crawler - Works for both GCloud and AILab
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for both environments
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    slurm-client \
    munge \
    openssh-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project structure
COPY scripts/ ./scripts/
COPY processed/ ./processed/
COPY processed_gcloud/ ./processed_gcloud/
COPY models/ ./models/
COPY results/ ./results/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/scripts:${PATH}"

# Create non-root user
RUN useradd -m -u 1000 ipv6user && chown -R ipv6user:ipv6user /app
USER ipv6user

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import pandas; print('OK')" || exit 1

ENTRYPOINT ["python3", "scripts/pipeline.py"]
CMD ["--help"]
