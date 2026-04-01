# Stage 1: Build fpocket using bullseye (GCC 10, no -Werror=incompatible-pointer-types)
FROM python:3.11-slim-bullseye AS fpocket-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libnetcdf-dev && \
    rm -rf /var/lib/apt/lists/*

COPY vendor/fpocket /tmp/fpocket

RUN cd /tmp/fpocket && make && make install


# Stage 2: Final image
FROM python:3.11-slim

# System deps: X11 libs for RDKit Draw, OpenBabel for PDB/PDBQT, wget for Vina, netcdf for fpocket
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxrender1 libxext6 \
    openbabel \
    wget \
    libnetcdf22 \
    && rm -rf /var/lib/apt/lists/*

# AutoDock Vina pre-built binary (v1.2.5)
RUN wget -q https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.5/vina_1.2.5_linux_x86_64 \
    -O /usr/local/bin/vina && \
    chmod +x /usr/local/bin/vina

# fpocket binaries from builder stage
COPY --from=fpocket-builder /usr/local/bin/fpocket /usr/local/bin/fpocket
COPY --from=fpocket-builder /usr/local/bin/dpocket /usr/local/bin/dpocket
COPY --from=fpocket-builder /usr/local/bin/mdpocket /usr/local/bin/mdpocket

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
