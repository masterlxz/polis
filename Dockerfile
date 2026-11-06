# Imagem de DESENVOLVIMENTO (ADR 0006). A imagem de produção é decisão da
# hospedagem (P-04) e não vive aqui.
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

# O venv fica fora de /app: o Compose monta o código em /app e esconderia um .venv de lá.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 1000 app \
    && mkdir /opt/venv /app \
    && chown app:app /opt/venv /app

USER app
WORKDIR /app

# Dependências antes do código: o cache só invalida quando pyproject.toml ou uv.lock mudam.
COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --locked

COPY --chown=app:app . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
