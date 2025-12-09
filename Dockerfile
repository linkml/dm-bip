FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Poetry / pip config
ENV POETRY_VERSION=1.8.4 \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1 \
    # Force Poetry to create a virtualenv instead of reusing system site-packages
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_DYNAMIC_VERSIONING_BYPASS=true

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# 🔹 Make sure the global tooling is modern enough for Poetry's installer
RUN pip install --upgrade pip setuptools wheel packaging

# Install Poetry + Cruft
RUN pip install "poetry==${POETRY_VERSION}" cruft

WORKDIR /app


# Copy dependency files first for caching
#COPY pyproject.toml poetry.lock* ./

# Copy the entire project
COPY . .

# Install dependencies using the same groups as on your local machine
# Uses the lock file; will run inside Poetry's own virtualenv
RUN poetry install --with env --with dev



# Default command – adjust if needed
CMD ["poetry", "run", "dm-bip", "run"]
