# Single production-like stage: the image contains the dependencies, and the
# code is either copied in (prod) or bind-mounted over /app (dev).
FROM python:3.13-slim

# The virtualenv lives outside /app so a bind mount of ./backend:/app never
# hides the installed dependencies.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/tmp/uv-cache \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

WORKDIR /app

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
RUN chown -R app:app /app /opt/venv

USER app

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
