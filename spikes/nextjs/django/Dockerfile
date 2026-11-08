# Spike (ADR 0015). Versões iguais às do uv.lock do projeto; gunicorn 26.2.0 (publicado em 2026-08-24).
FROM python:3.14-slim
RUN pip install --no-cache-dir "django==6.1.3" "psycopg[binary]==3.3.8" "gunicorn==26.2.0"
RUN useradd --create-home --uid 1000 app
USER app
WORKDIR /srv
COPY --chown=app:app app.py .
COPY --chown=app:app templates templates
EXPOSE 8000
# Um worker por vCPU emulada (WORKERS), threads para a espera do banco.
CMD ["sh", "-c", "exec gunicorn app:application -b 0.0.0.0:8000 -w ${WORKERS:-2} --threads 4"]
