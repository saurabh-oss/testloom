FROM python:3.12-slim AS base

LABEL maintainer="TestLoom Contributors"
LABEL description="AI-powered test case generation framework"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install -e ".[all]"

# Default command
ENTRYPOINT ["testloom"]
CMD ["--help"]
