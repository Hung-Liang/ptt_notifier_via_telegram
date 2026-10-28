FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    TZ=Asia/Taipei \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app

WORKDIR /app

# Install dependencies first so code changes don't invalidate this layer
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN mkdir -p assets/boards logs && chown -R app:app assets logs

USER app

# First notifier run can be up to notify_interval (default 30) minutes
# after start; raise start-period if the interval is longer
HEALTHCHECK --interval=5m --timeout=10s --start-period=35m \
    CMD ["python", "healthcheck.py"]

CMD ["python", "main.py"]
