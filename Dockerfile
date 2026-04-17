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

# Build metadata — set by CI (docker/build-push-action) or manual builds
ARG DM_BIP_VERSION=unknown
ARG DM_BIP_GIT_REF=unknown
ARG DM_BIP_BUILD_DATE=unknown

ENV DM_BIP_VERSION=${DM_BIP_VERSION}
ENV DM_BIP_GIT_REF=${DM_BIP_GIT_REF}
ENV DM_BIP_BUILD_DATE=${DM_BIP_BUILD_DATE}

LABEL org.opencontainers.image.version=${DM_BIP_VERSION}
LABEL org.opencontainers.image.revision=${DM_BIP_GIT_REF}
LABEL org.opencontainers.image.created=${DM_BIP_BUILD_DATE}
LABEL org.opencontainers.image.source=https://github.com/linkml/dm-bip

# Clone external repos (shallow, single layer)
# When BDC_PULL_LATEST=true (dev builds), clone default branches so git pull works at runtime.
# When false (release builds), pin to specific tags for reproducibility.
ARG BDC_PULL_LATEST=false
ENV BDC_PULL_LATEST=${BDC_PULL_LATEST}
RUN if [ "$BDC_PULL_LATEST" = "true" ]; then \
      git clone --depth 1 https://github.com/RTIInternational/NHLBI-BDC-DMC-HM.git && \
      git clone --depth 1 https://github.com/amc-corey-cox/bdc-harmonized-variables.git; \
    else \
      git clone --depth 1 --branch v1.2.0 https://github.com/RTIInternational/NHLBI-BDC-DMC-HM.git && \
      git clone --depth 1 --branch 2026.03-2 https://github.com/amc-corey-cox/bdc-harmonized-variables.git; \
    fi

# Capture git metadata for cloned repos so Python never needs to shell out to git
RUN for repo in NHLBI-BDC-DMC-HM bdc-harmonized-variables; do \
      echo "${repo}:"; \
      echo "  commit: $(git -C ${repo} rev-parse HEAD)"; \
      echo "  ref: $(git -C ${repo} describe --tags --always)"; \
    done > /app/repo-manifest.yaml

CMD ["uv", "run", "dm-bip", "run"]
