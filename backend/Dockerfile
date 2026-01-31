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

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Create directories for optional data and video (mount video at /data/video at runtime)
RUN mkdir -p data /data/video

# Optional: set VIDEO_PATH at runtime to the path inside the container where you mount the video file.
# Example: docker run -v /host/path/to/movie.mp4:/data/video/movie.mp4 -e VIDEO_PATH=/data/video/movie.mp4 ...
# ENV VIDEO_PATH=/data/video/movie.mp4

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
