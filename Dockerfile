FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official Docker image, pinned for stability
COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /uvx /usr/local/bin/

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency files and source package for layer caching
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

# Install dependencies using uv
RUN uv sync --frozen

# Copy the rest (scripts, tests, configs, etc.)
COPY . ./

# Archive the Dockerfile used to build this image at a known root-level path
COPY Dockerfile /Dockerfile.archived

# Clone external repos (shallow, single layer)
RUN git clone --depth 1 --branch v1.1.0 https://github.com/RTIInternational/NHLBI-BDC-DMC-HM.git && \
    git clone --depth 1 https://github.com/amc-corey-cox/bdc-harmonized-variables.git

ARG BDC_PULL_LATEST=false
ENV BDC_PULL_LATEST=${BDC_PULL_LATEST}

CMD ["uv", "run", "dm-bip", "run"]
