FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 libxext6 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-editable

COPY . .

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
