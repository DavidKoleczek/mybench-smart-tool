# Pinned OpenCode and uv on a Debian slim base.
# Python is pre-installed so the first `uv run` of an evaluation does not download an interpreter at run time.
FROM node:26-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g opencode-ai@1.18.25

COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /usr/local/bin/

RUN uv python install 3.13

ENV OPENCODE_DISABLE_AUTOUPDATE=true

WORKDIR /workspace
