FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.lock ./requirements.lock
RUN pip install -r requirements.lock
COPY pyproject.toml ./
COPY backend ./backend
RUN python backend/landlaw/local_embedding.py download /app/models/e5
RUN pip install --no-deps . && useradd --create-home --uid 10001 app
COPY data/sources.json data/legal_relations.json data/projects.json ./data/
COPY data/place_aliases.json ./data/
COPY data/evaluation ./data/evaluation
COPY migrations ./migrations
COPY reports ./reports
RUN chown -R app:app /app
USER app
EXPOSE 8000
CMD ["sh","-c","uvicorn landlaw.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-proxy-headers"]
