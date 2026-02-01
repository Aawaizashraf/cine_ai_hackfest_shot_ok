# Use Python 3.13 slim image
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTE=1
ENV UV_LINK_MODE=copy

# Set working directory
WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the project into the image
COPY . .

# Copy video from backend/video/ into the image. Put movie.mp4 in backend/video/ before building.
# If building from Git (e.g. Coolify), video/ only has .gitkeep — use a volume mount, or build locally (see VIDEO_IN_DOCKER.md).
COPY video/ /data/video/

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Create data dir; /data/video already populated by COPY above (or leave empty and use volume mount)
RUN mkdir -p data

# Default path for video; override with VIDEO_PATH env if your filename is different
ENV VIDEO_PATH=/data/video/movie.mp4

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
