FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends espeak-ng ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install torch CPU-only to reduce image size (~1.5 Go saved)
ENV UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN uv sync --frozen --no-dev

COPY *.py test.html ./

# Pre-download the Kokoro model so the container starts instantly
RUN uv run python -c "from kokoro import KPipeline; KPipeline(lang_code='f', repo_id='hexgrad/Kokoro-82M')"

EXPOSE 7860
CMD ["uv", "run", "python", "app.py", "--public"]
