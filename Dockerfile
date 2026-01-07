FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*


#Address Copilot suggestion to install the official uv Docker image and pin the tag so for stability
COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /uvx /usr/local/bin/

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency files first for caching  
COPY pyproject.toml uv.lock ./  

# Install dependencies using uv
RUN uv sync --frozen

# Default command
CMD ["uv", "run", "dm-bip", "run"]
