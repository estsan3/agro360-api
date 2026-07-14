# ------------------------------------------------------------------
# Imagen del backend Agro360 API (FastAPI + Poetry).
# Build multi-etapa: instala dependencias con Poetry y ejecuta con
# un runtime liviano sin herramientas de build.
# ------------------------------------------------------------------

# --- Etapa 1: resolución e instalación de dependencias -------------
FROM python:3.12-slim AS builder

ENV POETRY_VERSION=1.8.5 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app

# Copiamos solo los manifiestos primero para aprovechar la cache de Docker:
# si no cambian las dependencias, no se reinstala nada.
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

# --- Etapa 2: runtime ----------------------------------------------
FROM python:3.12-slim AS runtime

# Usuario sin privilegios para ejecutar la aplicación.
RUN useradd --create-home --shell /usr/sbin/nologin agro360

WORKDIR /app

# Virtualenv con las dependencias ya resueltas en la etapa anterior.
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Código de la aplicación.
COPY app ./app
COPY scripts ./scripts

# Carpeta para la base SQLite de desarrollo (montable como volumen).
RUN mkdir -p /app/data && chown -R agro360:agro360 /app

USER agro360

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
