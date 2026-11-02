FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# FontForge and ttfautohint are not needed by the current pipeline (the Nerd Fonts patcher runs
# in its own Docker image) but are handy for inspecting fonts and for the hinting experiments.
RUN apt-get update \
 && apt-get install -y --no-install-recommends fontforge python3-fontforge ttfautohint woff2 \
 && rm -rf /var/lib/apt/lists/*
