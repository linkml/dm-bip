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
# When BDC_PULL_LATEST=true (dev builds), clone default branches so git pull works at runtime.
# When false (release builds), pin to specific tags for reproducibility.
RUN git clone --depth 1 --branch v1.2.0 https://github.com/RTIInternational/NHLBI-BDC-DMC-HM.git && \
    git clone --depth 1 --branch fix/fhs-chr-blockers https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git;


#fix/fhs-chr-blockers
#fix/aric-chr-20260328
#fix/jhs-chr-20260328
#feature/spiromics
#fix/copdgene-chr-2026-03-23
#fix/mesa-chr-20260328

#git clone --depth 1 --branch fix/fhs-chr-blockers https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git;
#git clone --depth 1 --branch fix/hchs-chr-batch1 https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git; \
#git clone --depth 1 --branch fix/copdgene-chr-2026-03-23 https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git; \
    
#git clone --depth 1 --branch fix/hchs-chr-batch1 https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git \
#git clone --depth 1 --branch v1.2.0 https://github.com/RTIInternational/NHLBI-BDC-DMC-HM.git
#git clone --depth 1 --branch 2026.03-2 https://github.com/amc-corey-cox/bdc-harmonized-variables.git; \
#git clone --depth 1 --branch test/fhs-integration-2026-03-21 https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git; \
#git clone --depth 1 --branch test/whi-integration-486-490-492 https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git; \
#git clone --depth 1 --branch fix/hchs-chr-batch1 https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git; \
#git clone --depth 1 --branch fix/copdgene-chr-2026-03-23 https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git; \

CMD ["uv", "run", "dm-bip", "run"]
