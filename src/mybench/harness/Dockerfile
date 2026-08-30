# Pinned OpenCode and uv on a Debian slim base.
# Python is pre-installed so the first `uv run` of an evaluation does not download an interpreter at run time.
FROM node:26-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g opencode-ai@1.18.25

COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /usr/local/bin/

RUN uv python install 3.13

# The Copilot CLI is the judge's runtime; the version matches the CLI pinned inside the
# github-copilot-sdk wheel required by pyproject.toml.
ARG COPILOT_VERSION=1.0.79
RUN arch="$(dpkg --print-architecture)" \
    && case "${arch}" in amd64) arch=x64 ;; arm64) arch=arm64 ;; *) echo "Unsupported architecture: ${arch}" && exit 1 ;; esac \
    && curl -fsSL "https://github.com/github/copilot-cli/releases/download/v${COPILOT_VERSION}/copilot-linux-${arch}.tar.gz" \
    | tar -xz -C /usr/local/bin copilot

ENV OPENCODE_DISABLE_AUTOUPDATE=true

WORKDIR /workspace
